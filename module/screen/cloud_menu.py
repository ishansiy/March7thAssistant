"""Recover a missed Escape transition only from a confirmed game home screen."""
def recover_phone_menu(auto, target, cloud_enabled):
    if not cloud_enabled or target != 'menu':
        return False
    # Match a fresh frame and click the matched phone icon, not fixed coordinates.
    return bool(auto.click_element('./assets/images/screen/main.png', 'image', 0.95))
