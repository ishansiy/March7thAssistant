"""Recognize cloud-stream entry and disconnection independently of UI artwork."""

DISCONNECTED_TEXT = ("连接中断", "已中断连接", "错误码：-1022", "错误码:-1022")
ENTRY_TEXT = ("开始游戏", "点击进入")


def raise_if_disconnected(auto):
    if auto.find_element(DISCONNECTED_TEXT, "text", include=True,
                         prefer_frame_screenshot=False):
        raise ConnectionError("云游戏连接已中断，关闭当前会话并重新连接")


def click_cloud_entry(auto, logger):
    # OCR takes one fresh screenshot, reused for the image and text checks.
    # A disconnect must win over any stale entry button behind an overlay.
    raise_if_disconnected(auto)
    if auto.click_element("./assets/images/screen/click_enter.png", "image", 0.9,
                          take_screenshot=False, prefer_frame_screenshot=False):
        return True
    if auto.click_element(ENTRY_TEXT, "text", include=False, need_ocr=False,
                          take_screenshot=False, prefer_frame_screenshot=False):
        logger.info("已通过文字识别点击游戏入口")
        return True
    return False
