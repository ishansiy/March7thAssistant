"""Observe cloud queue transitions without treating missing UI as success."""
import time


QUEUE_STATE_SCRIPT = """
const visible = el => !!el && el.getClientRects().length > 0;
const find = selector => [...document.querySelectorAll(selector)].find(visible);
const dialogs = [...document.querySelectorAll('[role="dialog"], .el-dialog')].filter(visible);
for (const dialog of dialogs) {
    const text = dialog.innerText || '';
    if (text.includes('网络错误') && text.includes('当前网络异常')) return 'network_error';
    if (text.includes('连接中断') || text.includes('已中断连接')) return 'disconnected';
    if (text.includes('等待时间较长')) {
        const button = [...dialog.querySelectorAll('button, [role="button"], .el-button')]
            .find(el => visible(el) && el.textContent.trim() === '继续等待');
        if (button) { button.click(); return 'continue_waiting'; }
    }
}
if (find('[aria-labelledby*="请选择排队队列"]')) return 'select_queue';
if (find('[class*="waiting-in-queue"]')) return 'in_queue';
if (find('.game-player')) return 'game_running';
return 'unknown';
"""

PAGE_READY_SCRIPT = """
const visible = el => !!el && el.getClientRects().length > 0;
return [...document.querySelectorAll(
    '.game-player, [class*="waiting-in-queue"], [aria-labelledby*="请选择排队队列"], '
    + 'div.wel-card__content--start, #mihoyo-login-platform-iframe'
)].some(visible);
"""


def wait_in_queue(controller, timeout, *, clock=time.monotonic, sleep=time.sleep):
    deadline = clock() + timeout
    unknown_since = None
    last_status = None
    selections = 0
    network_retries = 0
    while clock() < deadline:
        status = controller.driver.execute_script(QUEUE_STATE_SCRIPT)
        if status != last_status:
            controller.log_info(f"云游戏排队状态: {status}")
            last_status = status
        if status == 'disconnected':
            raise ConnectionError('云游戏连接已中断')
        if status == 'network_error':
            network_retries += 1
            if network_retries > 3:
                raise ConnectionError('云游戏服务持续返回网络错误，三次间隔重试均失败')
            delay = 30 * (2 ** (network_retries - 1))
            controller.log_info(f'云游戏服务提示网络错误，{delay} 秒后在当前浏览器重试（{network_retries}/3）')
            dismissed = controller.driver.execute_script("""
                const dialog = [...document.querySelectorAll('[role="dialog"]')]
                    .find(el => el.getClientRects().length && el.innerText.includes('网络错误')
                        && el.innerText.includes('当前网络异常'));
                if (!dialog) return false;
                const button = [...dialog.querySelectorAll('button')]
                    .find(el => el.textContent.trim() === '好的');
                if (!button) return false;
                button.click();
                return true;
            """)
            if not dismissed:
                raise ConnectionError('无法关闭网络错误提示')
            sleep(min(delay, max(0, deadline - clock())))
            if clock() >= deadline:
                break
            controller._click_enter_game()
            unknown_since = None
            continue
        if status == 'game_running':
            if not controller._wait_game_canvas_ready():
                raise TimeoutError('游戏容器出现，但画面未加载')
            return True
        if status == 'select_queue':
            selections += 1
            if selections > 4:
                raise TimeoutError('选择排队队列无响应')
            paid = controller.cfg.cloud_game_use_paid_time and getattr(controller, '_paid_time', 0) > 0
            controller.driver.execute_script("""
                const items = document.getElementsByClassName('coin-prior-choose-item-include-info');
                const item = items[arguments[0]];
                if (item && item.getClientRects().length) item.click();
            """, 0 if paid else 1)
            controller.log_info('选择快速队列' if paid else '选择普通队列')
        if status == 'unknown':
            if unknown_since is None:
                unknown_since = clock()
            if clock() - unknown_since >= 60:
                raise TimeoutError('60 秒内未检测到排队、队列选择或游戏界面')
        else:
            unknown_since = None
        sleep(2)
    raise TimeoutError(f'排队超时（上限 {timeout // 60} 分钟）')
