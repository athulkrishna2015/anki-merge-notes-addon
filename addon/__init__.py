from aqt import mw
from aqt.qt import *
from aqt.utils import showInfo
from aqt.browser import Browser
from aqt import gui_hooks

from .gui import show_merge_dialog

def on_merge_notes(browser: Browser):
    selected_notes = browser.selectedNotes()
    if not selected_notes:
        showInfo("Please select at least one note.", parent=browser)
        return
        
    show_merge_dialog(browser, selected_notes)

def setup_browser_menu(browser: Browser):
    menu = browser.form.menu_Notes
    action = QAction("Merge Notes...", browser)
    action.triggered.connect(lambda: on_merge_notes(browser))
    # Add a separator and then our action
    menu.addSeparator()
    menu.addAction(action)

def on_browser_context_menu_init(browser: Browser, menu: QMenu):
    action = menu.addAction("Merge Notes...")
    action.triggered.connect(lambda: on_merge_notes(browser))

gui_hooks.browser_menus_did_init.append(setup_browser_menu)
gui_hooks.browser_will_show_context_menu.append(on_browser_context_menu_init)

def check_and_show_support_on_startup():
    addon_id = __name__.split('.')[0]
    
    # Ensure Anki is fully loaded, visible, and not showing any modal dialogs/sync windows
    if not mw.isVisible() or QApplication.activeModalWidget() is not None:
        QTimer.singleShot(1000, check_and_show_support_on_startup)
        return

    try:
        if mw.progress.busy():
            QTimer.singleShot(1000, check_and_show_support_on_startup)
            return
    except Exception:
        pass

    import os
    try:
        base_dir = os.path.dirname(__file__)
        version_path = os.path.join(base_dir, "VERSION")
        with open(version_path, "r", encoding="utf-8") as f:
            version = f.read().strip()
    except Exception:
        version = "1.3.0"

    config = mw.addonManager.getConfig(addon_id) or {}
    if config.get("i_have_supported", False):
        return

    # Check if the user opted out via the checkbox stored in addon metadata
    try:
        meta = mw.addonManager.addonMeta(addon_id) or {}
        if meta.get("supporter_opt_out", False):
            return
    except Exception:
        pass

    last_shown = config.get("last_shown_support_version", "")
    if last_shown == version:
        return

    config["last_shown_support_version"] = version
    mw.addonManager.writeConfig(addon_id, config)

    from .gui import show_config
    show_config(addon_id, start_tab_name="Support")

def on_profile_did_open():
    QTimer.singleShot(1000, check_and_show_support_on_startup)

gui_hooks.profile_did_open.append(on_profile_did_open)

from .gui import show_config
mw.addonManager.setConfigAction(__name__, lambda: show_config(__name__))

