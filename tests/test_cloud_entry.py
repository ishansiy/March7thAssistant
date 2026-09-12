"""Regression cases from the actual cloud-run OCR logs, without game imports."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock

spec = importlib.util.spec_from_file_location(
    'cloud_entry', Path(__file__).resolve().parents[1] / 'tasks/game/cloud_entry.py')
entry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(entry)


class ObservedScreen:
    def __init__(self, texts, old_image=False):
        self.texts, self.old_image, self.clicks = texts, old_image, []

    def find_element(self, targets, kind, **kwargs):
        return any(target in text for target in targets for text in self.texts)

    def click_element(self, target, kind, *args, **kwargs):
        found = self.old_image if kind == 'image' else any(text in target for text in self.texts)
        if found:
            self.clicks.append(kind)
        return found


class CloudEntryTests(unittest.TestCase):
    def test_observed_new_title_screen_enters_without_old_image(self):
        screen = ObservedScreen(['设置', '开始游戏', '星穹列车'])
        self.assertTrue(entry.click_cloud_entry(screen, Mock()))
        self.assertEqual(screen.clicks, ['text'])

    def test_old_entry_artwork_remains_supported(self):
        screen = ObservedScreen([], old_image=True)
        self.assertTrue(entry.click_cloud_entry(screen, Mock()))
        self.assertEqual(screen.clicks, ['image'])

    def test_idle_disconnect_triggers_reconnect_before_click(self):
        screen = ObservedScreen(['连接中断', '因为您长时间未操作游戏，已中断连接',
                                 '错误码：-1022', '退出游戏'], old_image=True)
        with self.assertRaises(ConnectionError):
            entry.click_cloud_entry(screen, Mock())
        self.assertEqual(screen.clicks, [])

    def test_loading_screen_is_not_mistaken_for_entry(self):
        self.assertFalse(entry.click_cloud_entry(ObservedScreen(['正在加载']), Mock()))


if __name__ == '__main__':
    unittest.main()
