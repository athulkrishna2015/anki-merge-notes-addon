from aqt.qt import *
from .logger import logger

class LogsTab(QWidget):
    def __init__(self, dialog, parent=None):
        super().__init__(parent)
        self.dialog = dialog
        self.setup_ui()

    def setup_ui(self):
        logs_layout = QVBoxLayout()
        logs_layout.addWidget(self.dialog.log_viewer)
        
        logs_btn_layout = QHBoxLayout()
        copy_logs_btn = QPushButton("Copy Logs")
        copy_logs_btn.clicked.connect(lambda: QApplication.clipboard().setText(logger.get_logs()))
        logs_btn_layout.addWidget(copy_logs_btn)
        
        clear_logs_btn = QPushButton("Clear Logs")
        clear_logs_btn.clicked.connect(lambda: [logger.clear(), self.dialog.refresh_logs()])
        logs_btn_layout.addWidget(clear_logs_btn)
        logs_layout.addLayout(logs_btn_layout)
        self.setLayout(logs_layout)
