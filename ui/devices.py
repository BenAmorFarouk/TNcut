"""
Devices widget for TNCut application.
Displays and manages discovered network devices.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableView, QPushButton,
    QLineEdit, QLabel, QMenu, QHeaderView, QAbstractItemView,
    QMessageBox, QSplitter, QFrame, QGroupBox, QFormLayout,
    QTextEdit, QComboBox, QSpinBox, QCheckBox,
    QSizePolicy, QSpacerItem
)
from PySide6.QtCore import Qt, Signal, Slot, QModelIndex, QSortFilterProxyModel
from typing import List
from PySide6.QtGui import QAction, QIcon, QKeySequence, QShortcut

from models import Device
from models.device_table_model import DeviceTableModel
from network.arp_spoof import arp_spoofer
from utils.logger import get_logger
import threading

logger = get_logger(__name__)


class DevicesWidget(QWidget):
    """Widget for displaying and managing network devices."""

    # Signals
    device_selected = Signal(object)  # Device object
    device_edit_requested = Signal(object)  # Device object
    device_delete_requested = Signal(object)  # Device object
    scan_requested = Signal()
    refresh_requested = Signal()

    def __init__(self):
        super().__init__()
        self.setObjectName("devices")
        self._current_devices: List[Device] = []
        self._table_model = DeviceTableModel()
        self._setup_ui()
        self._setup_connections()
        self.device_table.setModel(self._table_model)
        self.device_table.selectionModel().selectionChanged.connect(self._on_selection_changed)

    def _setup_ui(self):
        """Set up the devices user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Header
        header_layout = QHBoxLayout()
        title_label = QLabel("Network Devices")
        title_font = self.font()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search devices...")
        self.search_box.setClearButtonEnabled(True)
        self.search_box.setMaximumWidth(300)

        self.add_button = QPushButton("+ Add Device")
        self.add_button.setObjectName("addButton")
        self.add_button.setToolTip("Manually add a device")

        self.scan_button = QPushButton("🔍 Scan Network")
        self.scan_button.setObjectName("primaryButton")
        self.scan_button.setToolTip("Scan network for devices")

        self.refresh_button = QPushButton("🔄 Refresh")
        self.refresh_button.setObjectName("secondaryButton")
        self.refresh_button.setToolTip("Refresh device list")

        header_layout.addWidget(title_label)
        header_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        header_layout.addWidget(self.search_box)
        header_layout.addWidget(self.add_button)
        header_layout.addWidget(self.scan_button)
        header_layout.addWidget(self.refresh_button)

        layout.addLayout(header_layout)

        # Main content splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        # Device table
        table_frame = QFrame()
        table_frame.setFrameStyle(QFrame.StyledPanel)
        table_layout = QVBoxLayout(table_frame)

        self.device_table = QTableView()
        self.device_table.setObjectName("deviceTable")
        self.device_table.setAlternatingRowColors(True)
        self.device_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.device_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.device_table.setSortingEnabled(True)
        self.device_table.horizontalHeader().setStretchLastSection(True)
        self.device_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)

        table_layout.addWidget(self.device_table)

        # Table buttons
        table_buttons_layout = QHBoxLayout()
        self.edit_button = QPushButton("✏️ Edit")
        self.edit_button.setObjectName("actionButton")
        self.edit_button.setEnabled(False)

        self.delete_button = QPushButton("🗑️ Delete")
        self.delete_button.setObjectName("dangerButton")
        self.delete_button.setEnabled(False)

        self.wol_button = QPushButton("🌐 Wake-on-LAN")
        self.wol_button.setObjectName("actionButton")
        self.wol_button.setEnabled(False)

        self.scan_ports_button = QPushButton("🔍 Scan Ports")
        self.scan_ports_button.setObjectName("actionButton")
        self.scan_ports_button.setEnabled(False)

        table_buttons_layout.addWidget(self.edit_button)
        table_buttons_layout.addWidget(self.delete_button)
        table_buttons_layout.addWidget(self.wol_button)
        table_buttons_layout.addWidget(self.scan_ports_button)
        table_buttons_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        table_layout.addLayout(table_buttons_layout)
        splitter.addWidget(table_frame)

        # Device details panel
        details_frame = QFrame()
        details_frame.setFrameStyle(QFrame.StyledPanel)
        details_frame.setMaximumWidth(350)
        details_frame.setMinimumWidth(250)
        details_layout = QVBoxLayout(details_frame)

        details_title = QLabel("Device Details")
        details_font = self.font()
        details_font.setPointSize(14)
        details_font.setBold(True)
        details_title.setFont(details_font)
        details_layout.addWidget(details_title)

        # Device info form
        info_group = QGroupBox("Information")
        info_layout = QFormLayout()

        self.ip_label = QLabel("--")
        self.mac_label = QLabel("--")
        self.hostname_label = QLabel("--")
        self.vendor_label = QLabel("--")
        self.device_type_label = QLabel("--")
        self.status_label = QLabel("--")
        self.response_time_label = QLabel("--")
        self.last_seen_label = QLabel("--")

        info_layout.addRow("IP Address:", self.ip_label)
        info_layout.addRow("MAC Address:", self.mac_label)
        info_layout.addRow("Hostname:", self.hostname_label)
        info_layout.addRow("Vendor:", self.vendor_label)
        info_layout.addRow("Device Type:", self.device_type_label)
        info_layout.addRow("Status:", self.status_label)
        info_layout.addRow("Response Time:", self.response_time_label)
        info_layout.addRow("Last Seen:", self.last_seen_label)

        info_group.setLayout(info_layout)
        details_layout.addWidget(info_group)

        # Traffic stats
        traffic_group = QGroupBox("Traffic Statistics")
        traffic_layout = QFormLayout()

        self.bytes_sent_label = QLabel("--")
        self.bytes_received_label = QLabel("--")
        self.packets_sent_label = QLabel("--")
        self.packets_received_label = QLabel("--")

        traffic_layout.addRow("Data Sent:", self.bytes_sent_label)
        traffic_layout.addRow("Data Received:", self.bytes_received_label)
        traffic_layout.addRow("Packets Sent:", self.packets_sent_label)
        traffic_layout.addRow("Packets Received:", self.packets_received_label)

        traffic_group.setLayout(traffic_layout)
        details_layout.addWidget(traffic_group)

        # Notes
        notes_group = QGroupBox("Notes")
        notes_layout = QVBoxLayout()

        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Enter notes about this device...")
        self.notes_edit.setMaximumHeight(80)

        self.save_notes_button = QPushButton("💾 Save Notes")
        self.save_notes_button.setObjectName("actionButton")
        self.save_notes_button.setEnabled(False)

        notes_layout.addWidget(self.notes_edit)
        notes_layout.addWidget(self.save_notes_button)

        notes_group.setLayout(notes_layout)
        details_layout.addWidget(notes_group)

        # Actions
        actions_group = QGroupBox("Actions")
        actions_layout = QVBoxLayout()

        self.ping_button = QPushButton("📡 Ping")
        self.ping_button.setObjectName("actionButton")
        self.ping_button.setEnabled(False)

        self.traceroute_button = QPushButton("🛣️ Traceroute")
        self.traceroute_button.setObjectName("actionButton")
        self.traceroute_button.setEnabled(False)

        actions_layout.addWidget(self.ping_button)
        actions_layout.addWidget(self.traceroute_button)

        actions_group.setLayout(actions_layout)
        details_layout.addWidget(actions_group)

        details_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))

        splitter.addWidget(details_frame)

        # Set splitter sizes (70% table, 30% details)
        splitter.setSizes([700, 300])

        layout.addWidget(splitter)

        # Status bar
        status_layout = QHBoxLayout()
        self.device_count_label = QLabel("Devices: 0")
        self.selected_device_label = QLabel("No device selected")

        status_layout.addWidget(self.device_count_label)
        status_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        status_layout.addWidget(self.selected_device_label)

        layout.addLayout(status_layout)

    def _setup_connections(self):
        """Set up signal/slot connections."""
        # Buttons
        self.scan_button.clicked.connect(self.scan_requested.emit)
        self.refresh_button.clicked.connect(self.refresh_requested.emit)
        self.add_button.clicked.connect(self._on_add_device)
        self.edit_button.clicked.connect(self._on_edit_device)
        self.delete_button.clicked.connect(self._on_delete_device)
        self.wol_button.clicked.connect(self._on_wol)
        self.scan_ports_button.clicked.connect(self._on_scan_ports)
        self.ping_button.clicked.connect(self._on_ping)
        self.traceroute_button.clicked.connect(self._on_traceroute)
        self.save_notes_button.clicked.connect(self._on_save_notes)

        # Search
        self.search_box.textChanged.connect(self._on_search_text_changed)

        # Context menu
        self.device_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.device_table.customContextMenuRequested.connect(self._show_context_menu)

    def _on_selection_changed(self, selected, deselected):
        """Handle device table selection changes."""
        indexes = self.device_table.selectionModel().selectedRows()
        has_selection = len(indexes) > 0

        self.edit_button.setEnabled(has_selection)
        self.delete_button.setEnabled(has_selection)
        self.wol_button.setEnabled(has_selection)
        self.scan_ports_button.setEnabled(has_selection)
        self.ping_button.setEnabled(has_selection)
        self.traceroute_button.setEnabled(has_selection)
        self.save_notes_button.setEnabled(has_selection)

        if has_selection and hasattr(self, '_current_devices'):
            # Get selected device
            index = indexes[0].row()
            if 0 <= index < len(self._current_devices):
                device = self._current_devices[index]
                self._display_device_details(device)
                self.selected_device_label.setText(f"Selected: {device.hostname or device.ip_address}")
            else:
                self.selected_device_label.setText("Selected: Invalid device")
                self._clear_device_details()
        else:
            self.selected_device_label.setText("No device selected")
            self._clear_device_details()

    def _on_search_text_changed(self, text: str):
        """Handle search text changes."""
        # Implementation would filter the proxy model
        pass

    def _on_add_device(self):
        """Handle manual device addition."""
        QMessageBox.information(self, "Add Device", "Manual device addition feature coming soon.")

    def _on_edit_device(self):
        """Handle device edit request."""
        # Implementation would get selected device and emit signal
        pass

    def _on_delete_device(self):
        """Handle device delete request."""
        # Implementation would get selected device and emit signal
        reply = QMessageBox.question(
            self, "Delete Device",
            "Are you sure you want to delete this device?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            # Emit delete signal with selected device
            pass

    def _on_wol(self):
        """Handle Wake-on-LAN request."""
        QMessageBox.information(self, "Wake-on-LAN", "Wake-on-LAN feature coming soon.")

    def _on_scan_ports(self):
        """Handle port scan request."""
        QMessageBox.information(self, "Port Scan", "Port scanning feature coming soon.")

    def _on_ping(self):
        """Ping the selected device and show results."""
        sel_model = self.device_table.selectionModel()
        indexes = sel_model.selectedRows() if sel_model else []
        if not indexes or not self._current_devices:
            return
        row = indexes[0].row()
        if 0 <= row < len(self._current_devices):
            device = self._current_devices[row]
            ip = device.ip_address
            self.ping_button.setEnabled(False)
            self.ping_button.setText("Pinging...")

            import threading
            def do_ping():
                from network.scanner import network_scanner
                results = []
                for i in range(4):
                    ms = network_scanner.ping_host(ip, count=1, timeout=2)
                    results.append(ms)
                from PySide6.QtCore import QMetaObject, Qt as QtConst
                QMetaObject.invokeMethod(
                    self, "_show_ping_results",
                    QtConst.QueuedConnection,
                    ip, results
                )

            def do_ping_and_show():
                from network.scanner import network_scanner
                results = []
                for i in range(4):
                    ms = network_scanner.ping_host(ip, count=1, timeout=2)
                    results.append(ms)
                # Use QTimer.singleShot to update UI from main thread
                from PySide6.QtCore import QTimer
                QTimer.singleShot(0, lambda: self._show_ping_results(ip, results))

            t = threading.Thread(target=do_ping_and_show, daemon=True)
            t.start()

    def _show_ping_results(self, ip: str, results: list):
        """Display ping results in a dialog."""
        self.ping_button.setEnabled(True)
        self.ping_button.setText("📡 Ping")
        successful = [r for r in results if r is not None]
        lines = []
        for i, ms in enumerate(results, 1):
            if ms is not None:
                lines.append(f"  Reply {i}: {ms:.1f} ms")
            else:
                lines.append(f"  Reply {i}: Request timed out")
        lines.append("")
        if successful:
            avg = sum(successful) / len(successful)
            mn = min(successful)
            mx = max(successful)
            loss = ((len(results) - len(successful)) / len(results)) * 100
            lines.append(f"  Min: {mn:.1f} ms  Max: {mx:.1f} ms  Avg: {avg:.1f} ms")
            lines.append(f"  Packet loss: {loss:.0f}%")
            self.response_time_label.setText(f"{avg:.1f} ms")
        else:
            lines.append("  Host unreachable")

        QMessageBox.information(
            self, f"Ping {ip}",
            f"Pinging {ip} with 4 packets:\n\n" + "\n".join(lines)
        )

    def _on_traceroute(self):
        """Handle traceroute request."""
        QMessageBox.information(self, "Traceroute", "Traceroute feature coming soon.")

    def _get_selected_device(self):
        """Get the currently selected device."""
        sel_model = self.device_table.selectionModel()
        indexes = sel_model.selectedRows() if sel_model else []
        if not indexes or not self._current_devices:
            return None
        row = indexes[0].row()
        if 0 <= row < len(self._current_devices):
            return self._current_devices[row]
        return None

    def _on_limit_speed(self):
        """Show speed limit dialog for selected device."""
        device = self._get_selected_device()
        if not device:
            return

        from ui.speed_limit_dialog import SpeedLimitDialog
        current = arp_spoofer.get_limit(device.ip_address)
        dlg = SpeedLimitDialog(
            device.ip_address,
            device.hostname or "",
            current_limit_kbps=current,
            parent=self
        )
        if dlg.exec() == SpeedLimitDialog.Accepted:
            limit_kbps = dlg.get_limit_kbps()
            if limit_kbps is None:
                arp_spoofer.restore(device.ip_address)
            else:
                if not device.mac_address:
                    QMessageBox.warning(self, "Error", "Device has no MAC address.")
                    return
                ok = arp_spoofer.set_limit(device.ip_address, device.mac_address, limit_kbps)
                if not ok:
                    QMessageBox.warning(self, "Error",
                                        "Failed to set limit. Make sure you're running as Administrator.")
            self._refresh_limits()

    def _on_cut_internet(self):
        """Cut internet for selected device (limit=0)."""
        device = self._get_selected_device()
        if not device or not device.mac_address:
            return
        reply = QMessageBox.question(
            self, "Cut Internet",
            f"Cut internet for {device.hostname or device.ip_address}?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            ok = arp_spoofer.set_limit(device.ip_address, device.mac_address, 0)
            if not ok:
                QMessageBox.warning(self, "Error",
                                    "Failed. Make sure you're running as Administrator.")
            self._refresh_limits()

    def _on_restore_internet(self):
        """Restore internet for selected device."""
        device = self._get_selected_device()
        if not device:
            return
        arp_spoofer.restore(device.ip_address)
        self._refresh_limits()

    def _refresh_limits(self):
        """Update the Limit column with current ARP spoofer state."""
        self._table_model.update_limits(arp_spoofer.get_all_limits())

    def _on_save_notes(self):
        """Handle saving device notes."""
        sel_model = self.device_table.selectionModel()
        indexes = sel_model.selectedRows() if sel_model else []
        if not indexes or not self._current_devices:
            return
        row = indexes[0].row()
        if 0 <= row < len(self._current_devices):
            device = self._current_devices[row]
            notes_text = self.notes_edit.toPlainText()
            try:
                from database.session import get_db_session
                from models.models import Device as DeviceModel
                with get_db_session() as session:
                    db_device = session.query(DeviceModel).filter_by(
                        ip_address=device.ip_address
                    ).first()
                    if db_device:
                        db_device.notes = notes_text
                logger.info(f"Notes saved for {device.ip_address}")
            except Exception as e:
                logger.error(f"Error saving notes: {e}")
                QMessageBox.warning(self, "Error", f"Could not save notes: {e}")

    def _show_context_menu(self, position):
        """Show context menu for device table."""
        indexes = self.device_table.selectionModel().selectedRows()
        if not indexes:
            return

        row = indexes[0].row()
        device = self._current_devices[row] if 0 <= row < len(self._current_devices) else None

        menu = QMenu()

        edit_action = QAction("✏️ Edit", self)
        edit_action.triggered.connect(self._on_edit_device)
        menu.addAction(edit_action)

        delete_action = QAction("🗑️ Delete", self)
        delete_action.triggered.connect(self._on_delete_device)
        menu.addAction(delete_action)

        menu.addSeparator()

        wol_action = QAction("🌐 Wake-on-LAN", self)
        wol_action.triggered.connect(self._on_wol)
        menu.addAction(wol_action)

        ports_action = QAction("🔍 Scan Ports", self)
        ports_action.triggered.connect(self._on_scan_ports)
        menu.addAction(ports_action)

        menu.addSeparator()

        # Speed limit actions
        limit_action = QAction("⚡ Limit Speed...", self)
        limit_action.triggered.connect(self._on_limit_speed)
        menu.addAction(limit_action)

        cut_action = QAction("🔌 Cut Internet", self)
        cut_action.triggered.connect(self._on_cut_internet)
        menu.addAction(cut_action)

        if device and arp_spoofer.is_limited(device.ip_address):
            restore_action = QAction("✅ Restore Internet", self)
            restore_action.triggered.connect(self._on_restore_internet)
            menu.addAction(restore_action)

        menu.exec_(self.device_table.mapToGlobal(position))

    def _display_device_details(self, device: Device):
        """Display device details in the details panel."""
        self.ip_label.setText(device.ip_address or "--")
        self.mac_label.setText(device.mac_address or "--")
        self.hostname_label.setText(device.hostname or "--")
        self.vendor_label.setText(device.vendor or "--")
        self.device_type_label.setText(device.device_type or "--")
        self.status_label.setText("Online" if device.is_online else "Offline")
        self.response_time_label.setText(f"{device.response_time} ms" if device.response_time else "--")
        self.last_seen_label.setText(
            device.last_seen.strftime("%Y-%m-%d %H:%M:%S") if device.last_seen else "--"
        )

        self.bytes_sent_label.setText("0 B")
        self.bytes_received_label.setText("0 B")
        self.packets_sent_label.setText("0")
        self.packets_received_label.setText("0")

        # Load notes from database
        try:
            from database.session import get_db_session
            from models.models import Device as DeviceModel
            with get_db_session() as session:
                db_device = session.query(DeviceModel).filter_by(
                    ip_address=device.ip_address
                ).first()
                if db_device and db_device.notes:
                    self.notes_edit.setPlainText(db_device.notes)
                else:
                    self.notes_edit.clear()
        except Exception:
            self.notes_edit.clear()

        self.save_notes_button.setEnabled(bool(device))

    def _clear_device_details(self):
        """Clear device details panel."""
        self.ip_label.setText("--")
        self.mac_label.setText("--")
        self.hostname_label.setText("--")
        self.vendor_label.setText("--")
        self.device_type_label.setText("--")
        self.status_label.setText("--")
        self.response_time_label.setText("--")
        self.last_seen_label.setText("--")
        self.bytes_sent_label.setText("--")
        self.bytes_received_label.setText("--")
        self.packets_sent_label.setText("--")
        self.packets_received_label.setText("--")
        self.notes_edit.clear()
        self.save_notes_button.setEnabled(False)

    def update_device_count(self, count: int):
        """Update the device count display."""
        self.device_count_label.setText(f"Devices: {count}")

    def update_devices(self, devices):
        """
        Update the device list with new data from network service.

        Args:
            devices: List of Device objects
        """
        self._current_devices = devices
        self._table_model.set_devices(devices)
        self.update_device_count(len(devices))

        sel_model = self.device_table.selectionModel()
        if sel_model and sel_model.selectedRows():
            pass
        else:
            self._clear_device_details()

        logger.debug(f"Updated device list with {len(devices)} devices")

    # Placeholder methods for model integration
    def set_device_model(self, model):
        """Set the device data model."""
        self.device_table.setModel(model)
        self.device_table.selectionModel().selectionChanged.connect(self._on_selection_changed)

    def refresh_devices(self):
        """Refresh the device list."""
        # Implementation would refresh the underlying model
        pass