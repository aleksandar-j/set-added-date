# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from aqt import mw
from aqt.utils import showWarning, getText, askUser

import datetime

PROMPT_TEXT = \
"""Enter new added date.
2020-01-24 = sets added date to '2020-01-24 00:00:00'
2019-05-30 12:45:33 = sets added date to '2019-05-30 12:45:33'
+195 = adds 195 seconds to added date"""

def getDateFromString(string):
    try: return datetime.datetime.strptime(string, '%Y-%m-%d %H:%M:%S')
    except: pass
    
    try: return datetime.datetime.strptime(string, '%Y-%m-%d')
    except: pass
    
    return None

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

class SelectedInfo:
    def __init__(self, selected_cards):
        self.cids = selected_cards
        
        _cid_to_card = {cid:mw.col.getCard(cid) for cid in self.cids}
        self.nids = list(dict.fromkeys(_cid_to_card[cid].nid for cid in self.cids))
        self.nid_to_cids = {nid:[cid for cid in self.cids if _cid_to_card[cid].nid == nid] for nid in self.nids}
        
        _nid_to_note = {nid:_cid_to_card[self.nid_to_cids[nid][0]].note() for nid in self.nids}
        _nid_to_cards = {nid:_nid_to_note[nid].cards() for nid in self.nids}
        self.nids_edit = {nid for nid in self.nids if len(_nid_to_cards[nid]) == len(self.nid_to_cids[nid])}
        self.nids_keep = {nid for nid in self.nids if not nid in self.nids_edit}

class ChangeInfo:
    def __init__(self):
        self.nid_to_new_nid = {}
        self.cid_to_new_cid = {}

def isUsedNID(nid, used=None):
    return (not used is None and nid in used) or \
           mw.col.db.scalar("SELECT id FROM notes WHERE id=?", nid)
def isUsedCID(cid, used=None):
    return (not used is None and cid in used) or \
           mw.col.db.scalar("SELECT id FROM cards WHERE id=?", cid) or \
           mw.col.db.scalar("SELECT cid FROM revlog WHERE cid=?", cid)
def isUsedRangeCID(cid_low, cid_high, used=None):
    return (not used is None and any(cid_low <= x <= cid_high for x in used)) or \
           mw.col.db.scalar("SELECT id FROM cards WHERE id BETWEEN ? AND ?", cid_low, cid_high) or \
           mw.col.db.scalar("SELECT cid FROM revlog WHERE cid BETWEEN ? AND ?", cid_low, cid_high)

def computeNewDatesAdd(add, selected_info):
    change_info = ChangeInfo()

    change_info.nid_to_new_nid = {nid : 0 for nid in selected_info.nids}
    change_info.cid_to_new_cid = {cid : 0 for cid in selected_info.cids}

    for nid in selected_info.nids:
        used_ids = set(change_info.nid_to_new_nid.values()) | set(change_info.cid_to_new_cid.values())

        new_nid = nid + add
        while isUsedNID(new_nid, used=used_ids):
            new_nid += 1
        change_info.nid_to_new_nid[nid] = new_nid

        for cid in selected_info.nid_to_cids[nid]:
            new_cid = cid + add
            while isUsedCID(new_cid, used=used_ids):
                new_cid += 1
            change_info.cid_to_new_cid[cid] = new_cid

            used_ids.add(new_cid)

    return change_info

def computeNewDatesSet(date, selected_info):
    change_info = ChangeInfo()

    change_info.nid_to_new_nid = {nid : date for nid in selected_info.nids}
    change_info.cid_to_new_cid = {cid : date for cid in selected_info.cids}

    for nid in selected_info.nids:
        used_ids = set(change_info.nid_to_new_nid.values()) | set(change_info.cid_to_new_cid.values())

        new_nid = max(used_ids) + 1
        while isUsedNID(new_nid, used=used_ids) or \
              isUsedRangeCID(new_nid, new_nid+len(selected_info.nid_to_cids[nid]), used=used_ids):
            new_nid += 1
        change_info.nid_to_new_nid[nid] = new_nid

        for i, cid in enumerate(selected_info.nid_to_cids[nid]):
            change_info.cid_to_new_cid[cid] = new_nid + i

    return change_info

