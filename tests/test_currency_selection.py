"""Exercise the actual selection handler without launching the game."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock


class SelectionTests(unittest.TestCase):
    def setUp(self):
        source = Path(__file__).resolve().parents[1] / 'tasks/weekly/currency_wars.py'
        tree = ast.parse(source.read_text(encoding='utf-8'))
        method = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
                      and n.name == 'check_investment_environment')
        self.visible = True
        self.auto = Mock(matched_text='投资环境')
        self.auto.find_element.side_effect = lambda target, *a, **k: self.visible if isinstance(target, tuple) else False
        self.auto.click_element.return_value = False
        namespace = dict(auto=self.auto, log=Mock(), time=Mock(), os=Mock(), cfg=SimpleNamespace(currencywars_strategy='default'))
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(source), 'exec'), namespace)
        self.handle = namespace['check_investment_environment']
        self.subject = SimpleNamespace(_get_ocr_texts_in_crop=lambda pos: [],
                                       _find_text_in_texts=lambda *a, **k: None,
                                       check_special_characters=Mock(),
                                       confirm_investment_choice=Mock(return_value=False))
        confirm = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
                       and n.name == 'confirm_investment_choice')
        exec(compile(ast.Module(body=[confirm], type_ignores=[]), str(source), 'exec'), namespace)
        self.confirm = namespace['confirm_investment_choice']

    def test_unchanged_page_stops_after_three_attempts(self):
        for _ in range(3):
            self.assertIsNone(self.handle(self.subject))
        clicks = self.auto.click_element.call_count
        self.assertIs(self.handle(self.subject), False)
        self.assertEqual(self.auto.click_element.call_count, clicks)
        self.assertEqual(self.auto.screenshot.save.call_count, 2)

    def test_leaving_page_resets_attempt_budget(self):
        self.handle(self.subject)
        self.visible = False
        self.handle(self.subject)
        self.assertEqual(self.subject._selection_attempts, 0)
        self.visible = True
        self.handle(self.subject)
        self.assertEqual(self.subject._selection_attempts, 1)

    def test_default_option_uses_same_confirmation_path(self):
        self.handle(self.subject)
        self.subject.confirm_investment_choice.assert_called_once()
        self.subject.check_special_characters.assert_not_called()

    def test_stale_page_does_not_apply_rewards(self):
        self.auto.click_element.return_value = True
        self.auto.find_element.side_effect = None
        self.auto.find_element.return_value = True
        self.assertFalse(self.confirm(self.subject, ['能量概念股'], (0,0,1,1), (0,0,1,1), '投资环境'))
        self.subject.check_special_characters.assert_not_called()

    def test_title_click_and_two_absent_frames_confirm_selection(self):
        self.auto.click_element.return_value = True
        self.auto.find_element.side_effect = [False, True, False, False]
        self.assertTrue(self.confirm(self.subject, ['能量概念股'], (0,0,1,1), (0,0,1,1), '投资环境'))
        self.assertEqual(self.auto.find_element.call_count, 4)
        self.assertEqual(self.auto.click_element.call_args_list[0].args, ('能量概念股', 'text'))
        self.subject.check_special_characters.assert_called_once_with(texts=['能量概念股'])

    def test_missing_confirm_button_does_not_apply_rewards(self):
        self.auto.click_element.side_effect = [True, False]
        self.assertFalse(self.confirm(self.subject, ['能量概念股'], (0,0,1,1), (0,0,1,1), '投资环境'))
        self.subject.check_special_characters.assert_not_called()


if __name__ == '__main__':
    unittest.main()
