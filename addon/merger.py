import re
import time
import json
import html
from aqt.utils import showInfo, askUser
from .logger import logger

AI_HINTS_JSON_PATTERN = re.compile(
    r'<div\b[^>]*class=["\'][^"\']*(?:ai-hints-json)[^"\']*["\'][^>]*>(.*?)</div>',
    flags=re.DOTALL | re.IGNORECASE
)

AI_HINTS_REMOVE_PATTERN = re.compile(
    r'(?:[\s\n\r]|<br\s*/?>|&nbsp;|<div>\s*</div>)*<div\b[^>]*class=["\'][^"\']*(?:ai-hints-json|ai-hints-container)[^"\']*["\'][^>]*>.*?</div>(?:[\s\n\r]|<br\s*/?>|&nbsp;|<div>\s*</div>)*',
    flags=re.DOTALL | re.IGNORECASE
)

def extract_ai_hints(text):
    """
    Extracts AI-Hints payload from a field's HTML string,
    and returns (cleaned_text, parsed_payload, toggles).
    """
    if not isinstance(text, str) or not text.strip():
        return text, {}, {}

    parsed_payloads = []
    show_hints = True
    show_options = True

    # Find all matches of JSON blocks
    for match in AI_HINTS_JSON_PATTERN.finditer(text):
        raw_payload = match.group(1)
        # Extract show/hide options/hints from the div wrapper
        div_start = text.rfind('<div', 0, match.start(1))
        if div_start != -1:
            div_tag = text[div_start:match.start(1)]
            if 'data-show-hints="false"' in div_tag:
                show_hints = False
            if 'data-show-options="false"' in div_tag:
                show_options = False

        if not raw_payload:
            continue
        cleaned = raw_payload.replace("&nbsp;", " ").replace("\xa0", " ")
        cleaned = re.sub(r'</?[a-zA-Z][a-zA-Z0-9]*\b[^>]*>', '\n', cleaned)
        try:
            parsed = json.loads(html.unescape(cleaned))
            if isinstance(parsed, dict):
                parsed_payloads.append(parsed)
        except Exception:
            pass

    # Remove all AI hints blocks (JSON and container) from the text
    cleaned_text = re.sub(AI_HINTS_REMOVE_PATTERN, '', text).strip()

    # Normalize and merge parsed payloads
    merged_payload = {}
    for p in parsed_payloads:
        # Check if it is keyed (e.g., contains 'c1', 'c2', etc.)
        is_keyed = False
        if not ("hints" in p or "options" in p):
            is_keyed = any(re.fullmatch(r"c\d+", str(key)) for key in p.keys())

        if not is_keyed:
            # Universal/legacy block, wrap it in "c1"
            if "hints" in p or "options" in p:
                p = {"c1": p}
            else:
                p = {}

        for cloze_key, data in p.items():
            if not isinstance(data, dict):
                continue
            if cloze_key not in merged_payload:
                merged_payload[cloze_key] = {
                    "hints": list(data.get("hints") or []),
                    "options": list(data.get("options") or []),
                }
                if "correct_answer" in data:
                    merged_payload[cloze_key]["correct_answer"] = data["correct_answer"]
                for k, v in data.items():
                    if k.startswith("_"):
                        merged_payload[cloze_key][k] = v
            else:
                existing = merged_payload[cloze_key]
                # Merge hints
                seen_hints = {h.strip() for h in existing["hints"]}
                for h in (data.get("hints") or []):
                    if h.strip() not in seen_hints:
                        existing["hints"].append(h)
                        seen_hints.add(h.strip())
                # Merge options
                seen_options = {o.strip() for o in existing["options"]}
                for o in (data.get("options") or []):
                    if o.strip() not in seen_options:
                        existing["options"].append(o)
                        seen_options.add(o.strip())
                # Merge correct answer
                if "correct_answer" not in existing and "correct_answer" in data:
                    existing["correct_answer"] = data["correct_answer"]
                # Merge metadata
                for k, v in data.items():
                    if k.startswith("_") and k not in existing:
                        existing[k] = v

    toggles = {"hints": show_hints, "options": show_options}
    return cleaned_text, merged_payload, toggles

