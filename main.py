"""
Main entry point for the TNCut application.
Initializes the application, database, and shows the main window.
"""

import sys
import os
import logging
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon, QPixmap

from ui.main_window import MainWindow
from ui.splash_screen import show_splash_screen
from database.session import init_database
from utils.logger import setup_logging, get_logger, enable_db_logging
from utils.theme import ThemeManager, ThemeMode
from config.settings import settings_manager
from services.network_service import network_service

# Initialize logger
logger = get_logger(__name__)


def setup_application() -> QApplication:
    """
    Set up the Qt application with high DPI scaling and application metadata.

    Returns:
        Configured QApplication instance
    """
    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("TNCut")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("TNCut")
    app.setOrganizationDomain("tncut.example.com")

    # Set application icon
    icon_path = Path(__file__).parent / "logo.ico"
    if not icon_path.exists():
        icon_path = Path(__file__).parent / "logo.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
        logger.info(f"Application icon set from: {icon_path}")
    else:
        logger.warning("Application icon not found")

    return app


def initialize_system() -> None:
    """Initialize system components: logging, database, settings."""
    try:
        # Set up logging
        setup_logging(log_level=logging.INFO, log_to_file=True)
        logger.info("Logging initialized")

        # Initialize database
        db_path = "data/tncut.db"
        echo_sql = settings_manager.get().database.echo if hasattr(settings_manager.get(), 'database') else False
        init_database(db_path=db_path, echo=echo_sql)
        logger.info("Database initialized")

        # Enable database logging now that DB is ready
        enable_db_logging()

        # Apply theme
        theme_mode_str = settings_manager.get().ui.theme if hasattr(settings_manager.get(), 'ui') else "dark"
        theme_mode = ThemeMode.DARK if theme_mode_str.lower() == "dark" else ThemeMode.LIGHT
        ThemeManager().set_theme_mode(theme_mode)
        logger.info(f"Theme set to: {theme_mode.value}")

    except Exception as e:
        print(f"Error during system initialization: {e}")
        raise


def main():
    """Main application entry point."""
    try:
        # Create Qt application
        app = setup_application()

        # Show splash screen
        splash = show_splash_screen(app, 1500)  # Show for at least 1.5 seconds

        # Initialize system components (behind the splash screen)
        initialize_system()

        # Create and show main window
        window = MainWindow()
        window.show()

        # Start network service
        network_service.start(scan_interval=30)

        # Finish splash screen
        splash.finish(window)

        logger.info("TNCut application started successfully")

        # Start application event loop
        sys.exit(app.exec())

    except Exception as e:
        import traceback
        crash_msg = traceback.format_exc()
        print(f"Fatal error starting application: {e}")
        try:
            crash_path = Path(__file__).parent / "crash.log"
            with open(crash_path, "w") as f:
                f.write(crash_msg)
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()