def computeNewDates(user_input, selected_info):
    user_input_add = getAddSeconds(user_input)
    if user_input_add:
        add = user_input_add * 1000
        return computeNewDatesAdd(add, selected_info)
    
    user_input_date = getDateFromString(user_input)
    if user_input_date:
        date = int(user_input_date.timestamp()) * 1000
        return computeNewDatesSet(date, selected_info)
    
    return None

def validateNewDates(selected_info, change_info):
    for cid in selected_info.cids:
        if mw.col.db.scalar("SELECT id FROM revlog WHERE cid=? AND id<?", cid, change_info.cid_to_new_cid[cid]):
            timeline_errors_msg = f"Cards with IDs [{cid}, ...] have review(s) before new added date. Continue for all?"
            timeline_errors_continue = askUser(timeline_errors_msg, defaultno=True, title="Set Added Date Timeline Warning")
            if timeline_errors_continue == False:
                return False
            break

    for nid in selected_info.nids_keep:
        if min(change_info.cid_to_new_cid[cid] for cid in selected_info.nid_to_cids[nid]) < nid:
            timeline_errors_msg = f"Partial notes with IDs [{nid}, ...] have some cards with IDs before new note ID. Continue for all?"
            timeline_errors_continue = askUser(timeline_errors_msg, defaultno=True, title="Set Added Date Timeline Warning")
            if timeline_errors_continue == False:
                return False
            break

    return True

def executeSQL(selected_info, change_info):
    mw.col.modSchema(check=True)

    for nid in selected_info.nids:
        if nid in selected_info.nids_edit:
            while isUsedNID(change_info.nid_to_new_nid[nid]):
                change_info.nid_to_new_nid[nid] += 1 # NOTE: Should never hit, fail-safe
            mw.col.db.execute("UPDATE notes SET id=? WHERE id=?", change_info.nid_to_new_nid[nid], nid)
            mw.col.db.execute("UPDATE cards SET nid=? WHERE nid=?", change_info.nid_to_new_nid[nid], nid)
        for cid in selected_info.nid_to_cids[nid]:
            while isUsedCID(change_info.cid_to_new_cid[cid]):
                change_info.cid_to_new_cid[cid] += 1 # NOTE: Should never hit, fail-safe
            mw.col.db.execute("UPDATE cards SET id=? WHERE id=?", change_info.cid_to_new_cid[cid], cid)
            mw.col.db.execute("UPDATE revlog SET cid=? WHERE cid=?", change_info.cid_to_new_cid[cid], cid)

    mw.reset()

def setAddedDate(browser):
    if not browser.selectedCards():
        return

    selected_info = SelectedInfo(browser.selectedCards())

    if selected_info.nids_keep and len(selected_info.nids) > 1:
        warning_msg = f"Some notes selected partially (not all their cards selected). Only selected cards will get new date. Continue?"
        warning_continue = askUser(warning_msg, defaultno=True, title="Set Added Date Warning")
        if warning_continue == False:
            return False

    prompt = PROMPT_TEXT
    if len(selected_info.nids) == 1:
        prompt_add = f"Note added date: {getStringFromTimestamp(selected_info.nids[0])}\n"
        if len(selected_info.cids) == 1:
            prompt_add += f"Card added date: {getStringFromTimestamp(selected_info.cids[0])}\n"
        prompt = prompt_add + "\n" + prompt
    user_input, succeeded = getText(prompt, parent=browser, default=datetime.datetime.now().strftime('%Y-%m-%d'))
    if not succeeded:
        return

    change_info = computeNewDates(user_input, selected_info)
    if change_info is None:
        showWarning("Invalid input.")
        return

    if not validateNewDates(selected_info, change_info):
        return
    
    executeSQL(selected_info, change_info)
