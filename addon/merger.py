import re
from aqt.utils import showInfo
from aqt import mw

def remove_cloze_syntax(text):
    # Matches {{c1::...}} or {{c1::...::hint}}
    cloze_pattern = re.compile(r'\{\{c\d+::(.*?)(?:::.*?)?\}\}')
    # We replace it with the first captured group (the content)
    return re.sub(cloze_pattern, r'\1', text)

def perform_merge(mw, target_model_id, field_mapping, custom_separator, remove_cloze, delete_originals, selected_note_ids):
    # Ensure all selected notes still exist
    selected_notes = []
    for nid in selected_note_ids:
        try:
            note = mw.col.get_note(nid)
            selected_notes.append(note)
        except Exception:
            pass

    if not selected_notes:
        showInfo("No valid notes found to merge.")
        return False

    # Create new note
    target_model = mw.col.models.get(target_model_id)
    new_note = mw.col.new_note(target_model)

    # Gather tags and deck_id from first selected note
    all_tags = set()
    first_note = selected_notes[0]
    
    # Try to find the deck id of the first note's cards
    deck_id = 1 # default deck
    first_cards = first_note.cards()
    if first_cards:
        deck_id = first_cards[0].did
        
    for note in selected_notes:
        for tag in note.tags:
            all_tags.add(tag)

    new_note.tags = list(all_tags)

    # Dictionary to collect merged values
    merged_values = {f_name: [] for f_name in field_mapping}

    for note in selected_notes:
        note_keys = note.keys()
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
                # Target model is already determined, but we apply remove_cloze on the final combined text
                # We could check if the target field is actually a cloze field, but the user requested:
                # "remove cloze from none cloze fields". 
                # Instead of checking if the text matches target field type, we can check if the model is cloze.
                # If the target model IS NOT a cloze model, we strip clozes. Or we just strip based on the checkbox.
                # Actually, user request: "add option to remove cloze from none cloze fields".
                # If the target model is NOT a cloze type, stripping is useful. 
                # So if `remove_cloze` is True, we strip it. We will just strip it unconditionally if checked.
                combined_text = remove_cloze_syntax(combined_text)
            
            new_note[f_name] = combined_text

    try:
        mw.col.add_note(new_note, deck_id)
    except Exception as e:
        showInfo(f"Error adding merged note: {e}")
        return False

    if delete_originals:
        # Delete original notes
        # In newer Anki versions, mw.col.remove_notes expects a list of node ids.
        try:
            # For older and newer Anki compatibility
            if hasattr(mw.col, 'remove_notes'):
                mw.col.remove_notes(selected_note_ids)
            else:
                mw.col.remNotes(selected_note_ids)
        except Exception as e:
            showInfo(f"Error deleting original notes: {e}")

    return True