def merge_ai_hints_payloads(payloads):
    merged = {}
    for p in payloads:
        if not p or not isinstance(p, dict):
            continue
        for cloze_key, data in p.items():
            if not isinstance(data, dict):
                continue
            if cloze_key not in merged:
                merged[cloze_key] = {
                    "hints": list(data.get("hints") or []),
                    "options": list(data.get("options") or []),
                }
                if "correct_answer" in data:
                    merged[cloze_key]["correct_answer"] = data["correct_answer"]
                for k, v in data.items():
                    if k.startswith("_"):
                        merged[cloze_key][k] = v
            else:
                existing = merged[cloze_key]
                # Merge hints
                seen_hints = {h.strip() for h in existing["hints"]}
                for h in (data.get("hints") or []):
                    if h.strip() not in seen_hints:
                        existing["hints"].append(h)
                        seen_hints.add(h.strip())
                # Merge options
                seen_options = {o.strip() for o in existing["options"]}
                for o in (data.get("options") or []):
                    if o.strip() not in seen_options:
                        existing["options"].append(o)
                        seen_options.add(o.strip())
                # Merge correct answer
                if "correct_answer" not in existing and "correct_answer" in data:
                    existing["correct_answer"] = data["correct_answer"]
                # Merge metadata
                for k, v in data.items():
                    if k.startswith("_") and k not in existing:
                        existing[k] = v
    return merged

def serialize_ai_hints_payload(payload):
    pretty_json = json.dumps(payload, indent=2, ensure_ascii=False)
    return html.escape(pretty_json, quote=False)

def build_ai_hints_block(payload, toggles):
    addon_id = "2119980872"
    attrs = f'data-ai-hints-addon-id="{addon_id}" contenteditable="false"'
    if toggles.get("hints"):
        attrs += ' data-show-hints="true"'
    else:
        attrs += ' data-show-hints="false"'
    if toggles.get("options"):
        attrs += ' data-show-options="true"'
    else:
        attrs += ' data-show-options="false"'
        
    serialized = serialize_ai_hints_payload(payload)
    return f'<div class="ai-hints-json" {attrs} style="display:none">{serialized}</div>'

try:
    from anki.consts import CARD_TYPE_LRN, CARD_TYPE_NEW, QUEUE_TYPE_NEW, QUEUE_TYPE_PREVIEW
except Exception:
# ... (rest of imports/consts)
    CARD_TYPE_LRN = 1
    CARD_TYPE_NEW = 0
    QUEUE_TYPE_NEW = 0
    QUEUE_TYPE_PREVIEW = 4

CLOZE_PATTERN = re.compile(r"\{\{c\d+::(.*?)(?:::.*?)?\}\}", re.DOTALL)


def remove_cloze_syntax(text):
    return re.sub(CLOZE_PATTERN, r"\1", text)


def get_existing_notes(collection, note_ids):
    notes = []
    valid_note_ids = []
    for note_id in note_ids:
        try:
            note = collection.get_note(note_id)
        except Exception:
            continue
        notes.append(note)
        valid_note_ids.append(note_id)
    return notes, valid_note_ids


def get_existing_card(collection, card_id):
    try:
        return collection.get_card(card_id)
    except Exception:
        return None


def get_card_ids_for_note(collection, note_id):
    if hasattr(collection, "card_ids_of_note"):
        return list(collection.card_ids_of_note(note_id))

    note = collection.get_note(note_id)
    return [card.id for card in note.cards()]


def normalize_preserved_card_state(card):
    if getattr(card, "odid", 0):
        card.due = getattr(card, "odue", card.due)
        card.odue = 0
        card.odid = 0
        if getattr(card, "type", CARD_TYPE_NEW) == CARD_TYPE_LRN:
            card.queue = QUEUE_TYPE_NEW
            card.type = CARD_TYPE_NEW
        else:
            card.queue = card.type
    elif getattr(card, "queue", None) == QUEUE_TYPE_PREVIEW:
        card.queue = card.type


def copy_card_state(source_card, target_card):
    preserved_fields = (
        "type",
        "queue",
        "due",
        "ivl",
        "factor",
        "reps",
        "lapses",
        "left",
        "odue",
        "odid",
        "flags",
        "original_position",
        "custom_data",
        "memory_state",
        "desired_retention",
        "decay",
        "last_review_time",
    )
    for field_name in preserved_fields:
        if hasattr(source_card, field_name):
            setattr(target_card, field_name, getattr(source_card, field_name))

    normalize_preserved_card_state(target_card)


def build_copied_revlog_rows(collection, source_card_id, target_card_id):
    source_rows = collection.db.all(
        "select * from revlog where cid = ? order by id",
        source_card_id,
    )
    if not source_rows:
        return []

    copied_rows = []
    current_usn = collection.usn() if hasattr(collection, "usn") else None

    # Optimization: Use a local counter to avoid repeated scalar queries.
    # We find a safe starting point (max ID + 1) and then just increment.
    max_revlog_id = collection.db.scalar("select max(id) from revlog") or 0
    next_id = max_revlog_id + 1

    for row in source_rows:
        copied_row = list(row)
        copied_row[0] = next_id
        copied_row[1] = target_card_id
        if current_usn is not None:
            copied_row[2] = current_usn
        
        copied_rows.append(tuple(copied_row))
        next_id += 1

    return copied_rows


