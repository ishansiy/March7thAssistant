import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock

spec = importlib.util.spec_from_file_location('cloud_storage', Path(__file__).resolve().parents[1] / 'module/game/cloud_storage.py')
storage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(storage)


class StorageTests(unittest.TestCase):
    def test_blank_document_is_navigated_before_storage_access(self):
        driver = Mock()
        driver.execute_script.side_effect = [False, True]
        wait = Mock()
        wait.until.side_effect = lambda predicate: self.assertTrue(predicate(driver))
        storage.ensure_game_storage(driver, 'https://example.test/game', wait)
        driver.get.assert_called_once_with('https://example.test/game')

    def test_existing_game_origin_is_not_reloaded(self):
        driver = Mock()
        driver.execute_script.return_value = True
        wait = Mock()
        wait.until.side_effect = lambda predicate: self.assertTrue(predicate(driver))
        storage.ensure_game_storage(driver, 'https://example.test/game', wait)
        driver.get.assert_not_called()


if __name__ == '__main__':
    unittest.main()
