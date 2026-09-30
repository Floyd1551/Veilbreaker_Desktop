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


def main():
    run(sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v")
    run(sys.executable, "tools/make_icon.py")
    run(sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "Veilbreaker.spec")
    bundle = ROOT / "dist/Veilbreaker"
    exe = bundle / ("veilbreaker.exe" if os.name == "nt" else "veilbreaker")
    gui = bundle / ("VeilbreakerDesktop.exe" if os.name == "nt" else "VeilbreakerDesktop")
    run(exe, "--version", timeout=30)
    run(exe, "selftest", timeout=60)
    # Test real frozen worker dispatch and Unicode data paths, without contacting hardware.
    with tempfile.TemporaryDirectory(prefix="veilbreaker-frozen-") as temp:
        folder = Path(temp)
        request = folder / "request.json"
        response = folder / "result.json"
        request.write_text(json.dumps({"action": "analyze", "config": {"data_dir": str(folder / "Büro"), "site_id": "東京"},
                                       "input": str(ROOT / "examples/cellular-degraded.json")}), encoding="utf-8")
        run(exe, "--desktop-job", request, response, timeout=60)
        result = json.loads(response.read_text(encoding="utf-8"))
        if not result.get("ok") or not Path(result["result"]["evidence_zip"]).exists():
            raise RuntimeError("Frozen analysis worker failed")
    run(gui, "--smoke-test", ROOT / "test-artifacts/packaged-gui", timeout=60)
    report = json.loads((ROOT / "test-artifacts/packaged-gui/gui-smoke.json").read_text(encoding="utf-8"))
    if not report.get("passed") or report["version"] != __version__:
        raise RuntimeError("Packaged GUI smoke failed")
    licenses = bundle / "third-party-licenses"
    licenses.mkdir(exist_ok=True)
    for package in ("PySide6", "PySide6_Essentials", "PySide6_Addons", "shiboken6", "pyserial", "PyInstaller"):
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
    if os.name != "nt":
        (bundle / "installer").mkdir(exist_ok=True)
        shutil.copy2(ROOT / "installer/install-linux.sh", bundle / "installer/install-linux.sh")
        shutil.copy2(ROOT / "installer/uninstall-linux.sh", bundle / "installer/uninstall-linux.sh")
    manifest = {"version": __version__, "python": platform.python_version(), "platform": platform.platform(),
                "packages": {d.metadata["Name"]: d.version for d in importlib.metadata.distributions()},
                "passed": True, "checks": ["source tests", "frozen CLI selftest", "frozen Unicode analysis worker", "frozen GUI five pages"]}
    (bundle / "build-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    name = f"Veilbreaker-{__version__}-{platform.system().lower()}-{platform.machine().lower()}"
    archive = Path(shutil.make_archive(str(ROOT / "dist" / name), "zip" if os.name == "nt" else "gztar", ROOT / "dist", "Veilbreaker"))
    archive.with_name(archive.name + ".sha256").write_text(hashlib.sha256(archive.read_bytes()).hexdigest() + "  " + archive.name + "\n", encoding="ascii")
    if sys.platform == "linux":
        from test_linux_install import test_install
        test_install(ROOT)
        from build_linux import build_deb
        deb = build_deb(ROOT, __version__)
        if deb:
            deb.with_name(deb.name + ".sha256").write_text(hashlib.sha256(deb.read_bytes()).hexdigest() + "  " + deb.name + "\n", encoding="ascii")
    print(f"Verified release: {archive}")


if __name__ == "__main__":
    main()
