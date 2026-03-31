import re

from aqt import mw
from aqt.browser import Browser
from aqt.qt import *
from aqt.utils import showInfo


def match_field_score(source_field, target_field):
    source = source_field.lower().strip()
    target = target_field.lower().strip()
    if source == target:
        return 100

    source_clean = source.replace(" ", "").replace("_", "")
    target_clean = target.replace(" ", "").replace("_", "")
    if source_clean == target_clean:
        return 90

    synonym_groups = [
        {"front", "expression", "vocab", "word", "kanji", "hanzi", "text"},
        {"back", "meaning", "english", "translation", "definition"},
        {"reading", "kana", "pinyin", "furigana", "pronunciation"},
    ]
    for group in synonym_groups:
        if any(syn in source_clean for syn in group) and any(
            syn in target_clean for syn in group
        ):
            return 50

    if source_clean and target_clean and (
        source_clean in target_clean or target_clean in source_clean
    ):
        return 10

    return 0


def normalize_cached_sources(cached_value):
    if isinstance(cached_value, str):
        return [cached_value] if cached_value else []
    if isinstance(cached_value, (list, tuple)):
        return [str(value) for value in cached_value if value]
    return []


def filter_existing_note_ids(collection, note_ids):
    valid_note_ids = []
    for note_id in note_ids:
        try:
            collection.get_note(note_id)
        except Exception:
            continue
        valid_note_ids.append(note_id)
    return valid_note_ids


HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
WHITESPACE_PATTERN = re.compile(r"\s+")


def summarize_for_picker(text, limit=60):
    plain_text = HTML_TAG_PATTERN.sub(" ", text or "")
    plain_text = WHITESPACE_PATTERN.sub(" ", plain_text).strip()
    if len(plain_text) <= limit:
        return plain_text
    return plain_text[: limit - 3] + "..."


