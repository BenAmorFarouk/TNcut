"""
Splash screen for TNCut application.
Displays application logo and loading status on startup.
"""

import time
from PySide6.QtWidgets import (
    QSplashScreen, QLabel, QVBoxLayout, QWidget, QProgressBar,
    QApplication
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QFont, QColor, QPainter

from utils.logger import get_logger

logger = get_logger(__name__)


def show_splash_screen(app: QApplication, duration: int = 2000) -> QSplashScreen:
    """
    Show a simple splash screen.

    Args:
        app: QApplication instance
        duration: Display time in milliseconds (not used, kept for API compat)

    Returns:
        QSplashScreen instance
    """
    pixmap = QPixmap("logo.png")
    if pixmap.isNull():
        pixmap = QPixmap(300, 300)
        pixmap.fill(QColor("#202020"))

    # Scale to a reasonable splash size
    splash_pixmap = QPixmap(400, 300)
    splash_pixmap.fill(QColor("#202020"))

    painter = QPainter(splash_pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    # Draw logo centered
    logo_size = 120
    scaled_logo = pixmap.scaled(logo_size, logo_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    x = (400 - scaled_logo.width()) // 2
    painter.drawPixmap(x, 30, scaled_logo)

    # Draw title
    painter.setPen(QColor("#ffffff"))
    font = QFont("Segoe UI", 20, QFont.Bold)
    painter.setFont(font)
    painter.drawText(0, 170, 400, 40, Qt.AlignCenter, "TNCut")

    # Draw subtitle
    painter.setPen(QColor("#aaaaaa"))
    font = QFont("Segoe UI", 10)
    painter.setFont(font)
    painter.drawText(0, 210, 400, 30, Qt.AlignCenter, "Network Monitor v1.0.1")

    # Draw loading text
    painter.setPen(QColor("#888888"))
    font = QFont("Segoe UI", 9)
    painter.setFont(font)
    painter.drawText(0, 260, 400, 30, Qt.AlignCenter, "Loading...")

    painter.end()

    splash = QSplashScreen(splash_pixmap)
    splash.show()
    app.processEvents()

    return splash
