# [Anki Merge Notes Add-on](https://github.com/athulkrishna2015/anki-merge-notes-addon)

This Anki add-on allows you to merge multiple selected notes/cards directly from the Anki Browser into a single note.

Install from [AnkiWeb](https://ankiweb.net/shared/info/1774874894)

## Features

- **Merge Multiple Notes:** Select two or more cards in the Anki Browser, right-click, and choose "Merge Notes...".
- **Cross-Type Merging:** You can merge notes of different Note Types. The add-on extracts all available fields from the selected notes.
- **Multi-Source Field Mapping:** A unified graphical interface lets you map one or more source fields into each target field of your chosen Note Type.
- **Custom Separator:** Choose a custom text or HTML separator (like `<br><hr><br>`) to insert between the merged contents.
- **Remove Cloze Syntax:** Option to automatically strip out `{{c1::...}}` syntax from the combined text, keeping only the raw text, which is especially useful when merging cloze notes into a basic non-cloze note type.
- **Automatic Cleanup:** Option to automatically delete the original source notes after a successful merge.
- **Tags Preservation:** The newly merged note will inherit all tags from the original notes.
- **Intelligent Field Matching:** Automatically suggests the best source field for each target field based on name similarity.
- **Persistent Preferences:** The add-on remembers your field mappings per Note Type, selected Target Deck, custom separator, and other options across Anki sessions, including multi-source mappings.
- **Auto-Detection:** Automatically suggests the target deck based on the deck of your originally selected notes.
- **Safer Merge Validation:** Missing source notes or invalid target selections are detected before merge/delete actions are applied.

## ⚠️ Important: Review History & Duplicate Cards

When you merge notes, the add-on creates a **newly created note with all "New" cards**. It is important to understand how this affects your study history:

1. **No History Transfer:** Review history from the original cards is **not** transferred to the new merged cards.
2. **Deletion of Original Notes:** If the "Delete original notes" option is enabled, the source notes and their associated cards (including all review history) are deleted.
3. **Duplicate Cards:** If the "Delete original notes" option is disabled, the original notes remain intact, resulting in duplicates (the original cards with their history, and the new merged cards as "New" cards).

**Recommendation:** This add-on is best suited for merging **unstudied (New) notes**. Use caution when merging notes that have active review history, as the newly generated cards will not inherit their progress.

## Installation

### From AnkiWeb (Recommended)
1. Open Anki.
2. Go to `Tools` -> `Add-ons`.
3. Click `Get Add-ons...`.
4. Paste the code: `1774874894`.
5. Restart Anki.

### Manual Installation
1. Copy the `addon` folder contents to your Anki `addons21` directory, or use `make_ankiaddon.py` to build an `.ankiaddon` package.
2. Restart Anki.

## Usage

1. Open the Anki **Browser**.
2. Select two or more cards/notes.
3. Right-click and select **"Merge Notes..."** from the context menu, or from the `Notes` menu in the menu bar.
4. **Choose Target Note Type:** Select the model you want for the new merged note.
5. **Map Fields:** For each target field, check one or more source fields you want to combine into it.
6. **Configure Options:** 
   - Set a custom separator.
   - Choose whether to remove cloze syntax.
   - Choose whether to delete the original notes.
7. Click **OK** to merge.
<img width="1042" height="948" alt="Screenshot_20260324_155101" src="https://github.com/user-attachments/assets/1e982659-cd5f-4f1a-a9cd-6371ca32a973" />

## Changelog

**2026-03-25**
- Restored true multi-source field mapping in the merge dialog, matching the documented checkbox workflow.
- Fixed stale-note handling so deleted or invalid selections are skipped safely before merge and delete actions run.
- Improved merge validation for missing target note types/decks and made merged tag ordering deterministic.
- Fixed cloze cleanup for multiline cloze content.
- Added regression tests for version helpers and merge behavior.

**2026-03-24**
- Added **Intelligent Field Matching** to automatically suggest the best source fields for each target field.
- Added **Persistent Preferences** to remember your field mappings per Note Type, Target Deck, and other configurations across sessions.
- Added **Auto-Detection** for the target deck automatically based on originally selected notes.
- Fixed a bug where global configurations (custom separator, checkboxes) were not being persisted correctly on dialog load.
