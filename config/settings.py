"""
Application settings and configuration management.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass, asdict, field


@dataclass
class NetworkSettings:
    """Network-related settings."""
    refresh_interval: int = 5000  # milliseconds
    discovery_interval: int = 30000  # milliseconds
    timeout: int = 5  # seconds
    ping_count: int = 3
    port_scan_timeout: float = 1.0
    bandwidth_limit: int = 100  # Mbps (0-100), used for speed percentage charts


@dataclass
class UISettings:
    """User interface settings."""
    theme: str = "dark"  # "dark" or "light"
    sidebar_width: int = 250
    animation_duration: int = 250  # milliseconds
    show_animations: bool = True


@dataclass
class DatabaseSettings:
    """Database settings."""
    db_path: str = "data/tncut.db"
    echo: bool = False  # SQLAlchemy echo mode


@dataclass
class NotificationSettings:
    """Notification settings."""
    enabled: bool = True
    new_device: bool = True
    device_disconnect: bool = True
    high_bandwidth: bool = True
    gateway_unreachable: bool = True
    internet_disconnected: bool = True


@dataclass
class Settings:
    """Main application settings container."""
    network: NetworkSettings = field(default_factory=NetworkSettings)
    ui: UISettings = field(default_factory=UISettings)
    database: DatabaseSettings = field(default_factory=DatabaseSettings)
    notifications: NotificationSettings = field(default_factory=NotificationSettings)


class SettingsManager:
    """Manages application settings persistence and retrieval."""

    def __init__(self, config_dir: Optional[str] = None):
        if config_dir is None:
            config_dir = Path.home() / ".tncut"
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.config_dir / "settings.json"
        self._settings = Settings()
        self.load()

    def load(self) -> Settings:
        """Load settings from file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                for key, value in data.items():
                    if not hasattr(self._settings, key):
                        continue
                    current = getattr(self._settings, key)
                    if isinstance(value, dict) and hasattr(current, '__dataclass_fields__'):
                        for nested_key, nested_value in value.items():
                            if hasattr(current, nested_key):
                                setattr(current, nested_key, nested_value)
                    else:
                        setattr(self._settings, key, value)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load settings from {self.config_file}: {e}")
                print("Using default settings.")
        return self._settings

    def save(self) -> None:
        """Save current settings to file."""
        try:
            data = asdict(self._settings)
            with open(self.config_file, 'w') as f:
                json.dump(data, f, indent=2)
        except IOError as e:
            print(f"Error saving settings to {self.config_file}: {e}")

    def get(self) -> Settings:
        """Get current settings."""
        return self._settings

    def update(self, **kwargs) -> None:
        """Update settings with provided keyword arguments."""
        for key, value in kwargs.items():
            if hasattr(self._settings, key):
                setattr(self._settings, key, value)
                # Handle nested dataclass updates
                if hasattr(getattr(self._settings, key), '__dataclass_fields__'):
                    nested_obj = getattr(self._settings, key)
                    if isinstance(value, dict):
                        for nested_key, nested_value in value.items():
                            if hasattr(nested_obj, nested_key):
                                setattr(nested_obj, nested_key, nested_value)
        self.save()

    def reset_to_defaults(self) -> None:
        """Reset settings to default values."""
        self._settings = Settings()
        self.save()


# Global settings instance
settings_manager = SettingsManager()