"""
Speed limit dialog for setting per-device bandwidth limits.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
    QSpinBox, QComboBox, QDialogButtonBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class SpeedLimitDialog(QDialog):
    """Dialog for setting a device's bandwidth limit (value in KB/s)."""

    def __init__(self, device_ip: str, device_hostname: str = "",
                 current_limit_kbps: int = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Set Speed Limit")
        self.setFixedSize(420, 280)
        self._limit_kbps = current_limit_kbps  # None = no limit

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Device info
        device_label = QLabel(device_hostname or device_ip)
        device_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        device_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(device_label)

        if device_hostname:
            ip_label = QLabel(f"({device_ip})")
            ip_label.setAlignment(Qt.AlignCenter)
            ip_label.setStyleSheet("color: #888;")
            layout.addWidget(ip_label)

        # Value + Unit row
        input_layout = QHBoxLayout()

        self.spinbox = QSpinBox()
        self.spinbox.setRange(0, 100000)
        self.spinbox.setFixedWidth(120)

        self.unit_combo = QComboBox()
        self.unit_combo.addItems(["KB/s", "Mbps"])
        self.unit_combo.setFixedWidth(80)

        # Set initial values from current limit
        if current_limit_kbps is not None and current_limit_kbps > 0:
            if current_limit_kbps >= 1000 and current_limit_kbps % 1000 == 0:
                self.spinbox.setValue(current_limit_kbps // 1000)
                self.unit_combo.setCurrentIndex(1)  # Mbps
            else:
                self.spinbox.setValue(current_limit_kbps)
                self.unit_combo.setCurrentIndex(0)  # KB/s
        else:
            self.spinbox.setValue(0)
            self.unit_combo.setCurrentIndex(1)

        input_layout.addStretch()
        input_layout.addWidget(QLabel("Speed:"))
        input_layout.addWidget(self.spinbox)
        input_layout.addWidget(self.unit_combo)
        input_layout.addStretch()
        layout.addLayout(input_layout)

        self.spinbox.valueChanged.connect(self._update_status)
        self.unit_combo.currentIndexChanged.connect(self._update_status)

        # Quick presets
        presets_layout = QHBoxLayout()
        presets_label = QLabel("Presets:")
        presets_label.setStyleSheet("color: #888;")
        presets_layout.addWidget(presets_label)

        for label, kbps in [("Cut", 0), ("128 KB/s", 128), ("256 KB/s", 256),
                            ("512 KB/s", 512), ("1 Mbps", 1000), ("5 Mbps", 5000),
                            ("No Limit", -1)]:
            btn = QLabel(f'<a href="#">{label}</a>')
            btn.setStyleSheet("font-size: 11px;")
            btn.linkActivated.connect(lambda _, k=kbps: self._apply_preset(k))
            presets_layout.addWidget(btn)

        presets_layout.addStretch()
        layout.addLayout(presets_layout)

        # Status label
        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont("Segoe UI", 11))
        layout.addWidget(self.status_label)
        self._update_status()

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _apply_preset(self, kbps: int):
        if kbps == -1:
            # No limit
            self.spinbox.setValue(0)
            self.unit_combo.setCurrentIndex(1)
            self._limit_kbps = None
            self._update_status()
            self.accept()
            return
        if kbps == 0:
            self.spinbox.setValue(0)
            self.unit_combo.setCurrentIndex(0)
        elif kbps >= 1000:
            self.spinbox.setValue(kbps // 1000)
            self.unit_combo.setCurrentIndex(1)
        else:
            self.spinbox.setValue(kbps)
            self.unit_combo.setCurrentIndex(0)

    def _update_status(self):
        value = self.spinbox.value()
        is_mbps = self.unit_combo.currentIndex() == 1

        if value == 0 and not is_mbps:
            self._limit_kbps = 0
            self.status_label.setText("Device will be DISCONNECTED")
            self.status_label.setStyleSheet("color: #dc3545; font-weight: bold;")
        elif value == 0 and is_mbps:
            self._limit_kbps = None
            self.status_label.setText("No limit (full speed)")
            self.status_label.setStyleSheet("color: #28a745;")
        else:
            if is_mbps:
                self._limit_kbps = value * 1000
                self.status_label.setText(f"Limited to {value} Mbps")
            else:
                self._limit_kbps = value
                self.status_label.setText(f"Limited to {value} KB/s")
            self.status_label.setStyleSheet("color: #fd7e14;")

    def get_limit_kbps(self) -> int:
        """Return limit in KB/s. 0=cut, None=no limit/restore."""
        return self._limit_kbps
