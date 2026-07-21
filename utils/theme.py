"""
Theme management for TNCut application.
Handles dark/light theme switching and styling.
"""

from enum import Enum
from typing import Dict
from PySide6.QtGui import QPalette, QColor
from PySide6.QtWidgets import QApplication
from utils.logger import get_logger

logger = get_logger(__name__)


class ThemeMode(Enum):
    """Application theme modes."""
    LIGHT = "light"
    DARK = "dark"


class ThemeManager:
    """Manages application themes and styling."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self._current_mode = ThemeMode.DARK  # Default to dark theme
        self._custom_stylesheet = ""
        self._theme_colors: Dict[str, str] = {}

        self._initialize_theme_colors()
        logger.debug("ThemeManager initialized")

    def _initialize_theme_colors(self):
        """Initialize color palettes for light and dark themes."""
        # Dark theme colors (based on Windows 11 dark theme)
        self._theme_colors[ThemeMode.DARK] = {
            "window": "#202020",
            "window_text": "#ffffff",
            "base": "#252526",
            "alternate_base": "#2d2d30",
            "text": "#ffffff",
            "button": "#2d2d30",
            "button_text": "#ffffff",
            "bright_text": "#ff0000",
            "link": "#0078d4",
            "highlight": "#0078d4",
            "highlighted_text": "#ffffff",
            "tooltip_base": "#ffffcc",
            "tooltip_text": "#000000",
            "border": "#3e3e42",
            "shadow": "#000000",
            "highlight_light": "#1e90ff",
            "highlight_dark": "#005a9e"
        }

        # Light theme colors (based on Windows 11 light theme)
        self._theme_colors[ThemeMode.LIGHT] = {
            "window": "#ffffff",
            "window_text": "#000000",
            "base": "#fafafa",
            "alternate_base": "#f0f0f0",
            "text": "#000000",
            "button": "#f0f0f0",
            "button_text": "#000000",
            "bright_text": "#ff0000",
            "link": "#0078d4",
            "highlight": "#0078d4",
            "highlighted_text": "#ffffff",
            "tooltip_base": "#ffffe1",
            "tooltip_text": "#000000",
            "border": "#d0d0d0",
            "shadow": "#ffffff",
            "highlight_light": "#add8e6",
            "highlight_dark": "#005a9e"
        }

    def get_current_mode(self) -> ThemeMode:
        """Get the current theme mode."""
        return self._current_mode

    def set_theme_mode(self, mode: ThemeMode):
        """Set the application theme mode."""
        self._current_mode = mode
        self._apply_theme()
        logger.info(f"Theme changed to: {mode.value}")

    def toggle_theme(self):
        """Toggle between light and dark themes."""
        new_mode = ThemeMode.LIGHT if self._current_mode == ThemeMode.DARK else ThemeMode.DARK
        self.set_theme_mode(new_mode)

    def get_color(self, role: str) -> str:
        """Get a color value for the current theme."""
        return self._theme_colors[self._current_mode].get(role, "#000000")

    def _apply_theme(self):
        """Apply the current theme to the QApplication."""
        app = QApplication.instance()
        if app is None:
            logger.warning("QApplication instance not found when applying theme")
            return

        palette = QPalette()
        colors = self._theme_colors[self._current_mode]

        # Set palette colors
        palette.setColor(QPalette.Window, QColor(colors["window"]))
        palette.setColor(QPalette.WindowText, QColor(colors["window_text"]))
        palette.setColor(QPalette.Base, QColor(colors["base"]))
        palette.setColor(QPalette.AlternateBase, QColor(colors["alternate_base"]))
        palette.setColor(QPalette.Text, QColor(colors["text"]))
        palette.setColor(QPalette.Button, QColor(colors["button"]))
        palette.setColor(QPalette.ButtonText, QColor(colors["button_text"]))
        palette.setColor(QPalette.BrightText, QColor(colors["bright_text"]))
        palette.setColor(QPalette.Link, QColor(colors["link"]))
        palette.setColor(QPalette.Highlight, QColor(colors["highlight"]))
        palette.setColor(QPalette.HighlightedText, QColor(colors["highlighted_text"]))
        palette.setColor(QPalette.ToolTipBase, QColor(colors["tooltip_base"]))
        palette.setColor(QPalette.ToolTipText, QColor(colors["tooltip_text"]))

        app.setPalette(palette)

        # Apply stylesheet
        app.setStyleSheet(self._get_stylesheet())

        logger.debug(f"Applied {self._current_mode.value} theme")

    def _get_stylesheet(self) -> str:
        """Get the application stylesheet for the current theme."""
        # Base stylesheet that works for both themes
        stylesheet = f"""
        /* Main Application Styles */
        QMainWindow {{
            background-color: {self.get_color('window')};
            color: {self.get_color('window_text')};
        }}

        QWidget {{
            background-color: transparent;
            color: {self.get_color('window_text')};
            font-family: 'Segoe UI', 'Arial', sans-serif;
            font-size: 9pt;
        }}

        /* Sidebar Styles */
        QWidget#sidebar {{
            background-color: {self.get_color('base')};
            border-right: 1px solid {self.get_color('border')};
        }}

        QFrame#logoFrame {{
            background-color: {self.get_color('base')};
            border-bottom: 1px solid {self.get_color('border')};
        }}

        QLabel#appNameLabel {{
            color: {self.get_color('text')};
            font-weight: bold;
        }}

        QFrame#navFrame {{
            background-color: transparent;
        }}

        QPushButton[objectName^="navBtn_"] {{
            background-color: transparent;
            border: none;
            text-align: left;
            padding: 12px 20px;
            font-size: 16pt;
            color: {self.get_color('text')};
            border-radius: 4px;
        }}

        QPushButton[objectName^="navBtn_"]:hover {{
            background-color: {self.get_color('alternate_base')};
        }}

        QPushButton[objectName^="navBtn_"]:checked {{
            background-color: {self.get_color('highlight')};
            color: {self.get_color('highlighted_text')};
            font-weight: bold;
        }}

        QPushButton[objectName^="navBtn_"]:checked:hover {{
            background-color: {self.get_color('highlight_light')};
        }}

        QFrame#separator {{
            background-color: {self.get_color('border')};
            max-height: 1px;
        }}

        /* Content Area Styles */
        QWidget#contentArea {{
            background-color: {self.get_color('window')};
        }}

        /* Button Styles */
        QPushButton {{
            background-color: {self.get_color('button')};
            color: {self.get_color('button_text')};
            border: 1px solid {self.get_color('border')};
            padding: 8px 16px;
            border-radius: 4px;
            font-weight: normal;
        }}

        QPushButton:hover {{
            background-color: {self.get_color('alternate_base')};
            border-color: {self.get_color('highlight_light')};
        }}

        QPushButton:pressed {{
            background-color: {self.get_color('highlight')};
            color: {self.get_color('highlighted_text')};
        }}

        QPushButton:disabled {{
            background-color: {self.get_color('base')};
            color: {self.get_color('text')};
            opacity: 0.5;
        }}

        /* Input Styles */
        QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
            background-color: {self.get_color('base')};
            color: {self.get_color('text')};
            border: 1px solid {self.get_color('border')};
            padding: 6px;
            border-radius: 4px;
            selection-background-color: {self.get_color('highlight')};
        }}

        QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
            border: 1px solid {self.get_color('highlight')};
        }}

        QComboBox::drop-down {{
            border: none;
            width: 20px;
        }}

        QComboBox::down-arrow {{
            image: url(:/icons/down-arrow.png);
            width: 12px;
            height: 12px;
        }}

        /* Table Styles */
        QTableView {{
            background-color: {self.get_color('base')};
            color: {self.get_color('text')};
            gridline-color: {self.get_color('border')};
            selection-background-color: {self.get_color('highlight')};
            selection-color: {self.get_color('highlighted_text')};
            border: 1px solid {self.get_color('border')};
        }}

        QTableView::item {{
            padding: 4px;
            border-bottom: 1px solid {self.get_color('border')};
        }}

        QTableView::item:selected {{
            background-color: {self.get_color('highlight')};
            color: {self.get_color('highlighted_text')};
        }}

        QHeaderView::section {{
            background-color: {self.get_color('alternate_base')};
            color: {self.get_color('text')};
            padding: 8px;
            border: 1px solid {self.get_color('border')};
            font-weight: bold;
        }}

        /* Tab Styles */
        QTabWidget::pane {{
            border: 1px solid {self.get_color('border')};
            background-color: {self.get_color('base')};
        }}

        QTabBar::tab {{
            background-color: {self.get_color('button')};
            color: {self.get_color('button_text')};
            padding: 8px 16px;
            margin-right: 2px;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }}

        QTabBar::tab:selected {{
            background-color: {self.get_color('highlight')};
            color: {self.get_color('highlighted_text')};
        }}

        QTabBar::tab:hover:!selected {{
            background-color: {self.get_color('alternate_base')};
        }}

        /* Scrollbar Styles */
        QScrollBar:vertical {{
            background-color: {self.get_color('base')};
            width: 12px;
            border-radius: 6px;
            margin: 0px;
        }}

        QScrollBar::handle:vertical {{
            background-color: {self.get_color('border')};
            border-radius: 6px;
            min-height: 20px;
        }}

        QScrollBar::handle:vertical:hover {{
            background-color: {self.get_color('highlight')};
        }}

        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}

        QScrollBar:horizontal {{
            background-color: {self.get_color('base')};
            height: 12px;
            border-radius: 6px;
            margin: 0px;
        }}

        QScrollBar::handle:horizontal {{
            background-color: {self.get_color('border')};
            border-radius: 6px;
            min-width: 20px;
        }}

        QScrollBar::handle:horizontal:hover {{
            background-color: {self.get_color('highlight')};
        }}

        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0px;
        }}

        /* GroupBox Styles */
        QGroupBox {{
            font-weight: bold;
            border: 1px solid {self.get_color('border')};
            border-radius: 4px;
            margin-top: 8px;
            padding-top: 8px;
        }}

        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 8px;
            background-color: {self.get_color('window')};
        }}

        /* Label Styles */
        QLabel {{
            color: {self.get_color('text')};
        }}

        /* Dashboard / Traffic stat cards */
        QLabel#dashboardTitle {{
            color: {self.get_color('text')};
        }}

        QFrame#statCard {{
            background-color: {self.get_color('base')};
            border: 1px solid {self.get_color('border')};
            border-radius: 6px;
        }}

        QLabel#statTitle {{
            color: {self.get_color('text')};
        }}

        QLabel#statValue {{
            color: {self.get_color('highlight')};
        }}

        QLabel#statIcon {{
            color: {self.get_color('text')};
        }}

        QPushButton#actionButton {{
            background-color: {self.get_color('highlight')};
            color: {self.get_color('highlighted_text')};
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            font-weight: bold;
        }}

        QPushButton#actionButton:hover {{
            background-color: {self.get_color('highlight_light')};
        }}

        QPushButton#actionButton:pressed {{
            background-color: {self.get_color('highlight_dark')};
        }}

        QPushButton#actionButton:disabled {{
            background-color: {self.get_color('button')};
            color: {self.get_color('border')};
        }}

        /* Status Bar Styles */
        QStatusBar {{
            background-color: {self.get_color('base')};
            color: {self.get_color('text')};
            border-top: 1px solid {self.get_color('border')};
        }}

        /* Menu Styles */
        QMenuBar {{
            background-color: {self.get_color('base')};
            color: {self.get_color('text')};
            border-bottom: 1px solid {self.get_color('border')};
        }}

        QMenuBar::item {{
            background-color: transparent;
            padding: 4px 8px;
        }}

        QMenuBar::item:selected {{
            background-color: {self.get_color('highlight')};
            color: {self.get_color('highlighted_text')};
        }}

        QMenu {{
            background-color: {self.get_color('base')};
            color: {self.get_color('text')};
            border: 1px solid {self.get_color('border')};
        }}

        QMenu::item:selected {{
            background-color: {self.get_color('highlight')};
            color: {self.get_color('highlighted_text')};
        }}

        /* Dialog Styles */
        QDialog {{
            background-color: {self.get_color('window')};
            color: {self.get_color('window_text')};
        }}

        /* Tooltip Styles */
        QToolTip {{
            background-color: {self.get_color('tooltip_base')};
            color: {self.get_color('tooltip_text')};
            border: 1px solid {self.get_color('border')};
            border-radius: 4px;
            padding: 4px;
        }}
        """

        # Add custom stylesheet if any
        if self._custom_stylesheet:
            stylesheet += "\n/* Custom Styles */\n" + self._custom_stylesheet

        return stylesheet

    def set_custom_stylesheet(self, stylesheet: str):
        """Set custom stylesheet to be appended to the theme."""
        self._custom_stylesheet = stylesheet
        self._apply_theme()

    def get_stylesheet(self) -> str:
        """Get the current stylesheet."""
        return self._get_stylesheet()