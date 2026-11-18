import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


class BuildEnvironmentTests(unittest.TestCase):
    def load_builder(self):
        spec = importlib.util.spec_from_file_location("release_builder", Path(__file__).parents[1] / "tools" / "build_release.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_source_modules_are_isolated_and_failures_stop_the_build(self):
        module = self.load_builder()
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / 'test_a.py').touch()
            (folder / 'test_b.py').touch()
            (folder / 'notes.py').touch()
            with patch.object(module, 'run') as runner:
                names = module.run_source_tests(folder)
            self.assertEqual(names, ['test_a.py', 'test_b.py'])
            self.assertEqual(runner.call_count, 2)
            self.assertEqual([call.args[-1] for call in runner.call_args_list], names)
            self.assertTrue(all(call.kwargs['timeout'] == 180 for call in runner.call_args_list))
            with patch.object(module, 'run', side_effect=RuntimeError('failed')):
                with self.assertRaisesRegex(RuntimeError, 'failed'):
                    module.run_source_tests(folder)

    def test_source_discovery_rejects_duplicate_names_and_empty_suite(self):
        module = self.load_builder()
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            with self.assertRaisesRegex(RuntimeError, 'No source test'):
                module.run_source_tests(folder)
            (folder / 'test_a.py').touch()
            nested = folder / 'nested'
            nested.mkdir()
            (nested / '__init__.py').touch()
            (nested / 'test_a.py').touch()
            with self.assertRaisesRegex(RuntimeError, 'Duplicate'):
                module.run_source_tests(folder)

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
