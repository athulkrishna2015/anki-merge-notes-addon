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
        
        # Read config
        addon_id = __name__.split('.')[0]
        config = self.mw.addonManager.getConfig(addon_id) or {}

        # UI Elements that contain state
        self.target_model_cb = QComboBox()
        self.fields_scroll_area = QScrollArea()
        self.fields_widget = QWidget()
        self.fields_layout = QFormLayout()
        
        self.separator_input = QLineEdit()
        self.remove_cloze_cb = QCheckBox("Remove cloze syntax from merged fields (keep only the text)")
        self.delete_originals_cb = QCheckBox("Delete original notes after merge")
        
        # Apply Config Defaults
        self.separator_input.setText(config.get("default_separator", "<br><hr><br>"))
        self.remove_cloze_cb.setChecked(config.get("default_remove_cloze", False))
        self.delete_originals_cb.setChecked(config.get("default_delete_originals", False))


        # Layout mapping target field name to its QListWidget containing checkboxes
        self.target_field_widgets = {}

        self.setup_ui()
        self.populate_models()
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

        layout.addLayout(options_layout)

        # Buttons
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)
        
        self.setLayout(layout)

    def populate_models(self):
        self.target_model_cb.blockSignals(True)
        models = self.mw.col.models.all_names_and_ids()
        # Sort models alphabetically
        sorted_models = sorted(models, key=lambda x: x.name)
        for model in sorted_models:
            self.target_model_cb.addItem(model.name, userData=model.id)
        self.target_model_cb.blockSignals(False)

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
        
        for f in target_model['flds']:
            f_name = f['name']
            
            # Create a list widget for source fields to allow multiple selection
            list_widget = QListWidget()
            list_widget.setFixedHeight(80) # small list
            list_widget.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
            
            for src_f in self.source_fields:
                item = QListWidgetItem(src_f)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                
                # Auto-check if names match roughly
                if src_f.lower() == f_name.lower():
                    item.setCheckState(Qt.CheckState.Checked)
                else:
                    item.setCheckState(Qt.CheckState.Unchecked)
                    
                list_widget.addItem(item)
                
            self.fields_layout.addRow(QLabel(f_name + ":"), list_widget)
            self.target_field_widgets[f_name] = list_widget

    def accept(self):
        from .merger import perform_merge
        
        target_model_id = self.target_model_cb.currentData()
        custom_separator = self.separator_input.text()
        remove_cloze = self.remove_cloze_cb.isChecked()
        delete_originals = self.delete_originals_cb.isChecked()

        # Gather field mappings structure
        # target_field_name -> list of source_field_names
        field_mapping = {}
        for target_name, list_widget in self.target_field_widgets.items():
            checked_sources = []
            for i in range(list_widget.count()):
                item = list_widget.item(i)
                if item.checkState() == Qt.CheckState.Checked:
                    checked_sources.append(item.text())
            field_mapping[target_name] = checked_sources

        # Check if at least one field is mapped
        has_mapping = any(len(sources) > 0 for sources in field_mapping.values())
        if not has_mapping:
            ret = QMessageBox.warning(self, "No Mappings", "You haven't mapped any fields. Merge anyway?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if ret == QMessageBox.StandardButton.No:
                return

        success = perform_merge(
            self.mw,
            target_model_id,
            field_mapping,
            custom_separator,
            remove_cloze,
            delete_originals,
            self.selected_notes
        )

        if success:
            super().accept()
            # Need to refresh browser to show changes and remove deleted notes
            self.mw.reset()
            self.browser.request_search()

def show_merge_dialog(browser: Browser, selected_notes):
    dialog = MergeDialog(browser, selected_notes)
    dialog.exec()
