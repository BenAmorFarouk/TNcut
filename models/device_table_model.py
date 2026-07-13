"""
Qt table model for displaying network devices.
"""

from typing import List, Any, Optional, Dict
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PySide6.QtGui import QColor

from models.models import Device


COLUMNS = [
    ("Status", "is_online"),
    ("IP Address", "ip_address"),
    ("MAC Address", "mac_address"),
    ("Hostname", "hostname"),
    ("Vendor", "vendor"),
    ("Type", "device_type"),
    ("Response (ms)", "response_time"),
    ("Last Seen", "last_seen"),
    ("Limit", "_limit"),
]


class DeviceTableModel(QAbstractTableModel):
    """Table model for the device list."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._devices: List[Device] = []
        self._limits: Dict[str, int] = {}

    def set_devices(self, devices: List[Device]):
        self.beginResetModel()
        self._devices = list(devices)
        self.endResetModel()

    def update_limits(self, limits: Dict[str, int]):
        """Update the limits dict and refresh the Limit column."""
        self._limits = dict(limits)
        if self._devices:
            limit_col = len(COLUMNS) - 1
            self.dataChanged.emit(
                self.index(0, limit_col),
                self.index(len(self._devices) - 1, limit_col)
            )

    def get_device(self, row: int) -> Optional[Device]:
        if 0 <= row < len(self._devices):
            return self._devices[row]
        return None

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._devices)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(COLUMNS)

    def headerData(self, section: int, orientation: Qt.Orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return COLUMNS[section][0]
        return None

    def data(self, index: QModelIndex, role=Qt.DisplayRole) -> Any:
        if not index.isValid() or index.row() >= len(self._devices):
            return None

        device = self._devices[index.row()]
        col_attr = COLUMNS[index.column()][1]

        if role == Qt.DisplayRole:
            if col_attr == "is_online":
                return "Online" if device.is_online else "Offline"
            elif col_attr == "last_seen":
                return device.last_seen.strftime("%Y-%m-%d %H:%M:%S") if device.last_seen else "--"
            elif col_attr == "response_time":
                return str(device.response_time) if device.response_time else "--"
            elif col_attr == "_limit":
                limit_kbps = self._limits.get(device.ip_address)
                if limit_kbps is None:
                    return "--"
                if limit_kbps == 0:
                    return "CUT"
                if limit_kbps >= 1000:
                    return f"{limit_kbps / 1000:.1f} Mbps"
                return f"{limit_kbps} KB/s"
            else:
                return getattr(device, col_attr, "--") or "--"

        elif role == Qt.ForegroundRole:
            if col_attr == "is_online":
                return QColor("#28a745") if device.is_online else QColor("#dc3545")
            elif col_attr == "_limit":
                limit_kbps = self._limits.get(device.ip_address)
                if limit_kbps is not None:
                    if limit_kbps == 0:
                        return QColor("#dc3545")
                    return QColor("#fd7e14")

        elif role == Qt.TextAlignmentRole:
            if col_attr in ("is_online", "response_time", "_limit"):
                return Qt.AlignCenter

        return None

    def sort(self, column: int, order=Qt.AscendingOrder):
        self.beginResetModel()
        attr = COLUMNS[column][1]
        reverse = order == Qt.DescendingOrder

        def sort_key(d):
            val = getattr(d, attr, None)
            if val is None:
                return ""
            return val

        self._devices.sort(key=sort_key, reverse=reverse)
        self.endResetModel()
