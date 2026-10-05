import importlib.util
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


class BuildEnvironmentTests(unittest.TestCase):
    @unittest.skipUnless(os.name == "nt", "Windows dependency search")
    def test_freezer_ignores_foreign_native_runtime_paths(self):
        spec = importlib.util.spec_from_file_location("release_builder", Path(__file__).parents[1] / "tools" / "build_release.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with patch.dict(os.environ, {"PATH": "C:/foreign/bin", "QT_PLUGIN_PATH": "C:/foreign/plugins", "QT_QPA_PLATFORM_PLUGIN_PATH": "C:/foreign/qt"}):
            env = module.freezer_environment()
            self.assertNotIn("foreign", env["PATH"])
            self.assertIn(str(Path(sys.executable).parent), env["PATH"])
            self.assertNotIn("QT_PLUGIN_PATH", env)
            self.assertEqual(os.environ["PATH"], "C:/foreign/bin")
