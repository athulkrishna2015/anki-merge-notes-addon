from aqt.qt import *
from aqt import mw
from aqt.utils import showInfo
from aqt.browser import Browser

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
        self.open_new_note_cb = QCheckBox("Open/select newly created note in Browser")
        
        # Apply Config Defaults
        config = self.mw.addonManager.getConfig(self.addon_id) or {}
        last_sep = config.get("last_separator", config.get("default_separator", "<br><hr><br>"))
        self.separator_input.setText(last_sep)
        
        last_rem = config.get("last_remove_cloze", config.get("default_remove_cloze", False))
        self.remove_cloze_cb.setChecked(last_rem)
        
        last_del = config.get("last_delete_originals", config.get("default_delete_originals", False))
        self.delete_originals_cb.setChecked(last_del)
        
        last_open = config.get("last_open_new_note", config.get("default_open_new_note", True))
        self.open_new_note_cb.setChecked(last_open)


        # Layout mapping target field name to its QListWidget containing checkboxes
        self.target_field_widgets = {}

        self.setup_ui()
        self.populate_models_and_decks()
        self.update_fields_ui()

    def get_unique_source_fields(self):
        fields = set()
        for nid in self.selected_notes:
            note = self.mw.col.get_note(nid)
            for name in note.keys():
                fields.add(name)
        return sorted(list(fields))

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
        
        self.separator_input.setText("<br><hr><br>")
        options_layout.addRow("Custom Separator:", self.separator_input)
        
        self.remove_cloze_cb.setChecked(False)
        options_layout.addRow("", self.remove_cloze_cb)
        
        self.delete_originals_cb.setChecked(False)
        options_layout.addRow("", self.delete_originals_cb)
        
        self.open_new_note_cb.setChecked(True)
        options_layout.addRow("", self.open_new_note_cb)

        layout.addLayout(options_layout)

        # Buttons
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)
        
        self.setLayout(layout)

    def populate_models_and_decks(self):
        config = self.mw.addonManager.getConfig(self.addon_id) or {}
        
        self.target_model_cb.blockSignals(True)
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
        if not model_id:
            return
            
        target_model = self.mw.col.models.get(model_id)
        
        config = self.mw.addonManager.getConfig(self.addon_id) or {}
        field_cache = config.get("field_map_cache", {})
        model_cache = field_cache.get(str(model_id), {})
        
        for f in target_model['flds']:
            f_name = f['name']
            
            cb = QComboBox()
            cb.addItem("--- (None) ---", userData="")
            
            match_index = 0
            best_score = -1
            cached_source = model_cache.get(f_name)
            
            for i, src_f in enumerate(self.source_fields, start=1):
                cb.addItem(src_f, userData=src_f)
                
                if cached_source and src_f == cached_source:
                    match_index = i
                    best_score = 1000 # Absolute highest priority
                elif best_score < 1000:
                    # Smart Matching Scoring
                    def get_match_score(src, target):
                        s = src.lower().strip()
                        t = target.lower().strip()
                        if s == t: return 100
                        
                        s_clean = s.replace(" ", "").replace("_", "")
                        t_clean = t.replace(" ", "").replace("_", "")
                        if s_clean == t_clean: return 90
                        
                        synonym_groups = [
                            {"front", "expression", "vocab", "word", "kanji", "hanzi", "text"},
                            {"back", "meaning", "english", "translation", "definition"},
                            {"reading", "kana", "pinyin", "furigana", "pronunciation"}
                        ]
                        for group in synonym_groups:
                            if any(syn in s_clean for syn in group) and any(syn in t_clean for syn in group):
                                return 50
                        
                        if s_clean and t_clean and (s_clean in t_clean or t_clean in s_clean): return 10
                        return 0
                    
                    score = get_match_score(src_f, f_name)
                    if score > best_score and score > 0:
                        best_score = score
                        match_index = i
                    
            cb.setCurrentIndex(match_index)
            self.fields_layout.addRow(QLabel(f_name + ":"), cb)
            self.target_field_widgets[f_name] = cb

    def accept(self):
        from .merger import perform_merge
        
        target_model_id = self.target_model_cb.currentData()
        target_deck_id = self.target_deck_cb.currentData()
        custom_separator = self.separator_input.text()
        remove_cloze = self.remove_cloze_cb.isChecked()
        delete_originals = self.delete_originals_cb.isChecked()
        open_new_note = self.open_new_note_cb.isChecked()

        config = self.mw.addonManager.getConfig(self.addon_id) or {}
        field_cache = config.get("field_map_cache", {})
        if str(target_model_id) not in field_cache:
            field_cache[str(target_model_id)] = {}

        # Gather field mappings structure
        # target_field_name -> list of source_field_names
        field_mapping = {}
        for target_name, cb in self.target_field_widgets.items():
            chosen_source = cb.currentData()
            if chosen_source:
                field_mapping[target_name] = [chosen_source]
                field_cache[str(target_model_id)][target_name] = chosen_source
            else:
                field_mapping[target_name] = []
                field_cache[str(target_model_id)][target_name] = ""
        
        config["field_map_cache"] = field_cache

        # Check if at least one field is mapped
        has_mapping = any(len(sources) > 0 for sources in field_mapping.values())
        if not has_mapping:
            ret = QMessageBox.warning(self, "No Mappings", "You haven't mapped any fields. Merge anyway?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if ret == QMessageBox.StandardButton.No:
                return

        new_note_id = perform_merge(
            self.mw,
            target_model_id,
            target_deck_id,
            field_mapping,
            custom_separator,
            remove_cloze,
            delete_originals,
            self.selected_notes
        )

        if new_note_id:
            # Save settings for next time
            config["last_separator"] = custom_separator
            config["last_remove_cloze"] = remove_cloze
            config["last_delete_originals"] = delete_originals
            config["last_open_new_note"] = open_new_note
            config["last_target_model_id"] = target_model_id
            config["last_target_deck_id"] = target_deck_id
            self.mw.addonManager.writeConfig(self.addon_id, config)
            
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
    dialog = MergeDialog(browser, selected_notes)
    dialog.exec()
