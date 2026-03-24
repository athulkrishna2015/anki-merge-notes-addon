# Merge Notes - Developer Notes

This repository contains the source for the **Merge Notes** Anki add-on.

## Project Structure

- `addon/`: Add-on package contents.
  - `__init__.py`: Entry point. Injects the browser menu action and binds the configuration GUI.
  - `gui.py`: PyQt dialog housing the main interface for field mapping and target model selection.
  - `merger.py`: Core logic for extracting, cleaning (clozes), appending, and injecting values into the new note, as well as cleanup.
  - `config.json`: Default properties.
  - `config_gui.py`: Provides the visual configuration UI and the Support tab for donations.
  - `Support/`: Directory containing QR codes displayed in the Support tab.
- `bump.py`: Version helpers (`validate_version`, `sync_version`) and configurable semantic bumping (`major`/`minor`/`patch`, default `patch`).
- `make_ankiaddon.py`: Creates `.ankiaddon`; auto-bumps patch only when no explicit version is provided.

## Features Wired Into Anki

- **Browser Context Menu:** Adds "Merge Notes..." to the notes context-menu and Edit menu.
- **Add-on Configuration Manager:** Replaces the default JSON editor with a tailored `QDialog` interface by passing `mw.addonManager.setConfigAction()`.
- **Note Addition API:** Native use of `mw.col.new_note()` and `mw.col.add_note()` to ensure stable compatibility with the Anki DB.

## Versioning Scheme

Version format is strictly:

```text
major.minor.patch
```

Behavior:

- `bump.py` validates semantic version format and syncs:
  - `manifest.json` keys: `version`, `human_version`
  - `addon/VERSION`
- `bump.py` can read current version and increment:
  - `patch`: `x.y.z` -> `x.y.(z+1)` (default)
  - `minor`: `x.y.z` -> `x.(y+1).0`
  - `major`: `x.y.z` -> `(x+1).0.0`
- `make_ankiaddon.py` behavior:
  - Without args: auto-bumps patch via `bump.py`, then packages.
  - With `<major.minor.patch>` arg: writes that version via `bump.py` sync helpers, then packages without bumping.

## Common Commands

Bump patch version:

```shell
python bump.py
```

Build `.ankiaddon` locally:

```shell
python make_ankiaddon.py
```

Build `.ankiaddon` with explicit version (no auto-bump):

```shell
python make_ankiaddon.py 1.5.0
```

Output naming format:

```text
Merge_Notes_v<major.minor.patch>_<YYYYMMDDHHMM>.ankiaddon
```

## Local Testing With Symlink

Linux:

```shell
ln -s "$(pwd)/addon" ~/.local/share/Anki2/addons21/merge_notes_dev
```

Windows (PowerShell as admin):

```powershell
New-Item -ItemType SymbolicLink -Path "$env:APPDATA\Anki2\addons21\merge_notes_dev" -Target "$pwd\addon"
```