def copy_card_state_for_new_note(collection, source_card_id, target_note_id):
    """Copy scheduling state from source card to the first card of target note.

    This uses collection.update_card() which is an undoable operation and
    must be called BEFORE merge_undo_entries() seals the undo group.

    Returns (source_card_id, target_card_id) for later revlog copying.
    """
    source_card = get_existing_card(collection, source_card_id)
    if source_card is None:
        raise ValueError("The selected source card for review history could not be found.")

    new_card_ids = get_card_ids_for_note(collection, target_note_id)
    if not new_card_ids:
        raise ValueError("The merged note did not generate any cards.")

    target_card = collection.get_card(new_card_ids[0])
    copy_card_state(source_card, target_card)
    collection.update_card(target_card)

    return source_card.id, target_card.id


def copy_revlog_rows_in_background(db_path, copied_rows):
    """Background thread function to copy revlog rows.
    
    This avoids hanging the UI during the 5-second lock timeout 
    and prevents Anki from clearing the undo stack.
    """
    import sqlite3
    import time
    
    # We wait a moment to give Anki time to release its writer lock
    time.sleep(0.5)
    
    # Attempt to copy with retries for locking
    for attempt in range(3):
        try:
            conn = sqlite3.connect(db_path, timeout=10)
            conn.executemany(
                "INSERT INTO revlog VALUES (?,?,?,?,?,?,?,?,?)",
                copied_rows,
            )
            conn.commit()
            conn.close()
            # Success!
            return
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower():
                time.sleep(1)
                continue
            break
        except Exception:
            break


def copy_revlog_rows(collection, source_card_id, target_card_id, synchronous=False):
    """Entry point for copying revlog rows.
    
    Calculates the rows and starts a background thread (or executes 
    synchronously for tests) to perform the insertion.
    """
    copied_rows = build_copied_revlog_rows(collection, source_card_id, target_card_id)
    if not copied_rows:
        return

    if synchronous:
        # For unit tests, we bypass the threading and the sleep
        import sqlite3
        conn = sqlite3.connect(collection.path, timeout=5)
        conn.executemany(
            "INSERT INTO revlog VALUES (?,?,?,?,?,?,?,?,?)",
            copied_rows,
        )
        conn.commit()
        conn.close()
        return

    import threading
    thread = threading.Thread(
        target=copy_revlog_rows_in_background,
        args=(collection.path, copied_rows),
        daemon=True
    )
    thread.start()
    logger.log("Review history copy started in background thread.")

def remove_note_safely(collection, note_id):
    try:
        if hasattr(collection, "remove_notes"):
            collection.remove_notes([note_id])
        else:
            collection.remNotes([note_id])
    except Exception:
        pass


