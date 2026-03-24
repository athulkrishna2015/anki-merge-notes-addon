import os
from aqt.qt import *
from aqt import mw

class ConfigDialog(QDialog):
    def __init__(self, addon_id, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Merge Notes Configuration")
        self.setMinimumWidth(400)
        self.setMinimumHeight(500)
        self.addon_id = addon_id
        self.mw = mw
        self.config = mw.addonManager.getConfig(self.addon_id) or {}
        self.setup_ui()
    
    def setup_ui(self):
        main_layout = QVBoxLayout()
        self.tabs = QTabWidget()
        
        # --- TAB 1: Configuration ---
        config_tab = QWidget()
        config_layout = QVBoxLayout()
        form = QFormLayout()
        
        intro = QLabel("<b>Set default options for the Merge Dialog:</b>")
        config_layout.addWidget(intro)

        self.separator_input = QLineEdit()
        self.separator_input.setText(self.config.get("default_separator", "<br><hr><br>"))
        form.addRow("Default Separator:", self.separator_input)
        
        self.remove_cloze_cb = QCheckBox("Remove Cloze Syntax (Keep Text Only)")
        self.remove_cloze_cb.setChecked(self.config.get("default_remove_cloze", False))
        form.addRow("", self.remove_cloze_cb)
        
        self.delete_cb = QCheckBox("Delete Original Notes After Merge")
        self.delete_cb.setChecked(self.config.get("default_delete_originals", False))
        form.addRow("", self.delete_cb)
        
        self.open_new_note_cb = QCheckBox("Open/Select Newly Created Note in Browser")
        self.open_new_note_cb.setChecked(self.config.get("default_open_new_note", True))
        form.addRow("", self.open_new_note_cb)
        
        config_layout.addLayout(form)
        config_layout.addStretch()
        config_tab.setLayout(config_layout)
        
        # --- TAB 2: Support ---
        support_tab = QWidget()
        support_layout = QVBoxLayout()
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        
        support_info = [
            ("UPI", "athulkrishnasv2015-2@okhdfcbank", "UPI.jpg"),
            ("BTC", "bc1qrrek3m7sr33qujjrktj949wav6mehdsk057cfx", "BTC.jpg"),
            ("ETH", "0xce6899e4903EcB08bE5Be65E44549fadC3F45D27", "ETH.jpg")
        ]
        
        base_dir = os.path.dirname(__file__)
        for title, address, img_filename in support_info:
            group = QGroupBox(title)
            g_layout = QVBoxLayout()
            
            img_path = os.path.join(base_dir, "Support", img_filename)
            img_label = QLabel()
            if os.path.exists(img_path):
                pixmap = QPixmap(img_path)
                # Scale pixmap to not be small, e.g. 250x250
                pixmap = pixmap.scaled(250, 250, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                img_label.setPixmap(pixmap)
                img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            else:
                img_label.setText(f"[Image {img_filename} not found]")
            
            g_layout.addWidget(img_label)
            
            text_layout = QHBoxLayout()
            addr_label = QLineEdit(address)
            addr_label.setReadOnly(True)
            copy_btn = QPushButton("Copy")
            # Capture the address in closure
            copy_btn.clicked.connect(lambda checked, a=address: QApplication.clipboard().setText(a))
            
            text_layout.addWidget(addr_label)
            text_layout.addWidget(copy_btn)
            g_layout.addLayout(text_layout)
            
            group.setLayout(g_layout)
            scroll_layout.addWidget(group)
        
        scroll_content.setLayout(scroll_layout)
        scroll_area.setWidget(scroll_content)
        support_layout.addWidget(scroll_area)
        support_tab.setLayout(support_layout)
        
        # Add tabs
        self.tabs.addTab(config_tab, "Options")
        self.tabs.addTab(support_tab, "Support")
        
        main_layout.addWidget(self.tabs)
        
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        main_layout.addWidget(btn_box)
        
        self.setLayout(main_layout)
        
    def accept(self):
        self.config["default_separator"] = self.separator_input.text()
        self.config["default_remove_cloze"] = self.remove_cloze_cb.isChecked()
        self.config["default_delete_originals"] = self.delete_cb.isChecked()
        self.config["default_open_new_note"] = self.open_new_note_cb.isChecked()
        
        self.mw.addonManager.writeConfig(self.addon_id, self.config)
        super().accept()

def show_config(addon_id):
    dialog = ConfigDialog(addon_id, mw)
    dialog.exec()
