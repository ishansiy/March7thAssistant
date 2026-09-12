"""Ensure Chrome has reached the game origin before reading its storage."""
STORAGE_READY_SCRIPT = """
try {
    if (location.origin !== new URL(arguments[0]).origin) return false;
    return typeof window.localStorage.length === 'number';
} catch (_) { return false; }
"""


def ensure_game_storage(driver, game_url, wait):
    if not driver.execute_script(STORAGE_READY_SCRIPT, game_url):
        driver.get(game_url)
    wait.until(lambda d: d.execute_script(STORAGE_READY_SCRIPT, game_url))
