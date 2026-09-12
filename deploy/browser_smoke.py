"""Exercise the image's actual Chrome renderer without any game account."""
import os
import tempfile
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.service import Service

started = time.monotonic()
assert not Path(tempfile.gettempdir()).resolve().is_relative_to('/mnt/workspace'), (
    'Chrome IPC/shared-memory files must use local temporary storage, not OSS/FUSE'
)
browser = next(Path('/m7a/3rdparty/WebBrowser/chrome/linux64').glob('*/chrome'))
driver_path = next(Path('/m7a/3rdparty/WebBrowser/chromedriver/linux64').glob('*/chromedriver'))
options = webdriver.ChromeOptions()
options.binary_location = str(browser)
options.page_load_strategy = 'eager'
for arg in ['--headless=new', '--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu']:
    options.add_argument(arg)
driver = webdriver.Chrome(service=Service(str(driver_path)), options=options)
try:
    driver.set_page_load_timeout(15)
    driver.get('data:text/html,<title>browser-smoke</title><h1>ready</h1><iframe srcdoc="<p>frame-ready</p>"></iframe>')
    assert driver.title == 'browser-smoke'
    assert driver.execute_script('return document.querySelector("h1").textContent') == 'ready'
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {'source': 'window.smokeReady = true', 'runImmediately': True})
    driver.switch_to.frame(driver.find_element('tag name', 'iframe'))
    assert driver.find_element('tag name', 'p').text == 'frame-ready'
    driver.switch_to.default_content()
    assert driver.get_screenshot_as_png().startswith(b'\x89PNG')
    # Exercise the production selectors in real Chrome, including hidden stale DOM.
    import importlib.util
    spec = importlib.util.spec_from_file_location('cloud_queue', '/m7a/module/game/cloud_queue.py')
    queue = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(queue)
    cases = [
        ('<div class="waiting-in-queue">queue</div>', 'in_queue', True),
        ('<div class="game-player">game</div>', 'game_running', True),
        ('<div class="game-player" style="display:none">old</div>', 'unknown', False),
        ('<div class="wel-card__content--start">start</div>', 'unknown', True),
        ('<div role="dialog">连接中断</div><div class="game-player">game</div>', 'disconnected', True),
        ('<div role="dialog">等待时间较长<button onclick="window.clicked=true">继续等待</button></div>', 'continue_waiting', False),
    ]
    for html, state, ready in cases:
        driver.execute_script('document.body.innerHTML = arguments[0]', html)
        assert driver.execute_script(queue.QUEUE_STATE_SCRIPT) == state, state
        assert driver.execute_script(queue.PAGE_READY_SCRIPT) == ready, state
    assert driver.execute_script('return window.clicked') is True
    print(f'Chrome renderer, CDP, iframe and screenshot passed in {time.monotonic() - started:.1f}s')
finally:
    driver.quit()
