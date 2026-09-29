"""Verify the merged shutdown path without touching real browser processes."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock


class ShutdownTests(unittest.TestCase):
    def setUp(self):
        source = Path(__file__).resolve().parents[1] / 'module/game/cloud.py'
        tree = ast.parse(source.read_text(encoding='utf-8'))
        method = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == 'stop_game')
        self.processes = Mock()
        self.processes.wait_procs.return_value = ([], ['browser'])
        self.os = Mock()
        self.os.path.exists.return_value = False
        namespace = dict(os=self.os, psutil=self.processes, Command=SimpleNamespace(CLOSE='close'))
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(source), 'exec'), namespace)
        self.stop = namespace['stop_game']
        self.controller = Mock()
        self.driver = self.controller.driver
        self.config = SimpleNamespace(timeout=120)
        self.driver.command_executor._client_config = self.config
        self.controller.get_m7a_browsers.return_value = ['browser']

    def test_stalled_driver_still_flushes_and_cleans_up_browser(self):
        def stalled(*args):
            self.assertEqual(self.config.timeout, 15)
            raise TimeoutError('stalled')
        self.driver.execute.side_effect = stalled
        self.driver.quit.side_effect = stalled
        self.assertTrue(self.stop(self.controller))
        self.driver.quit.assert_called_once()
        self.processes.wait_procs.assert_called_once_with(['browser'], timeout=5)
        self.controller.close_all_m7a_browser.assert_called_once()
        self.assertIsNone(self.controller.driver)
        self.assertEqual(self.config.timeout, 120)

    def test_short_timeout_is_preserved(self):
        self.config.timeout = 3
        self.driver.quit.side_effect = lambda: self.assertEqual(self.config.timeout, 3)
        self.assertTrue(self.stop(self.controller))
        self.assertEqual(self.config.timeout, 3)

    def test_without_driver_still_cleans_up_orphaned_browser(self):
        self.controller.driver = None
        self.assertTrue(self.stop(self.controller))
        self.processes.wait_procs.assert_not_called()
        self.controller.close_all_m7a_browser.assert_called_once()


if __name__ == '__main__':
    unittest.main()
