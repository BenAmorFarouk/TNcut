"""
Logs widget for TNCut application.
Displays application logs with level filtering and auto-tail.
"""

from typing import List, Any
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableView, QHeaderView, QAbstractItemView, QComboBox,
    QLineEdit, QCheckBox, QSizePolicy, QSpacerItem
)
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, QTimer
from PySide6.QtGui import QColor

from utils.logger import get_logger

logger = get_logger(__name__)


LOG_COLUMNS = [
    ("Timestamp", "timestamp"),
    ("Level", "level"),
    ("Logger", "logger_name"),
    ("Message", "message"),
    ("Module", "module"),
    ("Function", "function"),
    ("Line", "line_number"),
]

LEVEL_COLORS = {
    "DEBUG": "#6c757d",
    "INFO": "#17a2b8",
    "WARNING": "#ffc107",
    "ERROR": "#dc3545",
    "CRITICAL": "#ff0000",
}


class LogTableModel(QAbstractTableModel):
    """Table model for application log records."""

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
        return len(LOG_COLUMNS)

    def headerData(self, section: int, orientation: Qt.Orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return LOG_COLUMNS[section][0]
        return None

    def data(self, index: QModelIndex, role=Qt.DisplayRole) -> Any:
        if not index.isValid() or index.row() >= len(self._records):
            return None

        record = self._records[index.row()]
        col_key = LOG_COLUMNS[index.column()][1]

        if role == Qt.DisplayRole:
            if col_key == "timestamp":
                ts = record.get("timestamp")
                return ts.strftime("%Y-%m-%d %H:%M:%S") if ts else "--"
            elif col_key == "line_number":
                val = record.get("line_number")
                return str(val) if val else "--"
            return record.get(col_key, "--") or "--"

        elif role == Qt.ForegroundRole:
            if col_key == "level":
                level = record.get("level", "")
                color = LEVEL_COLORS.get(level)
                if color:
                    return QColor(color)

        elif role == Qt.BackgroundRole:
            level = record.get("level", "")
            if level == "ERROR":
                return QColor(220, 53, 69, 30)
            elif level == "CRITICAL":
                return QColor(255, 0, 0, 40)

        return None


class LogsWidget(QWidget):
    """Widget for displaying application and network logs."""

    def __init__(self):
        super().__init__()
        self.setObjectName("logs")
        self._model = LogTableModel()
        self._auto_scroll = True
        self._setup_ui()
        self._setup_timer()
        logger.debug("Logs widget initialized")

    def _setup_ui(self):
        """Set up the logs widget user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Title
        title = QLabel("System Logs")
        title_font = self.font()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        # Filter bar
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(10)

        # Level filter
        filter_layout.addWidget(QLabel("Level:"))
        self.level_filter = QComboBox()
        self.level_filter.addItems(["All Levels", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.level_filter.currentIndexChanged.connect(self._load_logs)
        filter_layout.addWidget(self.level_filter)

        # Search filter
        filter_layout.addWidget(QLabel("Search:"))
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Filter by message content...")
        self.search_box.setClearButtonEnabled(True)
        self.search_box.setMaximumWidth(300)
        self.search_box.textChanged.connect(self._load_logs)
        filter_layout.addWidget(self.search_box)

        filter_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        # Auto-scroll toggle
        self.auto_scroll_check = QCheckBox("Auto-scroll")
        self.auto_scroll_check.setChecked(True)
        self.auto_scroll_check.toggled.connect(self._on_auto_scroll_toggled)
        filter_layout.addWidget(self.auto_scroll_check)

        layout.addLayout(filter_layout)

        # Action bar
        action_layout = QHBoxLayout()

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self._load_logs)
        action_layout.addWidget(self.refresh_button)

        self.clear_button = QPushButton("Clear Logs")
        self.clear_button.clicked.connect(self._clear_logs)
        action_layout.addWidget(self.clear_button)

        action_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        self.log_count_label = QLabel("Entries: 0")
        action_layout.addWidget(self.log_count_label)

        layout.addLayout(action_layout)

        # Table
        self.table = QTableView()
        self.table.setModel(self._model)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setSortingEnabled(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.verticalHeader().setVisible(False)
        # Set reasonable default column widths
        self.table.setColumnWidth(0, 150)  # Timestamp
        self.table.setColumnWidth(1, 70)   # Level
        self.table.setColumnWidth(2, 120)  # Logger
        self.table.setColumnWidth(3, 400)  # Message
        self.table.setColumnWidth(4, 100)  # Module
        self.table.setColumnWidth(5, 100)  # Function
        self.table.setColumnWidth(6, 50)   # Line
        layout.addWidget(self.table)

    def _setup_timer(self):
        """Set up auto-refresh timer."""
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self._load_logs)
        self.refresh_timer.start(5000)

    def _load_logs(self):
        """Load log records from database."""
        try:
            from database.session import get_db_session
            from models.models import ApplicationLog

            with get_db_session() as session:
                query = session.query(ApplicationLog)

                # Apply level filter
                level_text = self.level_filter.currentText()
                if level_text != "All Levels":
                    query = query.filter(ApplicationLog.level == level_text)

                # Apply search filter
                search_text = self.search_box.text().strip()
                if search_text:
                    query = query.filter(
                        ApplicationLog.message.ilike(f"%{search_text}%")
                    )

                query = query.order_by(ApplicationLog.timestamp.desc())
                results = query.limit(500).all()

                records = []
                for r in results:
                    records.append({
                        "timestamp": r.timestamp,
                        "level": r.level,
                        "logger_name": r.logger_name,
                        "message": r.message,
                        "module": r.module,
                        "function": r.function,
                        "line_number": r.line_number,
                    })

                # Reverse so newest is at bottom (natural log order)
                records.reverse()
                self._model.set_records(records)
                self.log_count_label.setText(f"Entries: {len(records)}")

                # Auto-scroll to bottom
                if self._auto_scroll and records:
                    self.table.scrollToBottom()

        except Exception as e:
            logger.error(f"Error loading logs: {e}")

    def _clear_logs(self):
        """Clear all log records from database."""
        try:
            from database.session import get_db_session
            from models.models import ApplicationLog

            with get_db_session() as session:
                session.query(ApplicationLog).delete()

            self._load_logs()
            logger.info("Logs cleared")
        except Exception as e:
            logger.error(f"Error clearing logs: {e}")

    def _on_auto_scroll_toggled(self, checked: bool):
        """Handle auto-scroll toggle."""
        self._auto_scroll = checked
