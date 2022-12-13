# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from aqt import mw
from aqt.utils import showWarning, getText

import datetime

PROMPT_TEXT = \
"""Enter new added date.
2020-01-24 = sets added date to '2020-01-24 00:00:00'
2019-05-30 12:45:33 = sets added date to '2019-05-30 12:45:33'
+195 = adds 195 seconds to added date"""

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

def getStringFromTimestamp(stamp):
    return datetime.datetime.fromtimestamp(stamp // 1000).strftime('%Y-%m-%d %H:%M:%S')

def getAddSeconds(string):
    is_add = string[0] in ['+', '-'] and string[1:].isnumeric()
    if not is_add:
        return None
    try:
        number = int(string[1:])
    except:
        return None
    return number if string[0] == '+' else -number

def setAddedDate(browser):
    if not browser.selectedCards():
        return

    card_ids = browser.selectedCards()
    cards = [mw.col.getCard(id) for id in card_ids]
    note_ids = list(set(card.nid for card in cards))

    prompt = PROMPT_TEXT
    if len(note_ids) == 1:
        prompt_add = f"Note added date: {getStringFromTimestamp(cards[0].nid)}\n"
        if len(card_ids) == 1:
            prompt_add += f"Card added date: {getStringFromTimestamp(cards[0].id)}\n"
        prompt = prompt_add + "\n" + prompt
    
    user_input, succeeded = getText(prompt, parent=browser, 
                                    default=datetime.datetime.now().strftime('%Y-%m-%d'))
    if not succeeded:
        return

    user_input_add = getAddSeconds(user_input)
    user_input_date = getDateFromString(user_input)

    if user_input_add:
        user_input_add = user_input_add * 1000
        card_id_to_new_date = {card_id : card_id + user_input_add for card_id in card_ids}
        note_id_to_new_date = {note_id : note_id + user_input_add for note_id in note_ids}
    elif user_input_date:
        user_input_date = int(user_input_date.timestamp()) * 1000
        card_id_to_new_date = {card_id : user_input_date for card_id in card_ids}
        note_id_to_new_date = {note_id : user_input_date for note_id in note_ids}
    else:
        showWarning("Invalid input.")
        return

    for card_id in card_ids:
        if mw.col.db.scalar("SELECT id FROM revlog WHERE cid=? AND id<?", card_id, card_id_to_new_date[card_id]):
            showWarning(f"Card with ID '{card_id}' has review(s) before new added date. Aborting...")
            return

    mw.col.modSchema(check=True)

    for note_id in note_ids:
        while mw.col.db.scalar("SELECT id FROM notes WHERE id=?", note_id_to_new_date[note_id]):
            note_id_to_new_date[note_id] += 1
        mw.col.db.execute("UPDATE notes SET id=? WHERE id=?", note_id_to_new_date[note_id], note_id)
        mw.col.db.execute("UPDATE cards SET nid=? WHERE nid=?", note_id_to_new_date[note_id], note_id)

    for card_id in card_ids:
        while mw.col.db.scalar("SELECT id FROM cards WHERE id=?", card_id_to_new_date[card_id]):
            card_id_to_new_date[card_id] += 1
        mw.col.db.execute("UPDATE cards SET id=? WHERE id=?", card_id_to_new_date[card_id], card_id)
        mw.col.db.execute("UPDATE revlog SET cid=? WHERE cid=?", card_id_to_new_date[card_id], card_id)

    mw.reset()
