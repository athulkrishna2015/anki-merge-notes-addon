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

from .config_gui import show_config
mw.addonManager.setConfigAction(__name__, lambda: show_config(__name__))

