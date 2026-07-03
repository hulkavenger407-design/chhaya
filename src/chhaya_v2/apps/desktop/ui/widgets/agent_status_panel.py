from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QListWidget

class AgentStatusPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        header = QLabel("Active Agents")
        header.setObjectName("header")
        layout.addWidget(header)

        self.agent_list = QListWidget()
        layout.addWidget(self.agent_list)

    def add_agent(self, name: str, status: str):
        self.agent_list.addItem(f"{name} - [{status}]")

    def clear_agents(self):
        self.agent_list.clear()
