import re
from aqt.utils import showInfo

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


def perform_merge(mw, target_model_id, target_deck_id, field_mapping, custom_separator, remove_cloze, delete_originals, selected_note_ids):
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

    # Single Undo Setup
    current_undo = None
    if hasattr(mw.col, 'undo_status'):
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
