"""
History widget for TNCut application.
Displays historical device events with filtering capabilities.
"""

from datetime import datetime, timedelta
from typing import List, Any, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableView, QHeaderView, QAbstractItemView, QComboBox,
    QDateEdit, QLineEdit, QGroupBox, QSizePolicy, QSpacerItem
)
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, QDate, QTimer
from PySide6.QtGui import QColor

from utils.logger import get_logger

logger = get_logger(__name__)


HISTORY_COLUMNS = [
    ("Timestamp", "timestamp"),
    ("Device", "device_display"),
    ("Event Type", "event_type"),
    ("Description", "description"),
    ("Old Value", "old_value"),
    ("New Value", "new_value"),
]


class HistoryTableModel(QAbstractTableModel):
    """Table model for device history records."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._records: List[dict] = []

    def set_records(self, records: List[dict]):
        self.beginResetModel()
        self._records = list(records)
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._records)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(HISTORY_COLUMNS)

    def headerData(self, section: int, orientation: Qt.Orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return HISTORY_COLUMNS[section][0]
        return None

    def data(self, index: QModelIndex, role=Qt.DisplayRole) -> Any:
        if not index.isValid() or index.row() >= len(self._records):
            return None

        record = self._records[index.row()]
        col_key = HISTORY_COLUMNS[index.column()][1]

        if role == Qt.DisplayRole:
            if col_key == "timestamp":
                ts = record.get("timestamp")
                return ts.strftime("%Y-%m-%d %H:%M:%S") if ts else "--"
            return record.get(col_key, "--") or "--"

        elif role == Qt.ForegroundRole:
            if col_key == "event_type":
                event = record.get("event_type", "")
                color_map = {
                    "joined": "#28a745",
                    "left": "#dc3545",
                    "ip_changed": "#ffc107",
                }
                color = color_map.get(event)
                if color:
                    return QColor(color)

        return None


class HistoryWidget(QWidget):
    """Widget for displaying historical network and device data."""

    def __init__(self):
        super().__init__()
        self.setObjectName("history")
        self._model = HistoryTableModel()
        self._setup_ui()
        self._setup_timer()
        logger.debug("History widget initialized")

    def _setup_ui(self):
        """Set up the history widget user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Title
        title = QLabel("Network History")
        title_font = self.font()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        # Filter bar
        filter_group = QGroupBox("Filters")
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(10)

        # Device filter
        filter_layout.addWidget(QLabel("Device:"))
        self.device_filter = QComboBox()
        self.device_filter.addItem("All Devices", None)
        self.device_filter.setMinimumWidth(150)
        self.device_filter.currentIndexChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.device_filter)

        # Event type filter
        filter_layout.addWidget(QLabel("Event:"))
        self.event_filter = QComboBox()
        self.event_filter.addItems(["All Events", "joined", "left", "ip_changed"])
        self.event_filter.currentIndexChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.event_filter)

        # Date range
        filter_layout.addWidget(QLabel("From:"))
        self.date_from = QDateEdit()
        self.date_from.setDate(QDate.currentDate().addDays(-7))
        self.date_from.setCalendarPopup(True)
        self.date_from.dateChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.date_from)

        filter_layout.addWidget(QLabel("To:"))
        self.date_to = QDateEdit()
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setCalendarPopup(True)
        self.date_to.dateChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.date_to)

        filter_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)

        # Action bar
        action_layout = QHBoxLayout()

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self._load_history)
        action_layout.addWidget(self.refresh_button)

        self.clear_button = QPushButton("Clear History")
        self.clear_button.clicked.connect(self._clear_history)
        action_layout.addWidget(self.clear_button)

        action_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        self.record_count_label = QLabel("Records: 0")
        action_layout.addWidget(self.record_count_label)

        layout.addLayout(action_layout)

        # Table
        self.table = QTableView()
        self.table.setModel(self._model)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

    def _setup_timer(self):
        """Set up auto-refresh timer."""
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self._load_history)
        self.refresh_timer.start(10000)

    def _load_history(self):
        """Load history records from database."""
        try:
            from database.session import get_db_session
            from models.models import DeviceHistory, Device

            with get_db_session() as session:
                query = session.query(DeviceHistory).join(
                    Device, DeviceHistory.device_id == Device.id, isouter=True
                )

                # Apply device filter
                device_id = self.device_filter.currentData()
                if device_id is not None:
                    query = query.filter(DeviceHistory.device_id == device_id)

                # Apply event type filter
                event_text = self.event_filter.currentText()
                if event_text != "All Events":
                    query = query.filter(DeviceHistory.event_type == event_text)

                # Apply date range
                date_from = self.date_from.date().toPython()
                date_to = self.date_to.date().toPython()
                from_dt = datetime(date_from.year, date_from.month, date_from.day)
                to_dt = datetime(date_to.year, date_to.month, date_to.day, 23, 59, 59)
                query = query.filter(DeviceHistory.timestamp.between(from_dt, to_dt))

                query = query.order_by(DeviceHistory.timestamp.desc())
                results = query.limit(1000).all()

                records = []
                for r in results:
                    device_display = "--"
                    if r.device:
                        device_display = r.device.hostname or r.device.ip_address
                    records.append({
                        "timestamp": r.timestamp,
                        "device_display": device_display,
                        "event_type": r.event_type,
                        "description": r.description,
                        "old_value": r.old_value,
                        "new_value": r.new_value,
                    })

                self._model.set_records(records)
                self.record_count_label.setText(f"Records: {len(records)}")

        except Exception as e:
            logger.error(f"Error loading history: {e}")

    def _apply_filters(self):
        """Apply current filters and reload data."""
        self._load_history()

    def _clear_history(self):
        """Clear all history records."""
        try:
            from database.session import get_db_session
            from models.models import DeviceHistory

            with get_db_session() as session:
                session.query(DeviceHistory).delete()

            self._load_history()
            logger.info("History cleared")
        except Exception as e:
            logger.error(f"Error clearing history: {e}")

    def update_device_list(self, devices):
        """Update the device filter combo box."""
        current = self.device_filter.currentData()
        self.device_filter.blockSignals(True)
        self.device_filter.clear()
        self.device_filter.addItem("All Devices", None)
        for d in devices:
            label = d.hostname or d.ip_address
            self.device_filter.addItem(f"{label} ({d.ip_address})", d.id)
        # Restore selection
        for i in range(self.device_filter.count()):
            if self.device_filter.itemData(i) == current:
                self.device_filter.setCurrentIndex(i)
                break
        self.device_filter.blockSignals(False)
