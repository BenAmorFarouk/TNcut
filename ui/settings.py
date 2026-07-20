"""
Settings widget for TNCut application.
Manages application configuration and preferences.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QFormLayout, QLineEdit, QSpinBox, QComboBox,
    QCheckBox, QGroupBox, QSlider, QColorDialog
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from utils.logger import get_logger
from utils.theme import ThemeManager
from config.settings import settings_manager

logger = get_logger(__name__)


class SettingsWidget(QWidget):
    """Widget for managing application settings."""

    def __init__(self):
        super().__init__()
        self.setObjectName("settings")
        self._setup_ui()
        self._load_settings()
        logger.debug("Settings widget initialized")

    def _setup_ui(self):
        """Set up the settings widget user interface."""
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignTop)

        title = QLabel("Settings")
        title.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 20px;")
        layout.addWidget(title)

        # Tab widget for different settings categories
        tabs = QTabWidget()
        layout.addWidget(tabs)

        # Network tab
        network_tab = self._create_network_tab()
        tabs.addTab(network_tab, "Network")

        # UI/Theme tab
        ui_tab = self._create_ui_tab()
        tabs.addTab(ui_tab, "Interface")

        # Notifications tab
        notifications_tab = self._create_notifications_tab()
        tabs.addTab(notifications_tab, "Notifications")

        # About tab
        about_tab = self._create_about_tab()
        tabs.addTab(about_tab, "About")

        # Save button
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        save_button = QPushButton("Save Settings")
        save_button.clicked.connect(self._save_settings)
        button_layout.addWidget(save_button)

        reset_button = QPushButton("Reset to Defaults")
        reset_button.clicked.connect(self._reset_settings)
        button_layout.addWidget(reset_button)

        layout.addLayout(button_layout)

    def _create_network_tab(self) -> QWidget:
        """Create the network settings tab."""
        tab = QWidget()
        layout = QFormLayout(tab)

        # Scan interface selection
        self.interface_combo = QComboBox()
        self.interface_combo.setToolTip(
            "Network adapter used for scanning and ARP control. "
            "Auto picks the adapter for your default route. "
            "Choose explicitly if you switch between Wi-Fi and Ethernet."
        )
        self._populate_interfaces()
        layout.addRow("Scan Interface:", self.interface_combo)

        # Refresh interval
        self.refresh_interval = QSpinBox()
        self.refresh_interval.setRange(1000, 60000)  # 1 second to 60 seconds
        self.refresh_interval.setSingleStep(1000)
        self.refresh_interval.setSuffix(" ms")
        layout.addRow("Discovery Interval:", self.refresh_interval)

        # Discovery timeout
        self.discovery_timeout = QSpinBox()
        self.discovery_timeout.setRange(1000, 30000)
        self.discovery_timeout.setSingleStep(1000)
        self.discovery_timeout.setSuffix(" ms")
        layout.addRow("Discovery Timeout:", self.discovery_timeout)

        # Ping count
        self.ping_count = QSpinBox()
        self.ping_count.setRange(1, 10)
        layout.addRow("Ping Count:", self.ping_count)

        # Port scan timeout
        self.port_scan_timeout = QSpinBox()
        self.port_scan_timeout.setRange(100, 5000)
        self.port_scan_timeout.setSingleStep(100)
        self.port_scan_timeout.setSuffix(" ms")
        layout.addRow("Port Scan Timeout:", self.port_scan_timeout)

        # Bandwidth limit
        bw_layout = QHBoxLayout()
        self.bandwidth_limit = QSpinBox()
        self.bandwidth_limit.setRange(1, 100)
        self.bandwidth_limit.setValue(100)
        self.bandwidth_limit.setSuffix(" Mbps")
        self.bandwidth_limit.setToolTip("Set your internet bandwidth limit (1-100 Mbps). Used to calculate usage percentage on the dashboard charts.")
        bw_layout.addWidget(self.bandwidth_limit)
        self.bandwidth_label = QLabel("Used for dashboard speed % charts")
        self.bandwidth_label.setStyleSheet("color: #888;")
        bw_layout.addWidget(self.bandwidth_label)
        bw_layout.addStretch()
        layout.addRow("Bandwidth Limit:", bw_layout)

        return tab

    def _populate_interfaces(self):
        """Fill the interface dropdown with Auto + available network adapters."""
        self.interface_combo.clear()
        # First item: auto-detect (empty string stored)
        self.interface_combo.addItem("Auto (detect active network)", "")
        try:
            from network.scanner import network_scanner
            for iface in network_scanner.list_interfaces():
                label = iface["name"]
                if iface.get("ip"):
                    label = f"{iface['name']} — {iface['ip']}"
                self.interface_combo.addItem(label, iface["name"])
        except Exception as e:
            logger.warning(f"Could not list interfaces: {e}")

    def _create_ui_tab(self) -> QWidget:
        """Create the UI/theme settings tab."""
        tab = QWidget()
        layout = QFormLayout(tab)

        # Theme selection
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light"])
        self.theme_combo.currentTextChanged.connect(self._on_theme_changed)
        layout.addRow("Theme:", self.theme_combo)

        # Animation speed
        self.animation_speed = QSlider(Qt.Horizontal)
        self.animation_speed.setRange(100, 1000)
        self.animation_speed.setValue(250)
        self.animation_speed.setTickPosition(QSlider.TicksBelow)
        self.animation_speed.setTickInterval(100)
        layout.addRow("Animation Speed:", self.animation_speed)

        # Enable animations
        self.enable_animations = QCheckBox()
        self.enable_animations.setChecked(True)
        layout.addRow("Enable Animations:", self.enable_animations)

        return tab

    def _create_notifications_tab(self) -> QWidget:
        """Create the notifications settings tab."""
        tab = QWidget()
        layout = QFormLayout(tab)

        # Enable notifications
        self.enable_notifications = QCheckBox()
        self.enable_notifications.setChecked(True)
        layout.addRow("Enable Notifications:", self.enable_notifications)

        # New device alerts
        self.new_device_alert = QCheckBox()
        self.new_device_alert.setChecked(True)
        layout.addRow("New Device Alerts:", self.new_device_alert)

        # Device disconnect alerts
        self.device_disconnect_alert = QCheckBox()
        self.device_disconnect_alert.setChecked(True)
        layout.addRow("Device Disconnect Alerts:", self.device_disconnect_alert)

        # High bandwidth alerts
        self.high_bandwidth_alert = QCheckBox()
        self.high_bandwidth_alert.setChecked(True)
        layout.addRow("High Bandwidth Alerts:", self.high_bandwidth_alert)

        # Gateway unreachable alerts
        self.gateway_unreachable_alert = QCheckBox()
        self.gateway_unreachable_alert.setChecked(True)
        layout.addRow("Gateway Unreachable Alerts:", self.gateway_unreachable_alert)

        # Internet disconnected alerts
        self.internet_disconnected_alert = QCheckBox()
        self.internet_disconnected_alert.setChecked(True)
        layout.addRow("Internet Disconnected Alerts:", self.internet_disconnected_alert)

        return tab

    def _create_about_tab(self) -> QWidget:
        """Create the about tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setAlignment(Qt.AlignTop)

        title = QLabel("About TNCut")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        version = QLabel("Version 1.0.1")
        layout.addWidget(version)

        description = QLabel(
            "TNCut is a network monitoring and analysis tool "
            "designed for home and small business networks."
        )
        layout.addWidget(description)

        # Spacer
        layout.addStretch()

        return tab

    def _load_settings(self):
        """Load current settings into the UI."""
        settings = settings_manager.get()

        # Network settings
        if hasattr(settings, 'network'):
            saved_iface = getattr(settings.network, 'interface', "")
            idx = self.interface_combo.findData(saved_iface)
            self.interface_combo.setCurrentIndex(idx if idx >= 0 else 0)
            self.refresh_interval.setValue(settings.network.refresh_interval)
            self.discovery_timeout.setValue(settings.network.timeout * 1000)  # Convert to ms
            self.ping_count.setValue(settings.network.ping_count)
            self.port_scan_timeout.setValue(int(settings.network.port_scan_timeout * 1000))
            self.bandwidth_limit.setValue(getattr(settings.network, 'bandwidth_limit', 100))

        # UI settings
        if hasattr(settings, 'ui'):
            index = 0 if settings.ui.theme == "dark" else 1
            self.theme_combo.setCurrentIndex(index)
            self.animation_speed.setValue(settings.ui.animation_duration)
            self.enable_animations.setChecked(settings.ui.show_animations)

        # Notification settings
        if hasattr(settings, 'notifications'):
            self.enable_notifications.setChecked(settings.notifications.enabled)
            self.new_device_alert.setChecked(settings.notifications.new_device)
            self.device_disconnect_alert.setChecked(settings.notifications.device_disconnect)
            self.high_bandwidth_alert.setChecked(settings.notifications.high_bandwidth)
            self.gateway_unreachable_alert.setChecked(settings.notifications.gateway_unreachable)
            self.internet_disconnected_alert.setChecked(settings.notifications.internet_disconnected)

    def _save_settings(self):
        """Save settings from UI to configuration."""
        try:
            settings = settings_manager.get()

            # Update network settings
            if not hasattr(settings, 'network'):
                from config.settings import NetworkSettings
                settings.network = NetworkSettings()

            settings.network.refresh_interval = self.refresh_interval.value()
            settings.network.timeout = self.discovery_timeout.value() // 1000  # Convert to seconds
            settings.network.ping_count = self.ping_count.value()
            settings.network.port_scan_timeout = self.port_scan_timeout.value() / 1000.0  # Convert to seconds
            settings.network.bandwidth_limit = self.bandwidth_limit.value()

            # Apply the chosen scan interface immediately
            chosen_iface = self.interface_combo.currentData()
            settings.network.interface = chosen_iface or ""
            try:
                from network.scanner import network_scanner
                network_scanner.set_interface(settings.network.interface)
            except Exception as e:
                logger.warning(f"Could not apply scan interface: {e}")

            # Update UI settings
            if not hasattr(settings, 'ui'):
                from config.settings import UISettings
                settings.ui = UISettings()

            settings.ui.theme = "dark" if self.theme_combo.currentIndex() == 0 else "light"
            settings.ui.animation_duration = self.animation_speed.value()
            settings.ui.show_animations = self.enable_animations.isChecked()

            # Update notification settings
            if not hasattr(settings, 'notifications'):
                from config.settings import NotificationSettings
                settings.notifications = NotificationSettings()

            settings.notifications.enabled = self.enable_notifications.isChecked()
            settings.notifications.new_device = self.new_device_alert.isChecked()
            settings.notifications.device_disconnect = self.device_disconnect_alert.isChecked()
            settings.notifications.high_bandwidth = self.high_bandwidth_alert.isChecked()
            settings.notifications.gateway_unreachable = self.gateway_unreachable_alert.isChecked()
            settings.notifications.internet_disconnected = self.internet_disconnected_alert.isChecked()

            # Save to file
            settings_manager.save()

            # Apply theme immediately
            theme_mode = "dark" if self.theme_combo.currentIndex() == 0 else "light"
            from utils.theme import ThemeMode
            ThemeManager().set_theme_mode(
                ThemeMode.DARK if theme_mode == "dark" else ThemeMode.LIGHT
            )

            logger.info("Settings saved successfully")

        except Exception as e:
            logger.error(f"Error saving settings: {e}")

    def _reset_settings(self):
        """Reset settings to default values."""
        settings_manager.reset_to_defaults()
        self._load_settings()
        logger.info("Settings reset to defaults")

    def _on_theme_changed(self, theme_name: str):
        """Handle theme selection changes."""
        # Preview the theme change
        theme_mode = "dark" if theme_name.lower() == "dark" else "light"
        from utils.theme import ThemeMode
        # Apply immediately for preview
        # Note: In a real app, you might want to apply on save only