# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from aqt import gui_hooks
from aqt.qt import QAction

from . import set_added_date

def setupAction(browser):
    actionEditAddedDate = QAction("Set Added Date...", browser)
    actionEditAddedDate.triggered.connect(lambda: set_added_date.setAddedDate(browser))

    browser.form.menu_Cards.insertAction(browser.form.menu_Cards.actions()[2], actionEditAddedDate)

gui_hooks.browser_menus_did_init.append(setupAction)
