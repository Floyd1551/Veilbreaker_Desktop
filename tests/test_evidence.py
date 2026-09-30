import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from veilbreaker.cli import main
from veilbreaker.evidence import MANIFEST, verify_bundle
from veilbreaker.jobs import execute, DEMO_METRICS


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        source = self.root / "input.json"
        source.write_text(json.dumps(DEMO_METRICS), encoding="utf-8")
        result = execute({"action": "analyze", "config": {"data_dir": str(self.root), "site_id": "東京"}, "input": str(source)})
        self.pack = Path(result["evidence_zip"])

    def rewrite(self, change):
        with zipfile.ZipFile(self.pack) as archive:
            contents = {n: archive.read(n) for n in archive.namelist()}
        change(contents)
        with zipfile.ZipFile(self.pack, "w") as archive:
            for name, data in contents.items():
                archive.writestr(name, data)

    def test_new_bundle_and_cli_verify(self):
        result = verify_bundle(self.pack)
        self.assertEqual(result["status"], "verified")
        self.assertEqual(result["metadata"]["site_id"], "東京")
        with patch("sys.stdout", io.StringIO()):
            self.assertEqual(main(["verify", str(self.pack)]), 0)

    def test_modified_missing_and_extra_files_fail(self):
        original = self.pack.read_bytes()
        for mutate in (lambda c: c.update({"metrics.json": b"{}"}), lambda c: c.pop("report.txt"), lambda c: c.update({"extra.txt": b"extra"})):
            self.pack.write_bytes(original)
            self.rewrite(mutate)
            self.assertEqual(verify_bundle(self.pack)["status"], "failed")

    def test_legacy_bundle_is_not_claimed_verified(self):
        self.rewrite(lambda c: c.pop(MANIFEST))
        self.assertEqual(verify_bundle(self.pack)["status"], "unverified")
        with patch("sys.stdout", io.StringIO()):
            self.assertEqual(main(["verify", str(self.pack)]), 2)

    def test_invalid_manifests_fail_cleanly(self):
        original = self.pack.read_bytes()
        for invalid in (b"[]", b"null", b"{", b'{"schema_version": 99}', b'{"schema_version": 1, "files": []}'):
            self.pack.write_bytes(original)
            self.rewrite(lambda c: c.update({MANIFEST: invalid}))
            self.assertEqual(verify_bundle(self.pack)["status"], "failed")

    def test_unexpected_paths_and_duplicate_entries_fail(self):
        self.rewrite(lambda c: c.update({"../outside": b"bad"}))
        self.assertEqual(verify_bundle(self.pack)["status"], "failed")
        with zipfile.ZipFile(self.pack, "w") as archive:
            archive.writestr("file", "one")
            with self.assertWarns(UserWarning):
                archive.writestr("file", "two")
        self.assertEqual(verify_bundle(self.pack)["status"], "failed")

    def test_worker_verification_and_corrupt_archive(self):
        result = execute({"action": "verify", "config": {}, "input": str(self.pack)})
        self.assertEqual(result["returncode"], 0)
        self.pack.write_bytes(b"not a zip")
        self.assertEqual(verify_bundle(self.pack)["status"], "failed")

    def test_size_limit_is_enforced(self):
        with patch("veilbreaker.evidence.MAX_BYTES", 1):
            self.assertEqual(verify_bundle(self.pack)["status"], "failed")
