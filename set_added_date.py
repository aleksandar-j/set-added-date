
from aqt import mw
from aqt.utils import showInfo, getText

import datetime

debug = False

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
    if debug:
        showInfo(f"Card IDs: {card_ids}\nNote IDs: {note_ids}")
    
    user_input, succeeded = getText("Enter new added date. Examples of acceptable values are '2020-01-24' or '2019-05-30 12:45:33'.", 
                                    parent=browser, default=datetime.datetime.now().strftime('%Y-%m-%d'))
    if not succeeded:
        return

    user_input_date = getDateFromString(user_input)
    if not user_input_date:
        return
    user_input_date = int(user_input_date.timestamp()) * 1000
    if debug:
        showInfo(f"New ID start: {user_input_date}")

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

    mw.col.modSchema(check=True)

    mw.reset()
