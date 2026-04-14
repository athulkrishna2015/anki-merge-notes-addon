import re
from aqt.utils import showInfo, askUser

try:
    from anki.consts import CARD_TYPE_LRN, CARD_TYPE_NEW, QUEUE_TYPE_NEW, QUEUE_TYPE_PREVIEW
except Exception:
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
    next_candidate = None
    current_usn = collection.usn() if hasattr(collection, "usn") else None

    for row in source_rows:
        copied_row = list(row)
        base_id = int(copied_row[0])
        candidate_id = base_id if next_candidate is None else max(base_id, next_candidate)
        while collection.db.scalar("select 1 from revlog where id = ?", candidate_id):
            candidate_id += 1

        copied_row[0] = candidate_id
        copied_row[1] = target_card_id
        if current_usn is not None:
            copied_row[2] = current_usn
        copied_rows.append(tuple(copied_row))
        next_candidate = candidate_id + 1

    return copied_rows


def preserve_review_history_for_new_note(collection, source_card_id, target_note_id):
    source_card = get_existing_card(collection, source_card_id)
    if source_card is None:
        raise ValueError("The selected source card for review history could not be found.")

    new_card_ids = get_card_ids_for_note(collection, target_note_id)
    if not new_card_ids:
        raise ValueError("The merged note did not generate any cards.")

    target_card = collection.get_card(new_card_ids[0])
    copy_card_state(source_card, target_card)
    collection.update_card(target_card)

    copied_rows = build_copied_revlog_rows(collection, source_card.id, target_card.id)
    if copied_rows:
        collection.db.executemany(
            "insert into revlog values (?,?,?,?,?,?,?,?,?)",
            copied_rows,
        )

    return target_card.id


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
):
    if target_model_id is None:
        showInfo("Please choose a target note type.", parent=mw)
        return False

    if target_deck_id is None:
        showInfo("Please choose a target deck.", parent=mw)
        return False

    selected_notes, valid_note_ids = get_existing_notes(mw.col, selected_note_ids)

    if not selected_notes:
        showInfo("No valid notes found to merge.", parent=mw)
        return False

    if preserve_review_history:
        if review_history_source_card_id is None:
            showInfo(
                "Please choose a source card whose review history should be preserved.",
                parent=mw,
            )
            return False

        if get_existing_card(mw.col, review_history_source_card_id) is None:
            showInfo(
                "The selected source card for review history could not be found.",
                parent=mw,
            )
            return False

    if delete_originals:
        mapped_source_fields = {src for mapped_list in field_mapping.values() for src in mapped_list}
        unmapped_non_empty = set()
        for note in selected_notes:
            note_keys = set(note.keys())
            for field in note_keys:
                if field not in mapped_source_fields and note[field].strip():
                    unmapped_non_empty.add(field)

        if unmapped_non_empty:
            field_list_str = ", ".join(sorted(unmapped_non_empty))
            warning_msg = (
                f"Warning: You chose to delete original notes, but the following unmapped fields "
                f"contain data that will be PERMANENTLY LOST:\n\n{field_list_str}\n\n"
                f"Do you want to proceed with the merge?"
            )
            if not askUser(warning_msg, parent=mw):
                return False

    # Single Undo Setup
    current_undo = None
    if hasattr(mw.col, 'add_custom_undo_entry'):
        current_undo = mw.col.add_custom_undo_entry("Merge Notes")
    elif hasattr(mw.col, 'undo_status'):
        current_undo = mw.col.undo_status().last_step
    else:
        mw.checkpoint("Merge Notes")

    # Create new note
    target_model = mw.col.models.get(target_model_id)
    if not target_model:
        showInfo("The selected target note type could not be found.", parent=mw)
        return False

    new_note = mw.col.new_note(target_model)

    # Gather tags
    all_tags = set()
    for note in selected_notes:
        for tag in note.tags:
            all_tags.add(tag)

    new_note.tags = sorted(all_tags)

    # Dictionary to collect merged values
    merged_values = {f_name: [] for f_name in field_mapping}

    for note in selected_notes:
        note_keys = set(note.keys())
        for f_name, source_fields in field_mapping.items():
            for src_f in source_fields:
                if src_f in note_keys:
                    val = note[src_f]
                    if val.strip():
                        merged_values[f_name].append(val)

    # Assign values to new note
    for f_name, list_values in merged_values.items():
        if f_name in new_note.keys():
            combined_text = custom_separator.join(list_values)
            if remove_cloze:
                combined_text = remove_cloze_syntax(combined_text)
            
            new_note[f_name] = combined_text

    try:
        mw.col.add_note(new_note, target_deck_id)
    except Exception as e:
        showInfo(f"Error adding merged note: {e}", parent=mw)
        return False

    if preserve_review_history:
        try:
            preserve_review_history_for_new_note(
                mw.col,
                review_history_source_card_id,
                new_note.id,
            )
        except Exception as e:
            remove_note_safely(mw.col, new_note.id)
            showInfo(f"Error preserving review history: {e}", parent=mw)
            return False

    if delete_originals:
        # Delete original notes
        # In newer Anki versions, mw.col.remove_notes expects a list of node ids.
        try:
            # For older and newer Anki compatibility
            if hasattr(mw.col, 'remove_notes'):
                mw.col.remove_notes(valid_note_ids)
            else:
                mw.col.remNotes(valid_note_ids)
        except Exception as e:
            showInfo(f"Error deleting original notes: {e}", parent=mw)

    # Merge undos conditionally (2.1.45+)
    if current_undo is not None and hasattr(mw.col, 'merge_undo_entries'):
        try:
            mw.col.merge_undo_entries(current_undo)
        except Exception:
            pass

    return new_note.id
