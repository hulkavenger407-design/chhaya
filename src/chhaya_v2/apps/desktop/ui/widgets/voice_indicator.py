from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt

class VoiceIndicatorWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        self.status_label = QLabel("Voice: IDLE")
        self.status_label.setObjectName("header")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

    def set_state(self, state_name: str):
        # E.g. "LISTENING", "SPEAKING", "MUTED"
        self.status_label.setText(f"Voice: {state_name}")
