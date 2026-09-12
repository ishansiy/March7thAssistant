import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

spec = importlib.util.spec_from_file_location('cloud_queue', Path(__file__).resolve().parents[1] / 'module/game/cloud_queue.py')
queue = importlib.util.module_from_spec(spec)
spec.loader.exec_module(queue)


class QueueTests(unittest.TestCase):
    def run_queue(self, states, ready=True, timeout=120):
        now = [0]
        controller = SimpleNamespace(
            driver=Mock(), log_info=Mock(),
            _wait_game_canvas_ready=Mock(return_value=ready),
            cfg=SimpleNamespace(cloud_game_use_paid_time=False),
        )
        values = iter(states)
        last = [states[-1]]
        def execute(script, *args):
            if script == queue.QUEUE_STATE_SCRIPT:
                last[0] = next(values, last[0])
                return last[0]
        controller.driver.execute_script.side_effect = execute
        def sleep(seconds):
            now[0] += seconds
        return queue.wait_in_queue(controller, timeout, clock=lambda: now[0], sleep=sleep)

    def test_delayed_transition_beyond_old_ten_second_limit(self):
        self.assertTrue(self.run_queue(['unknown'] * 10 + ['in_queue', 'game_running']))

    def test_queue_disappearing_is_not_success(self):
        with self.assertRaisesRegex(TimeoutError, '60 秒'):
            self.run_queue(['in_queue', 'unknown'])

    def test_game_container_without_video_is_not_success(self):
        with self.assertRaisesRegex(TimeoutError, '画面未加载'):
            self.run_queue(['game_running'], ready=False)

    def test_disconnect_during_queue(self):
        with self.assertRaises(ConnectionError):
            self.run_queue(['in_queue', 'disconnected'])

    def test_user_queue_limit_is_respected(self):
        with self.assertRaisesRegex(TimeoutError, '排队超时'):
            self.run_queue(['in_queue'], timeout=60)

    def test_queue_selection_and_continue_waiting(self):
        self.assertTrue(self.run_queue(['select_queue', 'in_queue', 'continue_waiting', 'in_queue', 'game_running']))


if __name__ == '__main__':
    unittest.main()