def perform_merge(
    mw,
    target_model_id,
    target_deck_id,
    field_mapping,
    custom_separator,
    remove_cloze,
    delete_originals,
    selected_note_ids,
    preserve_review_history=False,
    review_history_source_card_id=None,
    parent_window=None,
    synchronous_history=False,
):
    parent = parent_window or mw
    overall_start = time.time()
    logger.log(f"Starting perform_merge for {len(selected_note_ids)} notes.")

    if target_model_id is None:
        showInfo("Please choose a target note type.", parent=parent)
        return False

    if target_deck_id is None:
        showInfo("Please choose a target deck.", parent=parent)
        return False

    start = time.time()
    selected_notes, valid_note_ids = get_existing_notes(mw.col, selected_note_ids)
    logger.log(f"Fetched existing notes in {time.time() - start:.4f}s")

    if not selected_notes:
        showInfo("No valid notes found to merge.", parent=parent)
        return False

    if preserve_review_history:
        if review_history_source_card_id is None:
            showInfo(
                "Please choose a source card whose review history should be preserved.",
                parent=parent,
            )
            return False

        if get_existing_card(mw.col, review_history_source_card_id) is None:
            showInfo(
                "The selected source card for review history could not be found.",
                parent=parent,
            )
            return False

    if delete_originals:
        start = time.time()
        mapped_source_fields = {src for mapped_list in field_mapping.values() for src in mapped_list}
        unmapped_non_empty = set()
        for note in selected_notes:
            note_keys = set(note.keys())
            for field in note_keys:
                if field not in mapped_source_fields and note[field].strip():
                    unmapped_non_empty.add(field)

        logger.log(f"Checked for unmapped fields in {time.time() - start:.4f}s")
        if unmapped_non_empty:
            field_list_str = ", ".join(sorted(unmapped_non_empty))
            warning_msg = (
                f"Warning: You chose to delete original notes, but the following unmapped fields "
                f"contain data that will be PERMANENTLY LOST:\n\n{field_list_str}\n\n"
                f"Do you want to proceed with the merge?"
            )
            if not askUser(warning_msg, parent=parent):
                logger.log("Merge aborted by user due to data loss warning.")
                return False

    # Single Undo Setup
    start = time.time()
    current_undo = None
    if hasattr(mw.col, 'add_custom_undo_entry'):
        current_undo = mw.col.add_custom_undo_entry("Merge Notes")
    elif hasattr(mw.col, 'undo_status'):
        current_undo = mw.col.undo_status().last_step
    else:
        mw.checkpoint("Merge Notes")
    logger.log(f"Undo setup in {time.time() - start:.4f}s")

    # Create new note
    target_model = mw.col.models.get(target_model_id)
    if not target_model:
        showInfo("The selected target note type could not be found.", parent=mw)
        return False

    new_note = mw.col.new_note(target_model)

    # Gather tags
    start = time.time()
    all_tags = set()
    for note in selected_notes:
        for tag in note.tags:
            all_tags.add(tag)

    new_note.tags = sorted(all_tags)
    logger.log(f"Gathered tags in {time.time() - start:.4f}s")

    # Dictionary to collect merged values
    start = time.time()
    merged_values = {f_name: [] for f_name in field_mapping}
    field_ai_payloads = {f_name: [] for f_name in field_mapping}
    field_toggles = {f_name: {"hints": True, "options": True} for f_name in field_mapping}

    for note in selected_notes:
        note_keys = set(note.keys())
        for f_name, source_fields in field_mapping.items():
            for src_f in source_fields:
                if src_f in note_keys:
                    val = note[src_f]
                    if val.strip():
                        cleaned_val, ai_payload, toggles = extract_ai_hints(val)
                        if cleaned_val.strip():
                            merged_values[f_name].append(cleaned_val)
                        if ai_payload:
                            field_ai_payloads[f_name].append(ai_payload)
                        if "hints" in toggles:
                            field_toggles[f_name]["hints"] = field_toggles[f_name]["hints"] and toggles["hints"]
                        if "options" in toggles:
                            field_toggles[f_name]["options"] = field_toggles[f_name]["options"] and toggles["options"]

    # Assign values to new note
    for f_name, list_values in merged_values.items():
        if f_name in new_note.keys():
            combined_text = custom_separator.join(list_values)
            if remove_cloze:
                combined_text = remove_cloze_syntax(combined_text)
            
            ai_payloads = field_ai_payloads[f_name]
            if ai_payloads:
                merged_payload = merge_ai_hints_payloads(ai_payloads)
                if merged_payload:
                    ai_block = build_ai_hints_block(merged_payload, field_toggles[f_name])
                    if combined_text.strip():
                        combined_text = combined_text.strip() + "<br><br>" + ai_block
                    else:
                        combined_text = ai_block
            
            new_note[f_name] = combined_text
    logger.log(f"Prepared merged field values in {time.time() - start:.4f}s")

    try:
        start = time.time()
        mw.col.add_note(new_note, target_deck_id)
        logger.log(f"Added new note in {time.time() - start:.4f}s")
    except Exception as e:
        showInfo(f"Error adding merged note: {e}", parent=parent)
        return False

    # --- Undoable card-state copy (must happen before merge_undo_entries) ---
    revlog_copy_ids = None
    if preserve_review_history:
        try:
            start = time.time()
            revlog_copy_ids = copy_card_state_for_new_note(
                mw.col,
                review_history_source_card_id,
                new_note.id,
            )
            logger.log(f"Copied card state in {time.time() - start:.4f}s")
        except Exception as e:
            remove_note_safely(mw.col, new_note.id)
            showInfo(f"Error preserving review history: {e}", parent=parent)
            return False

    if delete_originals:
        try:
            start = time.time()
            if hasattr(mw.col, 'remove_notes'):
                mw.col.remove_notes(valid_note_ids)
            else:
                mw.col.remNotes(valid_note_ids)
            logger.log(f"Deleted original notes in {time.time() - start:.4f}s")
        except Exception as e:
            showInfo(f"Error deleting original notes: {e}", parent=parent)

    # --- Seal the undo group ---
    if current_undo is not None and hasattr(mw.col, 'merge_undo_entries'):
        try:
            start = time.time()
            mw.col.merge_undo_entries(current_undo)
            logger.log(f"Merged undo entries in {time.time() - start:.4f}s")
        except Exception:
            pass

    # --- Revlog copy (background thread) ---
    # We start this after sealing the undo group so that the merge itself
    # is fully committed and undoable.
    if revlog_copy_ids is not None:
        try:
            copy_revlog_rows(
                mw.col, 
                revlog_copy_ids[0], 
                revlog_copy_ids[1], 
                synchronous=synchronous_history
            )
        except Exception as e:
            logger.log(f"Error starting background revlog copy: {e}")
            pass

    logger.log(f"perform_merge completed in {time.time() - overall_start:.4f}s")
    return new_note.id
