import importlib.util
import os
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('update_studio', Path(__file__).resolve().parents[1] / 'deploy/update_studio.py')
deploy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deploy)


class DeploymentGuards(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, IMAGE_DIGEST='sha256:' + 'a' * 64,
                              MODELSCOPE_API_KEY='test', WEBUI_TOKEN='test')
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_active_game_is_not_interrupted(self):
        with patch.object(deploy, 'request', side_effect=[
            {'data': {'hardware': 'platform/2v-cpu-16g-mem', 'status': 'Running'}},
            {'running': True},
        ]), patch.object(deploy.subprocess, 'run') as run:
            deploy.main()
            run.assert_not_called()

    def test_paid_hardware_is_rejected(self):
        with patch.object(deploy, 'request', return_value={
            'data': {'hardware': 'paid/example', 'status': 'Running'}
        }), self.assertRaisesRegex(RuntimeError, 'Hardware changed'):
            deploy.main()

    def test_invalid_digest_is_rejected_before_network(self):
        os.environ['IMAGE_DIGEST'] = 'latest'
        with patch.object(deploy, 'request') as request, self.assertRaises(ValueError):
            deploy.main()
        request.assert_not_called()

    def test_unavailable_status_does_not_start_deploy(self):
        with patch.object(deploy, 'request', side_effect=TimeoutError), \
                patch.object(deploy.subprocess, 'run') as run, self.assertRaises(TimeoutError):
            deploy.main()
        run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
