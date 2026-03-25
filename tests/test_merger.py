import importlib.util
import sys
import types
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MERGER_PATH = REPO_ROOT / "addon" / "merger.py"


def load_merger_module(show_info_calls):
    aqt_module = types.ModuleType("aqt")
    utils_module = types.ModuleType("aqt.utils")

    def show_info(message, parent=None):
        show_info_calls.append({"message": message, "parent": parent})

    utils_module.showInfo = show_info
    aqt_module.utils = utils_module

    previous_modules = {
        name: sys.modules.get(name) for name in ("aqt", "aqt.utils")
    }
    sys.modules["aqt"] = aqt_module
    sys.modules["aqt.utils"] = utils_module

    try:
        spec = importlib.util.spec_from_file_location("test_merger_module", MERGER_PATH)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module
    finally:
        for name, previous_module in previous_modules.items():
            if previous_module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous_module


class FakeNote:
    def __init__(self, note_id, fields, tags=None):
        self.id = note_id
        self._fields = dict(fields)
        self.tags = list(tags or [])

    def keys(self):
        return self._fields.keys()

    def __getitem__(self, key):
        return self._fields[key]

    def __setitem__(self, key, value):
        self._fields[key] = value


class FakeModels:
    def __init__(self, models):
        self._models = dict(models)

    def get(self, model_id):
        return self._models.get(model_id)


class FakeUndoStatus:
    def __init__(self, last_step):
        self.last_step = last_step


class FakeCollection:
    def __init__(self, notes, target_model):
        self.notes = dict(notes)
        self.models = FakeModels({101: target_model})
        self.added_note = None
        self.added_deck_id = None
        self.removed_note_ids = None
        self.merged_undo_token = None

    def get_note(self, note_id):
        if note_id not in self.notes:
            raise KeyError(note_id)
        return self.notes[note_id]

    def undo_status(self):
        return FakeUndoStatus("undo-token")

    def new_note(self, model):
        field_names = {field["name"]: "" for field in model["flds"]}
        return FakeNote(None, field_names)

    def add_note(self, note, deck_id):
        self.added_note = note
        self.added_deck_id = deck_id
        note.id = 999

    def remove_notes(self, note_ids):
        self.removed_note_ids = list(note_ids)

    def merge_undo_entries(self, token):
        self.merged_undo_token = token


class FakeMainWindow:
    def __init__(self, collection):
        self.col = collection
        self.checkpoints = []

    def checkpoint(self, label):
        self.checkpoints.append(label)


class MergerTests(unittest.TestCase):
    def test_remove_cloze_syntax_handles_multiline_content(self):
        show_info_calls = []
        merger = load_merger_module(show_info_calls)

        text = "Before {{c1::Line 1\nLine 2::hint}} After"

        self.assertEqual(
            merger.remove_cloze_syntax(text),
            "Before Line 1\nLine 2 After",
        )
        self.assertEqual(show_info_calls, [])

    def test_perform_merge_merges_multiple_sources_and_only_deletes_valid_notes(self):
        show_info_calls = []
        merger = load_merger_module(show_info_calls)
        target_model = {"flds": [{"name": "Combined"}, {"name": "Extra"}]}
        collection = FakeCollection(
            notes={
                1: FakeNote(
                    1,
                    {"Front": "Hello", "Back": "{{c1::World::hint}}"},
                    tags=["beta", "alpha"],
                ),
                2: FakeNote(
                    2,
                    {"Front": "Again", "Extra": "Tail"},
                    tags=["gamma", "alpha"],
                ),
            },
            target_model=target_model,
        )
        main_window = FakeMainWindow(collection)

        new_note_id = merger.perform_merge(
            main_window,
            101,
            202,
            {"Combined": ["Front", "Back"], "Extra": ["Extra"]},
            " / ",
            True,
            True,
            [1, 404, 2],
        )

        self.assertEqual(new_note_id, 999)
        self.assertEqual(collection.added_deck_id, 202)
        self.assertEqual(collection.added_note["Combined"], "Hello / World / Again")
        self.assertEqual(collection.added_note["Extra"], "Tail")
        self.assertEqual(collection.added_note.tags, ["alpha", "beta", "gamma"])
        self.assertEqual(collection.removed_note_ids, [1, 2])
        self.assertEqual(collection.merged_undo_token, "undo-token")
        self.assertEqual(show_info_calls, [])

    def test_perform_merge_rejects_missing_target_model(self):
        show_info_calls = []
        merger = load_merger_module(show_info_calls)
        collection = FakeCollection(notes={1: FakeNote(1, {"Front": "Hello"})}, target_model={"flds": []})
        collection.models = FakeModels({})
        main_window = FakeMainWindow(collection)

        result = merger.perform_merge(
            main_window,
            101,
            202,
            {"Combined": ["Front"]},
            "<br>",
            False,
            False,
            [1],
        )

        self.assertFalse(result)
        self.assertEqual(
            show_info_calls[0]["message"],
            "The selected target note type could not be found.",
        )


if __name__ == "__main__":
    unittest.main()
