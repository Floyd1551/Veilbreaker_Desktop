"""Exercise Linux per-user installation without touching the real user's home."""
import json
import os
from pathlib import Path
import subprocess
import tempfile


def test_install(root):
    with tempfile.TemporaryDirectory(prefix="veilbreaker-install-") as folder:
        home = Path(folder)
        env = dict(os.environ, HOME=str(home), XDG_DATA_HOME=str(home / "data"))
        app = home / "data/veilbreaker-app"
        data = home / "data/veilbreaker"
        data.mkdir(parents=True)
        sentinel = data / "preserve-me.txt"
        sentinel.write_text("keep", encoding="utf-8")
        source = root / "dist/Veilbreaker/installer/install-linux.sh"
        for _ in range(2):
            subprocess.run(["sh", str(source)], env=env, check=True)
            subprocess.run([str(app / "veilbreaker"), "selftest"], env=env, check=True, timeout=60)
            assert (home / ".local/bin/veilbreaker").resolve() == app / "veilbreaker"
            assert (home / "data/applications/veilbreaker.desktop").exists()
        subprocess.run(["sh", str(app / "installer/uninstall-linux.sh")], env=env, check=True)
        assert not app.exists()
        assert not (home / ".local/bin/veilbreaker").is_symlink()
        assert not (home / "data/applications/veilbreaker.desktop").exists()
        assert sentinel.read_text(encoding="utf-8") == "keep"
    report = root / "test-artifacts/linux-installer-report.json"
    report.write_text(json.dumps({"passed": True, "checks": ["install", "CLI launch", "reinstall", "uninstall", "data preservation"]}), encoding="utf-8")
