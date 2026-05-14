from aqt import gui_hooks
from aqt.qt import QAction, QMenu

from AnkiBulk.i18n import tr

_dialog = None


def main() -> None:
    gui_hooks.browser_menus_did_init.append(_on_browser_menus_init)


def _on_browser_menus_init(browser):
    menu = QMenu(tr("menu-ankibulk"), browser.menuBar())
    browser.menuBar().addMenu(menu)

    action = QAction(tr("menu-bulk-add"), menu)
    action.triggered.connect(lambda: _on_bulk_add(browser))
    menu.addAction(action)

    help_action = QAction(tr("menu-help"), menu)
    help_action.triggered.connect(lambda: _on_help(browser))
    menu.addAction(help_action)


def _on_bulk_add(browser):
    global _dialog
    from AnkiBulk.dialog import Dialog
    from aqt import mw

    if _dialog is not None and _dialog.isVisible():
        _dialog.raise_()
        _dialog.activateWindow()
        return

    _dialog = Dialog(browser, mw)
    _dialog.show()


def _on_help(browser):
    from AnkiBulk.help import Dialog

    dialog = Dialog(browser)
    dialog.exec()
