"""Deploy a tested image to the existing free Studio; never interrupt a task."""
import base64
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time
import urllib.request

STUDIO = 'https://www.modelscope.ai/openapi/v1/studios/udfca7deb/March7thAssistant'
APP = 'https://udfca7deb-march7thassistant.ms.fun'


def request(url, header, method='GET'):
    req = urllib.request.Request(url, headers=header, method=method)
    with urllib.request.urlopen(req, timeout=25) as response:
        return json.load(response)


def summary(message):
    print(message)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as f:
            f.write(message + '\n')


def main():
    digest = os.environ['IMAGE_DIGEST']
    if not re.fullmatch(r'sha256:[a-f0-9]{64}', digest):
        raise ValueError('Invalid validated image digest')
    token = os.environ['MODELSCOPE_API_KEY']
    web_token = os.environ['WEBUI_TOKEN']
    if not token or not web_token:
        raise ValueError('Deployment secrets are missing')
    headers = {'Authorization': 'Bearer ' + token}
    web_headers = {'X-M7A-Token': 'Bearer ' + web_token}
    info = request(STUDIO, headers)['data']
    if info['hardware'] != 'platform/2v-cpu-16g-mem':
        raise RuntimeError('Hardware changed; refusing automatic deployment')
    if info['status'] != 'Running':
        summary('Deployment deferred: Studio is not Running. Next daily run will retry.')
        return
    state = request(APP + '/api/status', web_headers)
    if state.get('running') or state.get('waiting_for_retry'):
        summary('Deployment deferred: game task is active. Next daily run will retry.')
        return
    env = os.environ.copy()
    env.update(GIT_CONFIG_COUNT='1', GIT_CONFIG_KEY_0='http.extraHeader',
               GIT_CONFIG_VALUE_0='Authorization: Basic ' + base64.b64encode(('oauth2:' + token).encode()).decode())
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / 'studio'
        def git(*args):
            return subprocess.check_output(['git', '-C', str(repo), *args], env=env, text=True).strip()
        subprocess.run(['git', 'clone', '--depth=1',
                        'https://www.modelscope.ai/studios/udfca7deb/March7thAssistant.git', str(repo)],
                       env=env, check=True)
        dockerfile = repo / 'Dockerfile'
        previous = dockerfile.read_text()
        updated = f'FROM ghcr.io/ishansiy/march7thassistant@{digest}\nEXPOSE 7860\n'
        if previous == updated:
            summary('Studio already references this image; no restart needed.')
            return
        # Recheck immediately before changing the deployment repository.
        if request(APP + '/api/status', web_headers).get('running'):
            summary('Deployment deferred: a task started during preparation.')
            return
        git('config', 'user.name', 'github-actions[bot]')
        git('config', 'user.email', '41898282+github-actions[bot]@users.noreply.github.com')
        previous_commit = git('rev-parse', 'HEAD')
        dockerfile.write_text(updated)
        git('add', 'Dockerfile')
        git('commit', '-m', 'Deploy validated image ' + digest)
        git('push', 'origin', 'HEAD:master')
        result = request(STUDIO + '/deploy', headers, 'POST')
        if not result.get('success'):
            raise RuntimeError('Studio deployment request failed')
        summary(f'Deploying {digest}. Previous Studio commit for rollback: {previous_commit}')
    for _ in range(40):
        time.sleep(15)
        state = request(STUDIO, headers)['data']['status']
        if state == 'Running':
            if request(APP + '/healthz', {})['status'] == 'ok':
                request(APP + '/api/status', web_headers)
                summary('Deployment is Running; health and authenticated API checks passed. Game completion is not asserted.')
                return
        if state in ('Failed', 'BuildFailed', 'RuntimeError', 'Stopped'):
            raise RuntimeError('Studio deployment failed: ' + state)
    raise TimeoutError('Studio did not become healthy within 10 minutes')


if __name__ == '__main__':
    main()
