"""
Dashboard widget for TNCut application.
Displays network overview, statistics, and quick actions.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QFrame, QPushButton, QSizePolicy,
    QSpacerItem, QGroupBox, QProgressBar
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QPixmap, QPainter, QColor

from widgets.chart_widget import NetworkTrafficChart
from utils.logger import get_logger

logger = get_logger(__name__)


class DashboardWidget(QWidget):
    """Dashboard widget showing network overview and statistics."""

    def __init__(self):
        super().__init__()
        self.setObjectName("dashboard")
        # Store historical data for charts
        self.upload_history = []
        self.download_history = []
        self.max_history_points = 50
        self._setup_ui()
        self._setup_timer()

    def _setup_ui(self):
        """Set up the dashboard user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Title
        title_label = QLabel("Network Dashboard")
        title_label.setObjectName("dashboardTitle")
        title_font = self.font()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)

        # Stats cards layout
        stats_layout = QGridLayout()
        stats_layout.setSpacing(15)

        # Create stat cards
        self.total_devices_card = self._create_stat_card("Total Devices", "0", "🖥️")
        self.online_devices_card = self._create_stat_card("Online Devices", "0", "🟢")
        self.offline_devices_card = self._create_stat_card("Offline Devices", "0", "🔴")
        self.network_status_card = self._create_stat_card("Network Status", "Checking...", "🌐")

        # Add cards to grid
        stats_layout.addWidget(self.total_devices_card, 0, 0)
        stats_layout.addWidget(self.online_devices_card, 0, 1)
        stats_layout.addWidget(self.offline_devices_card, 1, 0)
        stats_layout.addWidget(self.network_status_card, 1, 1)

        layout.addLayout(stats_layout)

        # Network info section
        network_group = QGroupBox("Network Information")
        network_layout = QGridLayout()
        network_layout.setSpacing(10)

        # Network info labels
        self.local_ip_label = QLabel("Local IP: --")
        self.gateway_label = QLabel("Gateway: --")
        self.internet_label = QLabel("Internet: --")
        self.upload_speed_label = QLabel("Upload: --")
        self.download_speed_label = QLabel("Download: --")

        network_layout.addWidget(QLabel("Local IP:"), 0, 0)
        network_layout.addWidget(self.local_ip_label, 0, 1)
        network_layout.addWidget(QLabel("Gateway:"), 1, 0)
        network_layout.addWidget(self.gateway_label, 1, 1)
        network_layout.addWidget(QLabel("Internet:"), 2, 0)
        network_layout.addWidget(self.internet_label, 2, 1)
        network_layout.addWidget(QLabel("Upload:"), 3, 0)
        network_layout.addWidget(self.upload_speed_label, 3, 1)
        network_layout.addWidget(QLabel("Download:"), 4, 0)
        network_layout.addWidget(self.download_speed_label, 4, 1)

        network_group.setLayout(network_layout)
        layout.addWidget(network_group)

        # Quick actions
        actions_group = QGroupBox("Quick Actions")
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(10)

        self.scan_button = QPushButton("🔍 Scan Network")
        self.scan_button.setObjectName("actionButton")
        self.scan_button.setMinimumHeight(40)

        self.refresh_button = QPushButton("🔄 Refresh")
        self.refresh_button.setObjectName("actionButton")
        self.refresh_button.setMinimumHeight(40)

        self.settings_button = QPushButton("⚙️ Settings")
        self.settings_button.setObjectName("actionButton")
        self.settings_button.setMinimumHeight(40)

        actions_layout.addWidget(self.scan_button)
        actions_layout.addWidget(self.refresh_button)
        actions_layout.addWidget(self.settings_button)
        actions_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        actions_group.setLayout(actions_layout)
        layout.addWidget(actions_group)
        # Charts section
        charts_group = QGroupBox("Network Traffic")
        charts_layout = QVBoxLayout()

        # Add the network traffic chart widget
        self.traffic_chart = NetworkTrafficChart()
        charts_layout.addWidget(self.traffic_chart)

        charts_group.setLayout(charts_layout)
        layout.addWidget(charts_group)

        # Add stretch to push everything to top
        layout.addItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))

    def _create_stat_card(self, title: str, value: str, icon: str) -> QFrame:
        """Create a statistics card widget."""
        card = QFrame()
        card.setObjectName("statCard")
        card.setFrameStyle(QFrame.StyledPanel)
        card.setLineWidth(1)
        card.setMinimumHeight(80)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(5)

        # Icon and title
        header_layout = QHBoxLayout()
        icon_label = QLabel(icon)
        icon_label.setObjectName("statIcon")
        icon_label.setFixedSize(24, 24)
        icon_label.setAlignment(Qt.AlignCenter)

        title_label = QLabel(title)
        title_label.setObjectName("statTitle")
        title_font = self.font()
        title_font.setPointSize(10)
        title_label.setFont(title_font)

        header_layout.addWidget(icon_label)
        header_layout.addWidget(title_label)
        header_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        # Value
        value_label = QLabel(value)
        value_label.setObjectName("statValue")
        value_font = self.font()
        value_font.setPointSize(24)
        value_font.setBold(True)
        value_label.setFont(value_font)
        value_label.setAlignment(Qt.AlignCenter)

        layout.addLayout(header_layout)
        layout.addWidget(value_label)

        # Store reference to value label for updates
        card.value_label = value_label

        return card

    def _setup_timer(self):
        """Set up timer for updating dashboard data."""
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_data)
        self.update_timer.start(5000)  # Update every 5 seconds

    def _update_data(self):
        """Update dashboard data (placeholder implementation)."""
        # This would be implemented with actual data from network monitoring
        pass

    def update_stats(self, total_devices: int, online_devices: int, offline_devices: int,
                     network_status: str, local_ip: str, gateway: str,
                     internet: str, upload_speed: str, download_speed: str,
                     upload_percent: float, download_percent: int):
        """
        Update dashboard statistics.

        Args:
            total_devices: Total number of devices discovered
            online_devices: Number of online devices
            offline_devices: Number of offline devices
            network_status: Overall network status
            local_ip: Local IP address
            gateway: Gateway IP address
            internet: Internet connectivity status
            upload_speed: Upload speed string
            download_speed: Download speed string
            upload_percent: Upload percentage (0-100)
            download_percent: Download percentage (0-100)
        """
        self.total_devices_card.value_label.setText(str(total_devices))
        self.online_devices_card.value_label.setText(str(online_devices))
        self.offline_devices_card.value_label.setText(str(offline_devices))
        self.network_status_card.value_label.setText(network_status)

        self.local_ip_label.setText(f"Local IP: {local_ip}")
        self.gateway_label.setText(f"Gateway: {gateway}")
        self.internet_label.setText(f"Internet: {internet}")
        self.upload_speed_label.setText(f"Upload: {upload_speed}")
        self.download_speed_label.setText(f"Download: {download_speed}")

        self.traffic_chart.update_traffic(
            upload_percent, download_percent,
            upload_label=upload_speed,
            download_label=download_speed
        )