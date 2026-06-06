from aqt.qt import *

class MergeTab(QWidget):
    def __init__(self, dialog, parent=None):
        super().__init__(parent)
        self.dialog = dialog
        self.setup_ui()

    def setup_ui(self):
        merge_layout = QVBoxLayout()
        
        info_label = QLabel(f"<b>Merging {len(self.dialog.selected_notes)} notes.</b>")
        merge_layout.addWidget(info_label)

        # Target Note Type Selection
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("Target Note Type:"))
        self.dialog.target_model_cb.currentIndexChanged.connect(self.dialog.update_fields_ui)
        model_layout.addWidget(self.dialog.target_model_cb)
        merge_layout.addLayout(model_layout)

        # Target Deck Selection
        deck_layout = QHBoxLayout()
        deck_layout.addWidget(QLabel("Target Deck:"))
        deck_layout.addWidget(self.dialog.target_deck_cb)
        merge_layout.addLayout(deck_layout)

        # Fields Mapping setup
        merge_layout.addWidget(QLabel("<b>Field Mappings (Source -> Target):</b>"))
        
        self.dialog.fields_widget.setLayout(self.dialog.fields_layout)
        self.dialog.fields_scroll_area.setWidgetResizable(True)
        self.dialog.fields_scroll_area.setWidget(self.dialog.fields_widget)
        merge_layout.addWidget(self.dialog.fields_scroll_area)

        # Options layout
        options_layout = QFormLayout()
        options_layout.addRow("Custom Separator:", self.dialog.separator_input)
        options_layout.addRow("", self.dialog.remove_cloze_cb)
        options_layout.addRow("", self.dialog.delete_originals_cb)

        self.dialog.preserve_review_history_cb.toggled.connect(self.dialog.update_review_history_controls)
        options_layout.addRow("", self.dialog.preserve_review_history_cb)
        options_layout.addRow(self.dialog.review_history_source_label, self.dialog.review_history_card_cb)
        self.dialog.review_history_warning_label.setWordWrap(True)
        options_layout.addRow("", self.dialog.review_history_warning_label)
        
        options_layout.addRow("", self.dialog.open_new_note_cb)

        merge_layout.addLayout(options_layout)
        self.setLayout(merge_layout)
