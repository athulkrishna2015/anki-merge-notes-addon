import importlib.util
import sys
import types
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MERGER_PATH = REPO_ROOT / "addon" / "merger.py"


def load_merger_module(show_info_calls, ask_user_calls=None, ask_user_responses=None):
    if ask_user_calls is None:
        ask_user_calls = []
    if ask_user_responses is None:
        ask_user_responses = []

    aqt_module = types.ModuleType("aqt")
    utils_module = types.ModuleType("aqt.utils")

    def show_info(message, parent=None):
        show_info_calls.append({"message": message, "parent": parent})
        
    def ask_user(message, parent=None):
        ask_user_calls.append({"message": message, "parent": parent})
        if ask_user_responses:
            return ask_user_responses.pop(0)
        return True

    utils_module.showInfo = show_info
    utils_module.askUser = ask_user
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


class FakeCard:
    def __init__(
        self,
        card_id,
        note_id,
        deck_id=0,
        ord=0,
        type=0,
        queue=0,
        due=0,
        ivl=0,
        factor=0,
        reps=0,
        lapses=0,
        left=0,
        odue=0,
        odid=0,
        flags=0,
        original_position=None,
        custom_data="",
        memory_state=None,
        desired_retention=None,
        decay=None,
        last_review_time=None,
    ):
        self.id = card_id
        self.nid = note_id
        self.did = deck_id
        self.ord = ord
        self.type = type
        self.queue = queue
        self.due = due
        self.ivl = ivl
        self.factor = factor
        self.reps = reps
        self.lapses = lapses
        self.left = left
        self.odue = odue
        self.odid = odid
        self.flags = flags
        self.original_position = original_position
        self.custom_data = custom_data
        self.memory_state = memory_state
        self.desired_retention = desired_retention
        self.decay = decay
        self.last_review_time = last_review_time


class FakeDB:
    def __init__(self, revlog_rows=None):
        self.revlog_rows = list(revlog_rows or [])

    def all(self, sql, *args):
        if sql == "select * from revlog where cid = ? order by id":
            card_id = args[0]
            return sorted(
                [row for row in self.revlog_rows if row[1] == card_id],
                key=lambda row: row[0],
            )
        raise AssertionError(f"Unexpected query: {sql}")

    def scalar(self, sql, *args):
        if sql == "select 1 from revlog where id = ?":
            revlog_id = args[0]
            return 1 if any(row[0] == revlog_id for row in self.revlog_rows) else None
        raise AssertionError(f"Unexpected scalar query: {sql}")

    def executemany(self, sql, args):
        if sql != "insert into revlog values (?,?,?,?,?,?,?,?,?)":
            raise AssertionError(f"Unexpected executemany query: {sql}")
        self.revlog_rows.extend(list(args))