class MergeDialog(QDialog):
    def __init__(self, browser: Browser, selected_notes, parent=None):
        super().__init__(parent or browser)
        self.browser = browser
        self.selected_notes = selected_notes
        self.mw = mw
        self.setWindowTitle("Merge Notes")
        self.setMinimumWidth(500)
        self.setMinimumHeight(600)

        # Collect unique source fields
        self.source_fields = self.get_unique_source_fields()
        
        # UI Elements that contain state
        self.addon_id = __name__.split('.')[0]
        self.target_model_cb = QComboBox()
        self.target_deck_cb = QComboBox()
        self.fields_scroll_area = QScrollArea()
        self.fields_widget = QWidget()
        self.fields_layout = QFormLayout()
        
        self.separator_input = QLineEdit()
        self.remove_cloze_cb = QCheckBox("Remove cloze syntax from merged fields (keep only the text)")
        self.delete_originals_cb = QCheckBox("Delete original notes after merge")
        self.preserve_review_history_cb = QCheckBox("Preserve review history on merged card")
        self.review_history_source_label = QLabel("Use History From:")
        self.review_history_card_cb = QComboBox()
        self.review_history_warning_label = QLabel(
            "Warning: preserving review history currently copies revlog entries "
            "directly, so Undo may not fully revert the copied history rows."
        )
        self.open_new_note_cb = QCheckBox("Open/select newly created note in Browser")
        
        # Apply Config Defaults
        config = self.mw.addonManager.getConfig(self.addon_id) or {}
        last_sep = config.get("last_separator", config.get("default_separator", "<br><hr><br>"))
        self.separator_input.setText(last_sep)
        
        last_rem = config.get("last_remove_cloze", config.get("default_remove_cloze", False))
        self.remove_cloze_cb.setChecked(last_rem)
        
        last_del = config.get("last_delete_originals", config.get("default_delete_originals", False))
        self.delete_originals_cb.setChecked(last_del)

        last_preserve = config.get(
            "last_preserve_review_history",
            config.get("default_preserve_review_history", True),
        )
        self.preserve_review_history_cb.setChecked(last_preserve)
        
        last_open = config.get("last_open_new_note", config.get("default_open_new_note", True))
        self.open_new_note_cb.setChecked(last_open)


        # Layout mapping target field name to its QListWidget of source fields.
        self.target_field_widgets = {}

        self.setup_ui()
        self.populate_models_and_decks()
        self.populate_review_history_cards()
        self.update_review_history_controls()
        self.update_fields_ui()

    def get_unique_source_fields(self):
        fields = set()
        for nid in self.selected_notes:
            try:
                note = self.mw.col.get_note(nid)
            except Exception:
                continue
            for name in note.keys():
                fields.add(name)
        return sorted(fields)

    def setup_ui(self):
        layout = QVBoxLayout()
        
        info_label = QLabel(f"<b>Merging {len(self.selected_notes)} notes.</b>")
        layout.addWidget(info_label)

        # Target Note Type Selection
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("Target Note Type:"))
        self.target_model_cb.currentIndexChanged.connect(self.update_fields_ui)
        model_layout.addWidget(self.target_model_cb)
        layout.addLayout(model_layout)

        # Target Deck Selection
        deck_layout = QHBoxLayout()
        deck_layout.addWidget(QLabel("Target Deck:"))
        deck_layout.addWidget(self.target_deck_cb)
        layout.addLayout(deck_layout)

        # Fields Mapping setup
        layout.addWidget(QLabel("<b>Field Mappings (Source -> Target):</b>"))
        
        self.fields_widget.setLayout(self.fields_layout)
        self.fields_scroll_area.setWidgetResizable(True)
        self.fields_scroll_area.setWidget(self.fields_widget)
        layout.addWidget(self.fields_scroll_area)

        # Options layout
        options_layout = QFormLayout()
        
        options_layout.addRow("Custom Separator:", self.separator_input)
        
        options_layout.addRow("", self.remove_cloze_cb)
        
        options_layout.addRow("", self.delete_originals_cb)

        self.preserve_review_history_cb.toggled.connect(self.update_review_history_controls)
        options_layout.addRow("", self.preserve_review_history_cb)
        options_layout.addRow(self.review_history_source_label, self.review_history_card_cb)
        self.review_history_warning_label.setWordWrap(True)
        options_layout.addRow("", self.review_history_warning_label)
        
        options_layout.addRow("", self.open_new_note_cb)

        layout.addLayout(options_layout)

        # Buttons
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)
        
        self.setLayout(layout)

    def populate_review_history_cards(self):
        self.review_history_card_cb.clear()
        first_reviewed_index = None

        for note_id in self.selected_notes:
            try:
                note = self.mw.col.get_note(note_id)
            except Exception:
                continue

            field_names = list(note.keys())
            preview = ""
            if field_names:
                preview = summarize_for_picker(note[field_names[0]])

            try:
                note_cards = note.cards()
            except Exception:
                note_cards = []

            for card in note_cards:
                try:
                    template_name = card.template()["name"]
                except Exception:
                    template_name = "Card"

                card_number = getattr(card, "ord", 0) + 1
                label = f"Card {card_number}: {template_name}"
                if preview:
                    label = f"{label} | {preview}"
                label = f"{label} (note {note_id}, card {card.id})"
                self.review_history_card_cb.addItem(label, userData=card.id)

                if first_reviewed_index is None and getattr(card, "type", 0) != 0:
                    first_reviewed_index = self.review_history_card_cb.count() - 1

        if self.review_history_card_cb.count():
            self.review_history_card_cb.setCurrentIndex(first_reviewed_index or 0)
            self.preserve_review_history_cb.setEnabled(True)
        else:
            self.preserve_review_history_cb.setChecked(False)
            self.preserve_review_history_cb.setEnabled(False)

    def update_review_history_controls(self):
        is_visible = (
            self.preserve_review_history_cb.isChecked()
            and self.review_history_card_cb.count() > 0
        )
        self.review_history_source_label.setVisible(is_visible)
        self.review_history_card_cb.setVisible(is_visible)
        self.review_history_card_cb.setEnabled(is_visible)
        self.review_history_warning_label.setVisible(is_visible)

    def populate_models_and_decks(self):
        config = self.mw.addonManager.getConfig(self.addon_id) or {}

        self.target_model_cb.blockSignals(True)
        self.target_model_cb.clear()
        models = self.mw.col.models.all_names_and_ids()
        sorted_models = sorted(models, key=lambda x: x.name)
        last_model_id = config.get("last_target_model_id")
        
        for i, model in enumerate(sorted_models):
            self.target_model_cb.addItem(model.name, userData=model.id)
            if model.id == last_model_id:
                self.target_model_cb.setCurrentIndex(i)
        self.target_model_cb.blockSignals(False)
        
        decks = self.mw.col.decks.all_names_and_ids()
        sorted_decks = sorted(decks, key=lambda x: x.name)
        self.target_deck_cb.clear()
        
        last_deck_id = None
        try:
            first_note = self.mw.col.get_note(self.selected_notes[0])
            first_cards = first_note.cards()
            if first_cards:
                last_deck_id = first_cards[0].did
        except Exception:
            pass
            
        if last_deck_id is None:
            last_deck_id = config.get("last_target_deck_id")
        
        for i, deck in enumerate(sorted_decks):
            self.target_deck_cb.addItem(deck.name, userData=deck.id)
            if deck.id == last_deck_id:
                self.target_deck_cb.setCurrentIndex(i)

    def update_fields_ui(self):
        # Clear existing layout
        while self.fields_layout.count():
            child = self.fields_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        self.target_field_widgets.clear()
        
        model_id = self.target_model_cb.currentData()
        if model_id is None:
            return
            
        target_model = self.mw.col.models.get(model_id)
        if not target_model:
            return
        
        config = self.mw.addonManager.getConfig(self.addon_id) or {}
        field_cache = config.get("field_map_cache", {})
        model_cache = field_cache.get(str(model_id), {})

        for f in target_model['flds']:
            f_name = f['name']

            list_widget = QListWidget()
            list_widget.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
            list_widget.setAlternatingRowColors(True)
            list_widget.setVerticalScrollMode(
                QAbstractItemView.ScrollMode.ScrollPerPixel
            )

            cached_sources = set(normalize_cached_sources(model_cache.get(f_name)))
            best_item = None
            best_score = 0

            for src_f in self.source_fields:
                item = QListWidgetItem(src_f)
                item.setFlags(
                    item.flags()
                    | Qt.ItemFlag.ItemIsEnabled
                    | Qt.ItemFlag.ItemIsUserCheckable
                )
                item.setCheckState(
                    Qt.CheckState.Checked
                    if src_f in cached_sources
                    else Qt.CheckState.Unchecked
                )
                list_widget.addItem(item)

                if not cached_sources:
                    score = match_field_score(src_f, f_name)
                    if score > best_score:
                        best_score = score
                        best_item = item

            if best_item is not None and not cached_sources:
                best_item.setCheckState(Qt.CheckState.Checked)

            if list_widget.count():
                row_count = min(list_widget.count(), 4)
                row_height = list_widget.sizeHintForRow(0)
                if row_height > 0:
                    frame_height = list_widget.frameWidth() * 2
                    list_widget.setMinimumHeight(
                        (row_height * row_count) + frame_height + 4
                    )

            self.fields_layout.addRow(QLabel(f"{f_name}:"), list_widget)
            self.target_field_widgets[f_name] = list_widget

    def get_checked_sources(self, list_widget):
        checked_sources = []
        for index in range(list_widget.count()):
            item = list_widget.item(index)
            if (
                item.flags() & Qt.ItemFlag.ItemIsUserCheckable
                and item.checkState() == Qt.CheckState.Checked
            ):
                checked_sources.append(item.text())
        return checked_sources

    def persist_dialog_state(
        self,
        target_model_id,
        target_deck_id,
        custom_separator,
        remove_cloze,
        delete_originals,
        preserve_review_history,
        open_new_note,
        field_mapping,
    ):
        config = self.mw.addonManager.getConfig(self.addon_id) or {}
        field_cache = config.get("field_map_cache", {})
        model_cache = field_cache.setdefault(str(target_model_id), {})
        for target_name, source_fields in field_mapping.items():
            model_cache[target_name] = list(source_fields)

        config["field_map_cache"] = field_cache
        config["last_separator"] = custom_separator
        config["last_remove_cloze"] = remove_cloze
        config["last_delete_originals"] = delete_originals
        config["last_preserve_review_history"] = preserve_review_history
        config["last_open_new_note"] = open_new_note
        config["last_target_model_id"] = target_model_id
        config["last_target_deck_id"] = target_deck_id
        self.mw.addonManager.writeConfig(self.addon_id, config)

    def accept(self):
        from .merger import perform_merge
        
        target_model_id = self.target_model_cb.currentData()
        target_deck_id = self.target_deck_cb.currentData()

        if target_model_id is None:
            showInfo("Please choose a target note type.", parent=self)
            return

        if target_deck_id is None:
            showInfo("Please choose a target deck.", parent=self)
            return

        custom_separator = self.separator_input.text()
        remove_cloze = self.remove_cloze_cb.isChecked()
        delete_originals = self.delete_originals_cb.isChecked()
        preserve_review_history = (
            self.preserve_review_history_cb.isChecked()
            and self.review_history_card_cb.count() > 0
        )
        review_history_source_card_id = (
            self.review_history_card_cb.currentData()
            if preserve_review_history
            else None
        )
        open_new_note = self.open_new_note_cb.isChecked()

        if preserve_review_history and review_history_source_card_id is None:
            showInfo(
                "Please choose a source card whose review history should be preserved.",
                parent=self,
            )
            return

        field_mapping = {}
        for target_name, list_widget in self.target_field_widgets.items():
            field_mapping[target_name] = self.get_checked_sources(list_widget)

        has_mapping = any(len(sources) > 0 for sources in field_mapping.values())
        if not has_mapping:
            ret = QMessageBox.warning(self, "No Mappings", "You haven't mapped any fields. Merge anyway?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if ret == QMessageBox.StandardButton.No:
                return

        self.persist_dialog_state(
            target_model_id,
            target_deck_id,
            custom_separator,
            remove_cloze,
            delete_originals,
            preserve_review_history,
            open_new_note,
            field_mapping,
        )

        new_note_id = perform_merge(
            self.mw,
            target_model_id,
            target_deck_id,
            field_mapping,
            custom_separator,
            remove_cloze,
            delete_originals,
            self.selected_notes,
            preserve_review_history,
            review_history_source_card_id,
        )

        if new_note_id:
            super().accept()
            # Refresh browser and optionally load the new note
            self.mw.reset()
            if open_new_note:
                try:
                    if hasattr(self.browser, 'searchFor'):
                        self.browser.searchFor(f"nid:{new_note_id}")
                    else:
                        self.browser.form.searchEdit.lineEdit().setText(f"nid:{new_note_id}")
                        if hasattr(self.browser, 'onSearchActivated'):
                            self.browser.onSearchActivated()
                        else:
                            self.browser.onSearch()
                except Exception:
                    pass

def show_merge_dialog(browser: Browser, selected_notes):
    valid_selected_notes = filter_existing_note_ids(mw.col, selected_notes)
    if not valid_selected_notes:
        showInfo("The selected notes are no longer available.", parent=browser)
        return

    dialog = MergeDialog(browser, valid_selected_notes)
    dialog.exec()
