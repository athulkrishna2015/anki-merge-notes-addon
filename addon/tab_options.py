from aqt.qt import *

class OptionsTab(QWidget):
    def __init__(self, dialog, parent=None):
        super().__init__(parent)
        self.dialog = dialog
        self.setup_ui()

    def setup_ui(self):
        config_layout = QVBoxLayout()
        form = QFormLayout()
        
        intro = QLabel("<b>Set default options for the Merge Dialog:</b>")
        config_layout.addWidget(intro)

        form.addRow("Default Separator:", self.dialog.config_separator_input)
        form.addRow("", self.dialog.config_remove_cloze_cb)
        form.addRow("", self.dialog.config_delete_cb)
        form.addRow("", self.dialog.config_preserve_review_history_cb)
        form.addRow("", self.dialog.config_open_new_note_cb)
        form.addRow("", self.dialog.config_clear_logs_on_startup_cb)

        config_layout.addLayout(form)
        config_layout.addStretch()
        self.setLayout(config_layout)
