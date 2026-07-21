"""
Main window for the TNCut application.
Implements the main application window with sidebar navigation and content area.
"""

import os
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QLabel, QFrame,
    QSpacerItem, QSizePolicy, QApplication
)
from PySide6.QtCore import Qt, QSize, QTimer, Signal
from PySide6.QtGui import QIcon, QFont, QPixmap, QPalette, QColor

from ui.sidebar import Sidebar
from ui.dashboard import DashboardWidget
from ui.devices import DevicesWidget
from ui.traffic import TrafficWidget
from ui.logs import LogsWidget
from ui.history import HistoryWidget
from ui.settings import SettingsWidget
from ui.about import AboutWidget
from services.network_service import network_service
from utils.logger import get_logger
from utils.theme import ThemeManager
from config.settings import settings_manager
import psutil
import time

logger = get_logger(__name__)


class MainWindow(QMainWindow):
    """Main application window."""

    devices_updated_signal = Signal(list)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("TNCut - Network Monitor")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)

        # Initialize UI components
        self._setup_ui()
        self._setup_connections()
        self._apply_theme()
        self._load_logo()

        # Track previous network counters for speed calculation
        self._prev_net = psutil.net_io_counters()
        self._prev_time = time.time()

        # Set up timer for periodic updates
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_dashboard)
        self.update_timer.start(2000)  # Update every 2 seconds

        logger.info("Main window initialized")

    def _setup_ui(self):
        """Set up the user interface."""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar
        self.sidebar = Sidebar()
        main_layout.addWidget(self.sidebar)

        # Content area
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Header
        self.header = self._create_header()
        content_layout.addWidget(self.header)

        # Stacked widget for different pages
        self.stacked_widget = QStackedWidget()
        content_layout.addWidget(self.stacked_widget)

        # Status bar
        self.status_bar = self.statusBar()
        self.status_label = QLabel("Ready")
        self.status_bar.addWidget(self.status_label, 1)

        # Add content widget to main layout
        main_layout.addWidget(content_widget, 1)

        # Initialize pages
        self._init_pages()

    def _create_header(self) -> QWidget:
        """Create the header widget."""
        header = QFrame()
        header.setObjectName("header")
        header.setFixedHeight(60)
        header.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 0, 20, 0)

        # Title
        title_label = QLabel("TNCut Network Monitor")
        title_label.setObjectName("titleLabel")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)

        header_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        # Status indicators
        self.status_indicator = QLabel("●")
        self.status_indicator.setObjectName("statusIndicator")
        self.status_indicator.setToolTip("Network Status")
        header_layout.addWidget(self.status_indicator)

        self.status_text = QLabel("Online")
        self.status_text.setObjectName("statusText")
        header_layout.addWidget(self.status_text)

        return header

    def _init_pages(self):
        """Initialize all application pages."""
        # Dashboard
        self.dashboard = DashboardWidget()
        self.stacked_widget.addWidget(self.dashboard)

        # Devices
        self.devices = DevicesWidget()
        self.stacked_widget.addWidget(self.devices)

        # Traffic
        self.traffic = TrafficWidget()
        self.stacked_widget.addWidget(self.traffic)

        # Logs
        self.logs = LogsWidget()
        self.stacked_widget.addWidget(self.logs)

        # History
        self.history = HistoryWidget()
        self.stacked_widget.addWidget(self.history)

        # Settings
        self.settings = SettingsWidget()
        self.stacked_widget.addWidget(self.settings)

        # About
        self.about = AboutWidget()
        self.stacked_widget.addWidget(self.about)

        # Set default page (Dashboard)
        self.stacked_widget.setCurrentIndex(0)

        # Connect to network service for updates (via signal for thread safety)
        self.devices_updated_signal.connect(self._on_devices_updated)
        network_service.add_update_callback(self._emit_devices_updated)

    def _setup_connections(self):
        """Set up signal-slot connections."""
        # Sidebar navigation
        self.sidebar.navigation_changed.connect(self._on_navigation_changed)

        # Window events
        # (Additional connections can be added here)

    def _on_navigation_changed(self, index: int):
        """Handle navigation change from sidebar."""
        self.stacked_widget.setCurrentIndex(index)
        self._update_header_title(index)

    def _update_header_title(self, index: int):
        """Update header title based on current page."""
        titles = [
            "Dashboard",
            "Devices",
            "Traffic",
            "Logs",
            "History",
            "Settings",
            "About"
        ]
        if 0 <= index < len(titles):
            # Find the title label and update it
            for i in range(self.header.layout().count()):
                item = self.header.layout().itemAt(i)
                if item.widget() and isinstance(item.widget(), QLabel) and item.widget().objectName() == "titleLabel":
                    item.widget().setText(titles[index])
                    break

    def _apply_theme(self):
        """Apply the current theme to the application."""
        ThemeManager()._apply_theme()

    def _load_logo(self):
        """Load and display the application logo."""
        logo_path = Path(__file__).parent.parent / "logo.png"
        if logo_path.exists():
            pixmap = QPixmap(str(logo_path))
            self.sidebar.update_logo(pixmap)
        else:
            logger.warning(f"Logo file not found: {logo_path}")

    def _update_dashboard(self):
        """Update dashboard widgets with live network speed data."""
        if not hasattr(self, 'dashboard'):
            return

        from network.scanner import network_scanner

        now = time.time()
        net = psutil.net_io_counters()
        dt = now - self._prev_time
        if dt <= 0:
            dt = 1

        upload_bytes_sec = (net.bytes_sent - self._prev_net.bytes_sent) / dt
        download_bytes_sec = (net.bytes_recv - self._prev_net.bytes_recv) / dt

        self._prev_net = net
        self._prev_time = now

        upload_speed = self._format_speed(upload_bytes_sec)
        download_speed = self._format_speed(download_bytes_sec)

        # Calculate percentage based on bandwidth limit from settings
        bandwidth_mbps = getattr(settings_manager.get().network, 'bandwidth_limit', 100)
        bandwidth_bytes = bandwidth_mbps * 1_000_000 / 8  # Mbps to bytes/sec
        if bandwidth_bytes > 0:
            upload_pct = min(100, (upload_bytes_sec / bandwidth_bytes) * 100)
            download_pct = min(100, (download_bytes_sec / bandwidth_bytes) * 100)
        else:
            upload_pct = 0
            download_pct = 0

        self.dashboard.update_stats(
            total_devices=len(network_service.get_devices()),
            online_devices=sum(1 for d in network_service.get_devices() if d.is_online),
            offline_devices=sum(1 for d in network_service.get_devices() if not d.is_online),
            network_status="Online" if network_scanner.local_ip != "Unknown" else "Offline",
            local_ip=network_scanner.local_ip,
            gateway=network_scanner.gateway,
            internet="Connected",
            upload_speed=upload_speed,
            download_speed=download_speed,
            upload_percent=upload_pct,
            download_percent=download_pct
        )

    @staticmethod
    def _format_speed(bytes_per_sec: float) -> str:
        """Format bytes/sec into a human-readable speed string."""
        if bytes_per_sec < 1024:
            return f"{bytes_per_sec:.0f} B/s"
        elif bytes_per_sec < 1024 * 1024:
            return f"{bytes_per_sec / 1024:.1f} KB/s"
        else:
            return f"{bytes_per_sec / (1024 * 1024):.2f} MB/s"

    def _emit_devices_updated(self, devices):
        """Thread-safe bridge: emit signal so the slot runs on the main thread."""
        self.devices_updated_signal.emit(devices)

    def _on_devices_updated(self, devices):
        """
        Handle updates from the network service.

        Args:
            devices: List of Device objects from network service
        """
        # Update the devices widget with new data
        if hasattr(self, 'devices'):
            self.devices.update_devices(devices)

        # Update dashboard with summary stats
        if hasattr(self, 'dashboard'):
            from network.scanner import network_scanner
            online_count = sum(1 for d in devices if d.is_online)
            offline_count = len(devices) - online_count
            self.dashboard.update_stats(
                total_devices=len(devices),
                online_devices=online_count,
                offline_devices=offline_count,
                network_status="Online" if len(devices) > 0 else "No devices",
                local_ip=network_scanner.local_ip,
                gateway=network_scanner.gateway,
                internet="Connected",
                upload_speed="--",
                download_speed="--",
                upload_percent=0,
                download_percent=0
            )

    def update_status(self, message: str, status_type: str = "info"):
        """
        Update the status bar message and indicator.

        Args:
            message: Status message to display
            status_type: Type of status (info, success, warning, error)
        """
        self.status_label.setText(message)

        # Update status indicator color based on type
        color_map = {
            "info": "#17a2b8",    # Blue
            "success": "#28a745", # Green
            "warning": "#ffc107", # Yellow
            "error": "#dc3545"    # Red
        }
        color = color_map.get(status_type.lower(), "#17a2b8")
        self.status_indicator.setStyleSheet(f"color: {color}; font-size: 16px;")

    def closeEvent(self, event):
        """Handle application close event."""
        self.update_timer.stop()
        # Stop traffic monitoring if running
        if hasattr(self, 'traffic'):
            self.traffic.stop_monitoring()
        # Restore all ARP-spoofed devices
        from network.arp_spoof import arp_spoofer
        arp_spoofer.restore_all()
        # Stop network service
        network_service.stop()
        logger.info("Application shutting down")
        super().closeEvent(event)