import re
import time
from datetime import datetime

from aqt import mw
from aqt.browser import Browser
from aqt.qt import *
from aqt.utils import showInfo

# --- Logging System ---
class Logger:
    _instance = None
    _logs = []
    _listeners = []

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Logger, cls).__new__(cls)
        return cls._instance

    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        entry = f"[{timestamp}] {message}"
        self._logs.append(entry)
        # Limit log size
        if len(self._logs) > 1000:
            self._logs.pop(0)
            
        for listener in self._listeners:
            try:
                listener(entry)
            except Exception:
                pass

    def get_logs(self):
        return "\n".join(self._logs)

    def clear(self):
        self._logs = []
        for listener in self._listeners:
            try:
                listener(None)
            except Exception:
                pass

    def add_listener(self, listener):
        if listener not in self._listeners:
            self._listeners.append(listener)

    def remove_listener(self, listener):
        if listener in self._listeners:
            self._listeners.remove(listener)

logger = Logger()

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
        self.addon_id = __name__.split('.')[0]
        
        # Log startup
        config = self.mw.addonManager.getConfig(self.addon_id) or {}
        if config.get("clear_logs_on_startup", True):
            logger.clear()
        logger.log(f"Opening MergeDialog for {len(self.selected_notes)} notes.")

        self.setWindowTitle("Merge Notes")
        self.setMinimumWidth(600)
        self.setMinimumHeight(700)

        # Collect unique source fields
        self.source_fields = self.get_unique_source_fields()
        
        # UI Elements that contain state
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
            "Review history is copied from the selected source card onto "
            "the first merged card. Undo should still revert the merge "
            "as a single step."
        )
        self.open_new_note_cb = QCheckBox("Open/select newly created note in Browser")
        
        self.log_viewer = QTextEdit()
        self.log_viewer.setReadOnly(True)
        self.log_viewer.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)

        # Apply Config Defaults
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
        
        # Live Logs Setup
        logger.add_listener(self.on_new_log)
        self.refresh_logs()

    def on_new_log(self, entry):
        if entry is None:
            self.log_viewer.setPlainText("")
        else:
            self.log_viewer.append(entry)
            self.log_viewer.verticalScrollBar().setValue(
                self.log_viewer.verticalScrollBar().maximum()
            )

    def closeEvent(self, event):
        logger.remove_listener(self.on_new_log)
        super().closeEvent(event)

    def refresh_logs(self):
        self.log_viewer.setPlainText(logger.get_logs())
        self.log_viewer.verticalScrollBar().setValue(self.log_viewer.verticalScrollBar().maximum())

    def get_unique_source_fields(self):
        start = time.time()
        fields = set()
        for nid in self.selected_notes:
            try:
                note = self.mw.col.get_note(nid)
            except Exception:
                continue
            for name in note.keys():
                fields.add(name)
        result = sorted(fields)
        logger.log(f"Collected {len(result)} unique source fields in {time.time() - start:.4f}s")
        return result

    def setup_ui(self):
        layout = QVBoxLayout()
        
        self.tabs = QTabWidget()
        
        # --- TAB 1: Merge Options ---
        merge_tab = QWidget()
        merge_layout = QVBoxLayout()
        
        info_label = QLabel(f"<b>Merging {len(self.selected_notes)} notes.</b>")
        merge_layout.addWidget(info_label)

        # Target Note Type Selection
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("Target Note Type:"))
        self.target_model_cb.currentIndexChanged.connect(self.update_fields_ui)
        model_layout.addWidget(self.target_model_cb)
        merge_layout.addLayout(model_layout)

        # Target Deck Selection
        deck_layout = QHBoxLayout()
        deck_layout.addWidget(QLabel("Target Deck:"))
        deck_layout.addWidget(self.target_deck_cb)
        merge_layout.addLayout(deck_layout)

        # Fields Mapping setup
        merge_layout.addWidget(QLabel("<b>Field Mappings (Source -> Target):</b>"))
        
        self.fields_widget.setLayout(self.fields_layout)
        self.fields_scroll_area.setWidgetResizable(True)
        self.fields_scroll_area.setWidget(self.fields_widget)
        merge_layout.addWidget(self.fields_scroll_area)

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

        merge_layout.addLayout(options_layout)
        merge_tab.setLayout(merge_layout)
        
        # --- TAB 2: Logs ---
        logs_tab = QWidget()
        logs_layout = QVBoxLayout()
        logs_layout.addWidget(self.log_viewer)
        
        logs_btn_layout = QHBoxLayout()
        copy_logs_btn = QPushButton("Copy Logs")
        copy_logs_btn.clicked.connect(lambda: QApplication.clipboard().setText(logger.get_logs()))
        logs_btn_layout.addWidget(copy_logs_btn)
        
        clear_logs_btn = QPushButton("Clear Logs")
        clear_logs_btn.clicked.connect(lambda: [logger.clear(), self.refresh_logs()])
        logs_btn_layout.addWidget(clear_logs_btn)
        logs_layout.addLayout(logs_btn_layout)
        logs_tab.setLayout(logs_layout)
        
        self.tabs.addTab(merge_tab, "Merge")
        self.tabs.addTab(logs_tab, "Logs")
        
        layout.addWidget(self.tabs)

        # Buttons
        self.btn_layout = QHBoxLayout()
        
        self.merge_btn = QPushButton("Merge")
        self.merge_btn.clicked.connect(self.on_merge_stay_open)
        self.btn_layout.addWidget(self.merge_btn)
        
        self.merge_close_btn = QPushButton("Merge and Close")
        self.merge_close_btn.clicked.connect(self.on_merge_and_close)
        self.btn_layout.addWidget(self.merge_close_btn)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        self.btn_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(self.btn_layout)
        
        self.setLayout(layout)

    def populate_review_history_cards(self):
        start = time.time()
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
        logger.log(f"Populated review history picker in {time.time() - start:.4f}s")

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
        start = time.time()
        config = self.mw.addonManager.getConfig(self.addon_id) or {}

        # If all selected notes share the same note type, prefer that type
        # over the cached last_model_id so the user doesn't have to pick it.
        common_model_id = None
        try:
            model_ids = set()
            for nid in self.selected_notes:
                note = self.mw.col.get_note(nid)
                model_ids.add(note.mid)
            if len(model_ids) == 1:
                common_model_id = model_ids.pop()
        except Exception:
            pass

        preferred_model_id = common_model_id or config.get("last_target_model_id")

        self.target_model_cb.blockSignals(True)
        self.target_model_cb.clear()
        models = self.mw.col.models.all_names_and_ids()
        sorted_models = sorted(models, key=lambda x: x.name)
        
        for i, model in enumerate(sorted_models):
            self.target_model_cb.addItem(model.name, userData=model.id)
            if model.id == preferred_model_id:
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
        logger.log(f"Populated models and decks in {time.time() - start:.4f}s")

    def update_fields_ui(self):
        start = time.time()
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
        logger.log(f"Updated fields UI in {time.time() - start:.4f}s")

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
        # We don't save clear_logs_on_startup here as it's a global config only changed in ConfigDialog
        self.mw.addonManager.writeConfig(self.addon_id, config)
        logger.log("Persisted dialog state.")

    def on_merge_stay_open(self):
        self.tabs.setCurrentIndex(1)  # Switch to Logs tab
        if self.perform_merge_action():
            self.merge_btn.setEnabled(False)
            self.merge_close_btn.setEnabled(False)

    def on_merge_and_close(self):
        if self.perform_merge_action():
            self.accept()

    def perform_merge_action(self):
        from .merger import perform_merge
        
        target_model_id = self.target_model_cb.currentData()
        target_deck_id = self.target_deck_cb.currentData()

        if target_model_id is None:
            showInfo("Please choose a target note type.", parent=self)
            return False

        if target_deck_id is None:
            showInfo("Please choose a target deck.", parent=self)
            return False

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
            return False

        field_mapping = {}
        for target_name, list_widget in self.target_field_widgets.items():
            field_mapping[target_name] = self.get_checked_sources(list_widget)

        has_mapping = any(len(sources) > 0 for sources in field_mapping.values())
        if not has_mapping:
            ret = QMessageBox.warning(self, "No Mappings", "You haven't mapped any fields. Merge anyway?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if ret == QMessageBox.StandardButton.No:
                return False

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

        result = perform_merge(
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
            parent_window=self,
        )

        if result:
            new_note_id, revlog_copy_ids = result

            # --- Delayed Background History Copy ---
            # We use a brief delay to ensure Anki's main process has finished its
            # current transaction and released the database file lock. This
            # keeps the Undo button working perfectly.
            if revlog_copy_ids:
                from .merger import copy_revlog_rows
                def copy_history_in_background():
                    start_bg = time.time()
                    try:
                        # Force Anki to commit its transaction to release the DB lock
                        if hasattr(self.mw.col, 'save'):
                            self.mw.col.save()

                        copy_revlog_rows(self.mw.col, revlog_copy_ids[0], revlog_copy_ids[1])
                        logger.log(f"History background copy successful in {time.time() - start_bg:.4f}s")
                    except Exception as bg_e:
                        logger.log(f"Background history copy failed: {bg_e}")

                QTimer.singleShot(250, copy_history_in_background)

            # Refresh the browser without a full mw.reset(), which can
            # interfere with custom undo bookkeeping on some Anki versions.
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
            else:
                try:
                    if hasattr(self.browser, "table") and hasattr(self.browser.table, "update_list"):
                        # Save scroll position
                        vbar = self.browser.table.verticalScrollBar()
                        old_pos = vbar.value()
                        
                        # Modern Anki: update_list() correctly removes deleted/ghost notes 
                        # from the browser view without triggering a full search reset 
                        # or forcing the scrollbar to jump to the top.
                        self.browser.table.update_list()
                        
                        # Restore scroll position
                        QTimer.singleShot(0, lambda: vbar.setValue(old_pos))
                    elif hasattr(self.browser, 'searchFor'):
                        # Fallback for older versions: mw.requireReset() is safer 
                        # than searchFor() for avoiding jarring jumps.
                        self.mw.requireReset()
                    else:
                        self.mw.requireReset()
                except Exception:
                    pass

            if hasattr(self.mw, 'update_undo_actions'):
                self.mw.update_undo_actions()
            return True
        return False

def show_merge_dialog(browser: Browser, selected_notes):
    valid_selected_notes = filter_existing_note_ids(mw.col, selected_notes)
    if not valid_selected_notes:
        showInfo("The selected notes are no longer available.", parent=browser)
        return

    dialog = MergeDialog(browser, valid_selected_notes)
    dialog.exec()
