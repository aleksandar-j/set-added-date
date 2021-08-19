# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from aqt import mw
from aqt.utils import showWarning, getText

import datetime

def getDateFromString(string):
    date = None

    if not date:
        try:
            date = datetime.datetime.strptime(string, '%Y-%m-%d %H:%M:%S')
        except:
            pass
    if not date:
        try:
            date = datetime.datetime.strptime(string, '%Y-%m-%d')
        except:
            pass
    
    return date

def getNoteIDs(card_ids):
    note_ids = []

    for card_id in card_ids:
        card = mw.col.getCard(card_id)
        if card.nid not in note_ids:
            note_ids.append(card.nid)

    return note_ids

def setAddedDate(browser):
    if not browser.selectedCards():
        return

    card_ids = browser.selectedCards()
    note_ids = getNoteIDs(card_ids)
    
    user_input, succeeded = getText("Enter new added date. Examples of acceptable values are '2020-01-24' or '2019-05-30 12:45:33'.", 
                                    parent=browser, default=datetime.datetime.now().strftime('%Y-%m-%d'))
    if not succeeded:
        return

    user_input_date = getDateFromString(user_input)
    if not user_input_date:
        return
    user_input_date = int(user_input_date.timestamp()) * 1000

    for card_id in card_ids:
        if mw.col.db.scalar("SELECT id FROM revlog WHERE cid=? AND id<?", card_id, user_input_date):
            showWarning(f"Card with ID '{card_id}' has review(s) before new added date. Aborting...")
            return

    date_milliseconds_note = user_input_date
    for note_id in note_ids:
        while mw.col.db.scalar("SELECT id FROM notes WHERE id=?", date_milliseconds_note):
            date_milliseconds_note += 1
        mw.col.db.execute("UPDATE notes SET id=? WHERE id=?", date_milliseconds_note, note_id)
        mw.col.db.execute("UPDATE cards SET nid=? WHERE nid=?", date_milliseconds_note, note_id)

    date_milliseconds_card = user_input_date
    for card_id in card_ids:
        while mw.col.db.scalar("SELECT id FROM cards WHERE id=?", date_milliseconds_card):
            date_milliseconds_card += 1
        mw.col.db.execute("UPDATE cards SET id=? WHERE id=?", date_milliseconds_card, card_id)
        mw.col.db.execute("UPDATE revlog SET cid=? WHERE cid=?", date_milliseconds_card, card_id)

    mw.col.modSchema(check=True)

    mw.reset()
