"""
About widget for TNCut application.
Displays application information, version, and system details.
"""

import platform
import sys
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QFormLayout, QTextEdit
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QFont
from utils.logger import get_logger

logger = get_logger(__name__)


class AboutWidget(QWidget):
    """Widget for displaying application information."""

    def __init__(self):
        super().__init__()
        self.setObjectName("about")
        self._setup_ui()
        logger.debug("About widget initialized")

    def _setup_ui(self):
        """Set up the about widget user interface."""
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignTop)
        layout.setSpacing(20)

        # Header with logo and title
        header_layout = QHBoxLayout()

        # Logo
        logo_label = QLabel()
        logo_label.setFixedSize(120, 120)
        logo_label.setAlignment(Qt.AlignCenter)
        # Note: In a real app, you would load the actual logo here
        logo_label.setText("LOGO")
        logo_label.setStyleSheet("""
            border: 2px dashed #ccc;
            border-radius: 10px;
            color: #666;
            font-size: 16px;
        """)
        header_layout.addWidget(logo_label)

        # Title and version
        title_layout = QVBoxLayout()
        title_label = QLabel("TNCut")
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_layout.addWidget(title_label)

        version_label = QLabel("Version 1.0.0")
        version_label.setStyleSheet("color: #666;")
        title_layout.addWidget(version_label)

        title_layout.addStretch()
        header_layout.addLayout(title_layout)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        # Description
        description = QLabel(
            "TNCut is a network monitoring and analysis tool "
            "designed for home and small business networks. "
            "It provides real-time device discovery, traffic monitoring, "
            "and network analytics capabilities."
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        # System information group
        system_group = QGroupBox("System Information")
        system_layout = QFormLayout()

        system_layout.addRow("Operating System:", QLabel(f"{platform.system()} {platform.release()}"))
        system_layout.addRow("Python Version:", QLabel(f"{sys.version.split()[0]}"))
        system_layout.addRow("Qt Version:", QLabel("6.5.0"))  # This would come from PySide6
        system_layout.addRow("Architecture:", QLabel(platform.machine()))
        system_layout.addRow("Hostname:", QLabel(platform.node()))

        system_group.setLayout(system_layout)
        layout.addWidget(system_group)

        # Features list
        features_group = QGroupBox("Features")
        features_layout = QVBoxLayout()

        features = [
            "Real-time device discovery using ARP scanning",
            "Network traffic monitoring and bandwidth tracking",
            "Device details including vendor and hostname information",
            "Historical data collection and analysis",
            "Customizable alerts and notifications",
            "Export capabilities (CSV, JSON, TXT)",
            "Modern Windows 11-inspired user interface",
            "Extensible plugin architecture (planned)"
        ]

        for feature in features:
            feature_label = QLabel(f"• {feature}")
            feature_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            features_layout.addWidget(feature_label)

        features_group.setLayout(features_layout)
        layout.addWidget(features_group)

        # License and credits
        license_group = QGroupBox("License & Credits")
        license_layout = QVBoxLayout()

        license_text = QLabel(
            "TNCut is released under the MIT License.\n\n"
            "This product includes software developed by:\n"
            "• The Qt Company (PySide6)\n"
            "• The SQLAlchemy Project\n"
            "• The Scapy Project\n"
            "• The Python Software Foundation"
        )
        license_text.setTextInteractionFlags(Qt.TextSelectableByMouse)
        license_text.setWordWrap(True)
        license_layout.addWidget(license_text)

        license_group.setLayout(license_layout)
        layout.addWidget(license_group)

        # Close button
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        close_button = QPushButton("Close")
        close_button.clicked.connect(self._on_close_clicked)
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)

    def _on_close_clicked(self):
        """Handle close button click."""
        # In a real app, this would close the about dialog
        # For now, just log the action
        logger.debug("About dialog closed")