class FakeCollection:
    def __init__(
        self,
        notes,
        target_model,
        cards=None,
        revlog_rows=None,
        new_note_card_ids=None,
    ):
        self.notes = dict(notes)
        self.models = FakeModels({101: target_model})
        self.cards = dict(cards or {})
        self.db = FakeDB(revlog_rows)
        self.added_note = None
        self.added_deck_id = None
        self.removed_note_ids = None
        self.merged_undo_token = None
        self.updated_card_ids = []
        self._new_note_card_ids = list(new_note_card_ids or [2001])

    def get_note(self, note_id):
        if note_id not in self.notes:
            raise KeyError(note_id)
        return self.notes[note_id]

    def get_card(self, card_id):
        if card_id not in self.cards:
            raise KeyError(card_id)
        return self.cards[card_id]

    def undo_status(self):
        return FakeUndoStatus("undo-token")

    def add_custom_undo_entry(self, label):
        return "custom-undo-token-" + label

    def new_note(self, model):
        field_names = {field["name"]: "" for field in model["flds"]}
        return FakeNote(None, field_names)

    def add_note(self, note, deck_id):
        self.added_note = note
        self.added_deck_id = deck_id
        note.id = 999
        self.notes[note.id] = note
        for ord_index, card_id in enumerate(self._new_note_card_ids):
            self.cards[card_id] = FakeCard(
                card_id,
                note.id,
                deck_id=deck_id,
                ord=ord_index,
            )

    def remove_notes(self, note_ids):
        self.removed_note_ids = list(note_ids)
        for note_id in note_ids:
            self.notes.pop(note_id, None)
            for card_id in list(self.cards):
                if self.cards[card_id].nid == note_id:
                    del self.cards[card_id]

    def card_ids_of_note(self, note_id):
        return [
            card_id
            for card_id, card in sorted(self.cards.items())
            if card.nid == note_id
        ]

    def update_card(self, card, skip_undo_entry=False):
        self.cards[card.id] = card
        self.updated_card_ids.append(card.id)

    def usn(self):
        return 77

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
        self.assertEqual(collection.merged_undo_token, "custom-undo-token-Merge Notes")
        self.assertEqual(show_info_calls, [])

    def test_perform_merge_can_copy_selected_card_history_to_new_card(self):
        show_info_calls = []
        merger = load_merger_module(show_info_calls)
        target_model = {"flds": [{"name": "Combined"}]}
        source_card = FakeCard(
            501,
            1,
            deck_id=111,
            type=2,
            queue=2,
            due=42,
            ivl=15,
            factor=2600,
            reps=9,
            lapses=1,
            left=0,
            flags=3,
            original_position=7,
            custom_data='{"foo":"bar"}',
            desired_retention=0.92,
            decay=0.35,
            last_review_time=123456789,
        )
        collection = FakeCollection(
            notes={
                1: FakeNote(1, {"Front": "Hello"}, tags=["alpha"]),
            },
            target_model=target_model,
            cards={source_card.id: source_card},
            revlog_rows=[
                (1000, 501, -1, 3, 10, 5, 2500, 1, 0),
                (1001, 501, -1, 4, 15, 10, 2100, 1, 0),
                (1002, 9999, -1, 3, 8, 4, 1800, 1, 0),
            ],
            new_note_card_ids=[2001],
        )
        main_window = FakeMainWindow(collection)

        new_note_id = merger.perform_merge(
            main_window,
            101,
            202,
            {"Combined": ["Front"]},
            "<br>",
            False,
            False,
            [1],
            True,
            501,
        )

        self.assertEqual(new_note_id, 999)
        self.assertEqual(collection.updated_card_ids, [2001])
        merged_card = collection.get_card(2001)
        self.assertEqual(merged_card.did, 202)
        self.assertEqual(merged_card.type, 2)
        self.assertEqual(merged_card.queue, 2)
        self.assertEqual(merged_card.due, 42)
        self.assertEqual(merged_card.ivl, 15)
        self.assertEqual(merged_card.factor, 2600)
        self.assertEqual(merged_card.reps, 9)
        self.assertEqual(merged_card.lapses, 1)
        self.assertEqual(merged_card.flags, 3)
        self.assertEqual(merged_card.original_position, 7)
        self.assertEqual(merged_card.custom_data, '{"foo":"bar"}')
        self.assertEqual(merged_card.desired_retention, 0.92)
        self.assertEqual(merged_card.decay, 0.35)
        self.assertEqual(merged_card.last_review_time, 123456789)
        self.assertEqual(
            [row for row in collection.db.revlog_rows if row[1] == 2001],
            [
                (1003, 2001, 77, 3, 10, 5, 2500, 1, 0),
                (1004, 2001, 77, 4, 15, 10, 2100, 1, 0),
            ],
        )
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

    def test_perform_merge_rejects_missing_review_history_source_card(self):
        show_info_calls = []
        merger = load_merger_module(show_info_calls)
        collection = FakeCollection(
            notes={1: FakeNote(1, {"Front": "Hello"})},
            target_model={"flds": [{"name": "Combined"}]},
        )
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
            True,
            404,
        )

        self.assertFalse(result)
        self.assertEqual(
            show_info_calls[0]["message"],
            "The selected source card for review history could not be found.",
        )

    def test_perform_merge_warns_on_data_loss_and_aborts_if_declined(self):
        show_info_calls = []
        ask_user_calls = []
        ask_user_responses = [False]
        merger = load_merger_module(show_info_calls, ask_user_calls, ask_user_responses)

        target_model = {"flds": [{"name": "Combined"}]}
        collection = FakeCollection(
            notes={
                1: FakeNote(1, {"Front": "Hello", "UnmappedField": "HasData"}),
            },
            target_model=target_model,
        )
        main_window = FakeMainWindow(collection)

        result = merger.perform_merge(
            main_window,
            101,
            202,
            {"Combined": ["Front"]},
            " / ",
            False,
            True,  # delete originals
            [1],
        )

        self.assertFalse(result)
        self.assertEqual(len(ask_user_calls), 1)
        self.assertIn("UnmappedField", ask_user_calls[0]["message"])
        self.assertIsNone(collection.added_deck_id)

    def test_perform_merge_warns_on_data_loss_and_proceeds_if_accepted(self):
        show_info_calls = []
        ask_user_calls = []
        ask_user_responses = [True]
        merger = load_merger_module(show_info_calls, ask_user_calls, ask_user_responses)

        target_model = {"flds": [{"name": "Combined"}]}
        collection = FakeCollection(
            notes={
                1: FakeNote(1, {"Front": "Hello", "UnmappedField": "HasData"}),
            },
            target_model=target_model,
        )
        main_window = FakeMainWindow(collection)

        result = merger.perform_merge(
            main_window,
            101,
            202,
            {"Combined": ["Front"]},
            " / ",
            False,
            True,  # delete originals
            [1],
        )

        self.assertEqual(result, 999)
        self.assertEqual(len(ask_user_calls), 1)


if __name__ == "__main__":
    unittest.main()
