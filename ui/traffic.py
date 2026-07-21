"""
Traffic widget for TNCut application.
Displays live network traffic statistics and charts with start/stop control.
"""

import time

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QGroupBox, QFrame, QSizePolicy, QSpacerItem
)
from PySide6.QtCore import Qt, QTimer

from widgets.chart_widget import NetworkTrafficChart
from utils.logger import get_logger

logger = get_logger(__name__)

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


class TrafficWidget(QWidget):
    """Widget for displaying and monitoring network traffic statistics."""

    # Poll interval in milliseconds.
    POLL_INTERVAL_MS = 1000

    def __init__(self):
        super().__init__()
        self.setObjectName("traffic")

        self._monitoring = False
        self._last_sent = 0
        self._last_recv = 0
        self._last_time = 0.0
        self._peak_up = 0.0
        self._peak_down = 0.0
        self._session_start_sent = 0
        self._session_start_recv = 0

        self._timer = QTimer(self)
        self._timer.setInterval(self.POLL_INTERVAL_MS)
        self._timer.timeout.connect(self._poll)

        self._setup_ui()
        logger.debug("Traffic widget initialized")

    def _setup_ui(self):
        """Set up the traffic widget user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title = QLabel("Network Traffic")
        title.setObjectName("dashboardTitle")
        title_font = self.font()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        # Controls
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(10)

        self.start_button = QPushButton("▶ Start")
        self.start_button.setObjectName("actionButton")
        self.start_button.setMinimumHeight(40)
        self.start_button.clicked.connect(self.start_monitoring)

        self.stop_button = QPushButton("⏹ Stop")
        self.stop_button.setObjectName("actionButton")
        self.stop_button.setMinimumHeight(40)
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_monitoring)

        self.status_label = QLabel("Stopped")
        self.status_label.setObjectName("statTitle")

        controls_layout.addWidget(self.start_button)
        controls_layout.addWidget(self.stop_button)
        controls_layout.addWidget(self.status_label)
        controls_layout.addItem(
            QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        layout.addLayout(controls_layout)

        # Live stat cards
        stats_layout = QGridLayout()
        stats_layout.setSpacing(15)

        self.upload_card = self._create_stat_card("Upload", "0 B/s", "⬆️")
        self.download_card = self._create_stat_card("Download", "0 B/s", "⬇️")
        self.total_sent_card = self._create_stat_card("Sent (session)", "0 B", "📤")
        self.total_recv_card = self._create_stat_card("Received (session)", "0 B", "📥")

        stats_layout.addWidget(self.upload_card, 0, 0)
        stats_layout.addWidget(self.download_card, 0, 1)
        stats_layout.addWidget(self.total_sent_card, 1, 0)
        stats_layout.addWidget(self.total_recv_card, 1, 1)
        layout.addLayout(stats_layout)

        # Chart
        charts_group = QGroupBox("Throughput")
        charts_layout = QVBoxLayout()
        self.traffic_chart = NetworkTrafficChart()
        charts_layout.addWidget(self.traffic_chart)
        charts_group.setLayout(charts_layout)
        layout.addWidget(charts_group)

        if not PSUTIL_AVAILABLE:
            self.start_button.setEnabled(False)
            self.status_label.setText("psutil not available — monitoring disabled")

        layout.addItem(
            QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))

    def _create_stat_card(self, title: str, value: str, icon: str) -> QFrame:
        """Create a statistics card widget (matches dashboard styling)."""
        card = QFrame()
        card.setObjectName("statCard")
        card.setFrameStyle(QFrame.StyledPanel)
        card.setLineWidth(1)
        card.setMinimumHeight(80)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(15, 15, 15, 15)
        card_layout.setSpacing(5)

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
        header_layout.addItem(
            QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        value_label = QLabel(value)
        value_label.setObjectName("statValue")
        value_font = self.font()
        value_font.setPointSize(20)
        value_font.setBold(True)
        value_label.setFont(value_font)
        value_label.setAlignment(Qt.AlignCenter)

        card_layout.addLayout(header_layout)
        card_layout.addWidget(value_label)

        card.value_label = value_label
        return card

    def start_monitoring(self):
        """Begin polling network counters and updating the display."""
        if self._monitoring or not PSUTIL_AVAILABLE:
            return

        counters = psutil.net_io_counters()
        self._last_sent = counters.bytes_sent
        self._last_recv = counters.bytes_recv
        self._session_start_sent = counters.bytes_sent
        self._session_start_recv = counters.bytes_recv
        self._last_time = time.monotonic()
        self._peak_up = 0.0
        self._peak_down = 0.0

        self.traffic_chart.clear()
        self._monitoring = True
        self._timer.start()

        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.status_label.setText("● Monitoring")
        logger.info("Traffic monitoring started")

    def stop_monitoring(self):
        """Stop polling network counters."""
        if not self._monitoring:
            return

        self._timer.stop()
        self._monitoring = False

        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.status_label.setText("Stopped")
        self.upload_card.value_label.setText("0 B/s")
        self.download_card.value_label.setText("0 B/s")
        logger.info("Traffic monitoring stopped")

    def _poll(self):
        """Sample net counters, compute rates, update cards and chart."""
        if not PSUTIL_AVAILABLE:
            return

        now = time.monotonic()
        elapsed = now - self._last_time
        if elapsed <= 0:
            return

        counters = psutil.net_io_counters()
        sent, recv = counters.bytes_sent, counters.bytes_recv

        up_rate = max(0.0, (sent - self._last_sent) / elapsed)
        down_rate = max(0.0, (recv - self._last_recv) / elapsed)

        self._last_sent = sent
        self._last_recv = recv
        self._last_time = now

        self._peak_up = max(self._peak_up, up_rate)
        self._peak_down = max(self._peak_down, down_rate)

        self.upload_card.value_label.setText(self._format_speed(up_rate))
        self.download_card.value_label.setText(self._format_speed(down_rate))
        self.total_sent_card.value_label.setText(
            self._format_bytes(sent - self._session_start_sent))
        self.total_recv_card.value_label.setText(
            self._format_bytes(recv - self._session_start_recv))

        # Scale chart values (0-100) relative to the session peak so the line
        # stays readable regardless of absolute link speed.
        up_pct = (up_rate / self._peak_up * 100) if self._peak_up > 0 else 0
        down_pct = (down_rate / self._peak_down * 100) if self._peak_down > 0 else 0
        self.traffic_chart.update_traffic(
            up_pct, down_pct,
            self._format_speed(up_rate), self._format_speed(down_rate))

    @staticmethod
    def _format_speed(bytes_per_sec: float) -> str:
        """Format bytes/sec into a human-readable speed string."""
        if bytes_per_sec < 1024:
            return f"{bytes_per_sec:.0f} B/s"
        elif bytes_per_sec < 1024 * 1024:
            return f"{bytes_per_sec / 1024:.1f} KB/s"
        else:
            return f"{bytes_per_sec / (1024 * 1024):.2f} MB/s"

    @staticmethod
    def _format_bytes(num_bytes: float) -> str:
        """Format a byte count into a human-readable size string."""
        num = float(num_bytes)
        for unit in ("B", "KB", "MB", "GB"):
            if num < 1024:
                return f"{num:.0f} {unit}" if unit == "B" else f"{num:.2f} {unit}"
            num /= 1024
        return f"{num:.2f} TB"
