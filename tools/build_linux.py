"""Build a Debian package from the verified native Linux folder bundle."""
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile


def build_deb(root, version):
    machine = platform.machine().lower()
    arch = {"x86_64": "amd64", "aarch64": "arm64"}.get(machine)
    if not arch or not shutil.which("dpkg-deb"):
        print("Debian packaging skipped: dpkg-deb or supported architecture unavailable.")
        return None
    with tempfile.TemporaryDirectory(prefix="veilbreaker-deb-") as folder:
        stage = Path(folder)
        shutil.copytree(root / "dist/Veilbreaker", stage / "opt/veilbreaker")
        control = stage / "DEBIAN"
        control.mkdir()
        (control / "control").write_text(
            f"Package: veilbreaker-desktop\nVersion: {version.replace('rc', '~rc')}\nArchitecture: {arch}\n"
            "Maintainer: Outpost Relay\nSection: net\nPriority: optional\n"
            "Depends: libc6 (>= 2.39), libegl1, libopengl0, libxkbcommon0, libxcb-cursor0, libxcb-icccm4, libxcb-keysyms1, libxcb-shape0, libxcb-xinerama0\n"
            "Description: Explainable field network diagnostics and evidence\n", encoding="utf-8")
        binaries = stage / "usr/bin"
        binaries.mkdir(parents=True)
        (binaries / "veilbreaker").symlink_to("/opt/veilbreaker/veilbreaker")
        (binaries / "veilbreaker-desktop").symlink_to("/opt/veilbreaker/VeilbreakerDesktop")
        desktop = stage / "usr/share/applications"
        desktop.mkdir(parents=True)
        (desktop / "veilbreaker.desktop").write_text(
            "[Desktop Entry]\nType=Application\nName=Veilbreaker\nExec=/opt/veilbreaker/VeilbreakerDesktop\n"
            "Icon=/opt/veilbreaker/_internal/veilbreaker/assets/app.png\nTerminal=false\nCategories=Network;Utility;\n", encoding="utf-8")
        target = root / "dist" / f"Veilbreaker-{version}-{arch}.deb"
        subprocess.run(["dpkg-deb", "--root-owner-group", "--build", str(stage), str(target)], check=True)
        return target
