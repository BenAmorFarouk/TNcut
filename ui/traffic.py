"""
Traffic widget for TNCut application.
Displays network traffic statistics and charts.
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from utils.logger import get_logger

logger = get_logger(__name__)


class TrafficWidget(QWidget):
    """Widget for displaying network traffic statistics."""

    def __init__(self):
        super().__init__()
        self.setObjectName("traffic")
        self._setup_ui()
        logger.debug("Traffic widget initialized")

    def _setup_ui(self):
        """Set up the traffic widget user interface."""
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignTop)

        title = QLabel("Network Traffic")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        # Placeholder content
        placeholder = QLabel("Traffic monitoring features coming soon...")
        placeholder.setAlignment(Qt.AlignCenter)
        layout.addWidget(placeholder)