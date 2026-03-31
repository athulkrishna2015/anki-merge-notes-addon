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
- **Optional Review History Preservation:** Optionally copy the scheduling state and review history from one selected source card onto the merged card.
- **Tags Preservation:** The newly merged note will inherit all tags from the original notes.
- **Intelligent Field Matching:** Automatically suggests the best source field for each target field based on name similarity.
- **Persistent Preferences:** The add-on remembers your field mappings per Note Type, selected Target Deck, custom separator, and other options across Anki sessions, including multi-source mappings.
- **Auto-Detection:** Automatically suggests the target deck based on the deck of your originally selected notes.
- **Safer Merge Validation:** Missing source notes or invalid target selections are detected before merge/delete actions are applied.

## ⚠️ Important: Review History & Duplicate Cards

When you merge notes, the add-on still creates a **new note**. Review history in Anki is tied to card IDs, so the add-on can only preserve history by copying it from **one selected source card** onto the merged result.

1. **New Note Creation:** The merge creates a new note, not an in-place rewrite of an existing one.
2. **Optional History Transfer:** If **Preserve review history on merged card** is enabled, you can choose one source card whose scheduling state and review log should be copied to the merged card.
3. **Single History Donor:** Only one source card's history can be preserved. Histories from multiple reviewed cards are not combined.
4. **Multi-Card Note Types:** If the target note type generates multiple cards, the preserved history is applied to the **first generated merged card**.
5. **Deletion of Original Notes:** If **Delete original notes after merge** is enabled, the source notes/cards are removed after the merge succeeds.
6. **Keeping Original Notes:** If deletion is disabled, the original cards remain, and the merged note is added alongside them.
7. **Undo Limitation:** The preserve-history feature currently copies review log rows directly, so Anki's normal Undo may not fully remove the copied history entries.

**Recommendation:** This add-on now works better with studied cards than before, but you should still choose the history source card carefully, especially when merging multiple reviewed notes into one result. If you rely on Undo, treat preserve-history merges with extra caution.

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
   - Choose whether to preserve review history on the merged card.
   - If preserving history, choose which source card should donate its history.
   - Review the Undo warning shown for preserve-history merges.
   - Choose whether to delete the original notes.
7. Click **OK** to merge.
<img width="1042" height="948" alt="Screenshot_20260324_155101" src="https://github.com/user-attachments/assets/1e982659-cd5f-4f1a-a9cd-6371ca32a973" />

---
## Support

If you find this add-on useful, please consider supporting its development:

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/D1D01W6NQT)

## Changelog

**2026-03-31 (v1.2.0)**
- Added a default-on **Preserve review history on merged card** option in the merge dialog.
- Added a source-card picker that shows the card number so you can choose which original card should donate its review history.
- Copied the selected source card's scheduling state and review log onto the merged card while keeping the merged-note workflow.
- Added configuration support and regression tests for the review-history preservation flow.
- Added a warning in the merge dialog and README that Undo may not fully revert copied review-history rows.

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
