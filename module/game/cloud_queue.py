"""Observe cloud queue transitions without treating missing UI as success."""
import time


QUEUE_STATE_SCRIPT = """
const visible = el => !!el && el.getClientRects().length > 0;
const find = selector => [...document.querySelectorAll(selector)].find(visible);
const dialogs = [...document.querySelectorAll('[role="dialog"], .el-dialog')].filter(visible);
for (const dialog of dialogs) {
    const text = dialog.innerText || '';
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
    while clock() < deadline:
        status = controller.driver.execute_script(QUEUE_STATE_SCRIPT)
        if status != last_status:
            controller.log_info(f"云游戏排队状态: {status}")
            last_status = status
        if status == 'disconnected':
            raise ConnectionError('云游戏连接已中断')
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
