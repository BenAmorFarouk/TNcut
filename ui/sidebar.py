"""
Sidebar navigation component for TNCut application.
Provides navigation between different application sections.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QLabel, QFrame,
    QSizePolicy, QSpacerItem
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon, QFont, QPixmap, QPalette

from utils.theme import ThemeManager
from utils.logger import get_logger

logger = get_logger(__name__)


class Sidebar(QWidget):
    """Sidebar navigation widget."""

    # Signal emitted when navigation selection changes
    navigation_changed = Signal(int)  # index of selected page

    def __init__(self):
        super().__init__()
        self.setObjectName("sidebar")
        self.setFixedWidth(250)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        self._current_index = 0
        self._buttons = []

        self._setup_ui()
        self._apply_theme()

        logger.debug("Sidebar initialized")

    def _setup_ui(self):
        """Set up the sidebar user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Logo area
        logo_frame = QFrame()
        logo_frame.setObjectName("logoFrame")
        logo_frame.setFixedHeight(80)
        logo_layout = QVBoxLayout(logo_frame)
        logo_layout.setContentsMargins(20, 20, 20, 20)

        # Logo image
        self.logo_label = QLabel()
        self.logo_label.setObjectName("logoLabel")
        self.logo_label.setFixedSize(60, 60)
        self.logo_label.setAlignment(Qt.AlignCenter)
        logo_layout.addWidget(self.logo_label, 0, Qt.AlignHCenter | Qt.AlignVCenter)

        # App name
        self.app_name_label = QLabel("TNCut")
        self.app_name_label.setObjectName("appNameLabel")
        self.app_name_label.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        self.app_name_label.setFont(font)
        logo_layout.addWidget(self.app_name_label)

        layout.addWidget(logo_frame)

        # Separator
        separator = QFrame()
        separator.setObjectName("separator")
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)

        # Navigation buttons container
        nav_frame = QFrame()
        nav_frame.setObjectName("navFrame")
        nav_layout = QVBoxLayout(nav_frame)
        nav_layout.setContentsMargins(0, 10, 0, 10)
        nav_layout.setSpacing(2)

        # Define navigation items: (icon_text, tooltip, object_name)
        nav_items = [
            ("📊", "Dashboard", "dashboard"),
            ("📱", "Devices", "devices"),
            ("📈", "Traffic", "traffic"),
            ("📋", "Logs", "logs"),
            ("📜", "History", "history"),
            ("⚙️", "Settings", "settings"),
            ("ℹ️", "About", "about")
        ]

        for i, (icon_text, tooltip, object_name) in enumerate(nav_items):
            btn = QPushButton()
            btn.setObjectName(f"navBtn_{object_name}")
            btn.setText(icon_text)
            btn.setToolTip(tooltip)
            btn.setCheckable(True)
            btn.setFixedHeight(50)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

            # Store index for navigation
            btn.setProperty("nav_index", i)

            # Connect button click
            btn.clicked.connect(lambda checked, index=i: self._on_button_clicked(index))

            nav_layout.addWidget(btn)
            self._buttons.append(btn)

        layout.addWidget(nav_frame)

        # Spacer to push content to top
        layout.addItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # Set first button as active by default
        if self._buttons:
            self._buttons[0].setChecked(True)

    def _on_button_clicked(self, index: int):
        """Handle navigation button click."""
        if index == self._current_index:
            return

        # Update button states
        for i, btn in enumerate(self._buttons):
            btn.setChecked(i == index)

        self._current_index = index
        self.navigation_changed.emit(index)

        logger.debug(f"Navigation changed to index: {index}")

    def set_current_index(self, index: int):
        """Set the current navigation index programmatically."""
        if 0 <= index < len(self._buttons):
            self._on_button_clicked(index)

    def _apply_theme(self):
        """Apply theme-specific styling."""
        # Theme is applied via stylesheet in main application
        pass

    def update_logo(self, pixmap: QPixmap):
        """Update the sidebar logo."""
        self.logo_label.setPixmap(pixmap.scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation))