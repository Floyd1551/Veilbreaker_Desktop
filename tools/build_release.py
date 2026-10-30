"""Build and smoke-test on the target OS. Does not publish releases."""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT / "src"))
from veilbreaker import __version__


def run(*args, **kwargs):
    return subprocess.run(list(map(str, args)), check=True, **kwargs)


def freezer_environment():
    env = os.environ.copy()
    if os.name == "nt":
        # Native dependency discovery must not collect unrelated application DLLs
        # from PATH (for example an incompatible ICU from a PDF tool runtime).
        windows = Path(env.get("SystemRoot", env.get("WINDIR", "C:/Windows")))
        env["PATH"] = os.pathsep.join(str(p) for p in (
            Path(sys.executable).parent, Path(sys.base_prefix), windows / "System32", windows))
        for key in ("QT_PLUGIN_PATH", "QT_QPA_PLATFORM_PLUGIN_PATH"):
            env.pop(key, None)
    return env


def main():
    skip_tests = "--skip-tests" in sys.argv
    if not skip_tests:
        run(sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v")
    run(sys.executable, "tools/make_icon.py")
    run(sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "Veilbreaker.spec", env=freezer_environment())
    bundle = ROOT / "dist/Veilbreaker"
    exe = bundle / ("veilbreaker.exe" if os.name == "nt" else "veilbreaker")
    gui = bundle / ("VeilbreakerDesktop.exe" if os.name == "nt" else "VeilbreakerDesktop")
    if not skip_tests:
        run(exe, "--version", timeout=30)
        run(exe, "selftest", timeout=60)
        run(exe, "--terrain-smoke", ROOT / "test-artifacts/packaged-terrain", timeout=90)
        # Test real frozen worker dispatch and Unicode data paths, without contacting hardware.
        with tempfile.TemporaryDirectory(prefix="veilbreaker-frozen-") as temp:
            folder = Path(temp)
            request = folder / "request.json"
            response = folder / "result.json"
            request.write_text(json.dumps({"action": "analyze", "config": {"data_dir": str(folder / "Büro"), "site_id": "東京"},
                                           "input": str(ROOT / "examples/cellular-degraded.json")}), encoding="utf-8")
            worker = run(exe, "--desktop-job", request, response, timeout=60, capture_output=True, text=True)
            result = json.loads(response.read_text(encoding="utf-8"))
            if not result.get("ok") or not Path(result["result"]["evidence_zip"]).exists():
                raise RuntimeError("Frozen analysis worker failed")
            events = [json.loads(line) for line in worker.stdout.splitlines()]
            if [event.get("status") for event in events] != ["running", "collected"]:
                raise RuntimeError("Frozen worker collection progress failed")
            if result["result"]["collection"]["metric_sources"].get("rsrp") != ["imported_metrics"]:
                raise RuntimeError("Frozen worker import provenance failed")
            run(exe, "verify", result["result"]["evidence_zip"], timeout=30)
        run(exe, "--gui-smoke", ROOT / "test-artifacts/packaged-gui-console", timeout=60)
        run(gui, "--smoke-test", ROOT / "test-artifacts/packaged-gui", timeout=60)
        report = json.loads((ROOT / "test-artifacts/packaged-gui/gui-smoke.json").read_text(encoding="utf-8"))
        if not report.get("passed") or report["version"] != __version__:
            raise RuntimeError("Packaged GUI smoke failed")
        try:
            run(gui, "--map-smoke", ROOT / "test-artifacts/packaged-map", timeout=90)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            # The Windows GUI executable has no console. Retain its actual
            # renderer results in CI logs before propagating the failure.
            diagnostic = ROOT / "test-artifacts/packaged-map/map-smoke.json"
            if diagnostic.exists():
                print(diagnostic.read_text(encoding="utf-8"), flush=True)
            raise
        map_report = json.loads((ROOT / "test-artifacts/packaged-map/map-smoke.json").read_text(encoding="utf-8"))
        if not map_report.get("passed"):
            raise RuntimeError("Packaged map rendering/selection/offline checks failed")
    licenses = bundle / "third-party-licenses"
    licenses.mkdir(exist_ok=True)
    for package in ("PySide6", "PySide6_Essentials", "PySide6_Addons", "shiboken6", "pyserial", "PyInstaller", "rasterio", "pyproj", "numpy", "affine", "attrs", "click", "cligj", "click-plugins", "pyparsing", "certifi"):
        distribution = importlib.metadata.distribution(package)
        for item in distribution.files or []:
            if any(term in str(item).lower() for term in ("license", "copying", "notice")):
                source = Path(distribution.locate_file(item))
                if source.is_file():
                    destination = licenses / package / str(item).replace("/", "_").replace("\\", "_")
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, destination)
    shutil.copy2(ROOT / "README.md", bundle / "README.md")
    shutil.copytree(ROOT / "docs", bundle / "docs", dirs_exist_ok=True)
    offline_manifest = None
    map_file = ROOT / "map-packs/CONUS-overview-20261019.pmtiles"
    map_sidecar = ROOT / "map-packs/CONUS-overview-20261019.json"
    cell_file = ROOT / "offline-input/311.csv"
    cell_metadata = ROOT / "offline-input/311.json"
    fcc_file = ROOT / "offline-input/fcc-r_tower-20261025.zip"
    fcc_metadata = ROOT / "offline-input/fcc-r_tower-20261025.json"
    inputs = (map_file, map_sidecar, cell_file, cell_metadata)
    if all(path.is_file() for path in inputs):
        from prepare_offline_data import prepare
        fcc_options = {}
        if fcc_file.is_file() and fcc_metadata.is_file():
            fcc_info = json.loads(fcc_metadata.read_text(encoding="utf-8-sig"))
            from prepare_offline_data import _hash
            if fcc_info.get('sha256') != _hash(fcc_file):
                raise ValueError('FCC archive checksum does not match its sidecar.')
            fcc_options = dict(fcc_archive=fcc_file, fcc_date=fcc_info.get('date'))
        elif os.environ.get("VEILBREAKER_OFFLINE_DATA_REQUIRED") == "1":
            raise RuntimeError('FCC archive and checksum/date sidecar must be staged for this build.')
        offline_manifest = prepare(map_file, map_sidecar, cell_file, bundle / "offline-data",
                                   json.loads(cell_metadata.read_text(encoding="utf-8-sig")), **fcc_options)
        if not skip_tests:
            run(gui, "--map-smoke", ROOT / "test-artifacts/packaged-real-map",
                bundle / "offline-data/maps/CONUS-overview.pmtiles", timeout=120)
            real_report = json.loads((ROOT / "test-artifacts/packaged-real-map/map-smoke.json").read_text(encoding="utf-8"))
            if not real_report.get("passed"):
                raise RuntimeError("Packaged CONUS map smoke failed")
    elif os.environ.get("VEILBREAKER_OFFLINE_DATA_REQUIRED") == "1":
        raise RuntimeError("Offline map, sidecar, cell export and metadata must all be staged for this build.")
    else:
        print("Optional offline deployment data not included: stage the map, cell export and metadata.", flush=True)
    if os.name != "nt":
        (bundle / "installer").mkdir(exist_ok=True)
        shutil.copy2(ROOT / "installer/install-linux.sh", bundle / "installer/install-linux.sh")
        shutil.copy2(ROOT / "installer/uninstall-linux.sh", bundle / "installer/uninstall-linux.sh")
    manifest = {"version": __version__, "python": platform.python_version(), "platform": platform.platform(),
                "packages": {d.metadata["Name"]: d.version for d in importlib.metadata.distributions()},
                "passed": not skip_tests, "tests_skipped": skip_tests, "offline_data": offline_manifest,
                "checks": [] if skip_tests else ["source tests", "frozen CLI selftest", "frozen Unicode analysis worker", "frozen GUI seven pages", "frozen offline map rendering and selection", "frozen terrain raster projection and profile"] + (["frozen CONUS map rendering"] if offline_manifest else [])}
    (bundle / "build-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    name = f"Veilbreaker-{__version__}-{platform.system().lower()}-{platform.machine().lower()}"
    archive = Path(shutil.make_archive(str(ROOT / "dist" / name), "zip" if os.name == "nt" else "gztar", ROOT / "dist", "Veilbreaker"))
    archive.with_name(archive.name + ".sha256").write_text(hashlib.sha256(archive.read_bytes()).hexdigest() + "  " + archive.name + "\n", encoding="ascii")
    if sys.platform == "linux":
        from test_linux_install import test_install
        if not skip_tests:
            test_install(ROOT)
        from build_linux import build_deb
        deb = build_deb(ROOT, __version__)
        if deb:
            deb.with_name(deb.name + ".sha256").write_text(hashlib.sha256(deb.read_bytes()).hexdigest() + "  " + deb.name + "\n", encoding="ascii")
    print(f"{'Built (tests skipped)' if skip_tests else 'Verified release'}: {archive}")


if __name__ == "__main__":
    main()
