import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock

spec = importlib.util.spec_from_file_location('cloud_menu', Path(__file__).resolve().parents[1] / 'module/screen/cloud_menu.py')
menu = importlib.util.module_from_spec(spec)
spec.loader.exec_module(menu)


class MenuRecoveryTests(unittest.TestCase):
    def test_known_phone_icon_is_clicked(self):
        auto = Mock()
        auto.click_element.return_value = True
        self.assertTrue(menu.recover_phone_menu(auto, 'menu', True))

    def test_other_screens_do_not_trigger_recovery(self):
        auto = Mock()
        self.assertFalse(menu.recover_phone_menu(auto, 'map', True))
        self.assertFalse(menu.recover_phone_menu(auto, 'menu', False))
        auto.click_element.assert_not_called()

    def test_missing_icon_is_not_reported_as_recovered(self):
        auto = Mock()
        auto.click_element.return_value = False
        self.assertFalse(menu.recover_phone_menu(auto, 'menu', True))


if __name__ == '__main__':
    unittest.main()
