"""
Network service for TNCut application.
Handles periodic network scanning and device management.
"""

import asyncio
import threading
from typing import List, Dict, Callable, Optional, Set
from datetime import datetime
import logging

from network.scanner import network_scanner
from models import Device, DeviceHistory
from utils.logger import get_logger

logger = get_logger(__name__)


class NetworkService:
    """Service for managing network discovery and device tracking."""

    def __init__(self):
        self.is_running = False
        self.scan_thread: Optional[threading.Thread] = None
        self.scan_interval = 30  # seconds
        self.devices: List[Device] = []
        self.update_callbacks: List[Callable] = []
        self._known_ips: Set[str] = set()
        self._mac_to_ip: Dict[str, str] = {}

        # Set up scanner callback
        network_scanner.set_scan_callback(self._on_devices_discovered)

    def add_update_callback(self, callback: Callable[[List[Device]], None]):
        self.update_callbacks.append(callback)

    def remove_update_callback(self, callback: Callable[[List[Device]], None]):
        if callback in self.update_callbacks:
            self.update_callbacks.remove(callback)

    def start(self, scan_interval: int = 30):
        if self.is_running:
            logger.warning("Network service is already running")
            return

        self.scan_interval = scan_interval
        self.is_running = True

        self.scan_thread = threading.Thread(target=self._run_scanner, daemon=True)
        self.scan_thread.start()

        logger.info(f"Network service started with {scan_interval}s scan interval")

    def stop(self):
        if not self.is_running:
            return

        self.is_running = False
        network_scanner.stop_scan()

        if self.scan_thread and self.scan_thread.is_alive():
            self.scan_thread.join(timeout=5)

        logger.info("Network service stopped")

    def scan_now(self) -> List[Device]:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                future = asyncio.run_coroutine_threadsafe(
                    network_scanner.scan_network(), loop
                )
                devices = future.result(timeout=10)
            else:
                devices = asyncio.run(network_scanner.scan_network())
        except RuntimeError:
            devices = asyncio.run(network_scanner.scan_network())

        self._on_devices_discovered(devices)
        return devices

    def _run_scanner(self):
        while self.is_running:
            try:
                devices = asyncio.run(network_scanner.scan_network())
                self._on_devices_discovered(devices)

                for _ in range(self.scan_interval):
                    if not self.is_running:
                        break
                    for _ in range(10):
                        if not self.is_running:
                            break
                        threading.Event().wait(1)
            except Exception as e:
                logger.error(f"Error in network scanner loop: {e}")
                for _ in range(5):
                    if not self.is_running:
                        break
                    threading.Event().wait(1)

    def _upsert_device(self, device_data: dict):
        """Insert or update a device row in the database from scan data.

        Preserves user-owned fields (notes, first_seen) on updates.
        """
        try:
            from database.session import get_db_session
            from models.models import Device as DeviceModel

            ip = device_data['ip']
            with get_db_session() as session:
                db_device = session.query(DeviceModel).filter_by(
                    ip_address=ip
                ).first()
                if db_device is None:
                    db_device = DeviceModel(
                        ip_address=ip,
                        first_seen=device_data.get(
                            'first_seen', device_data['last_seen']),
                    )
                    session.add(db_device)

                db_device.mac_address = device_data.get('mac', '') or db_device.mac_address
                db_device.hostname = device_data.get('hostname')
                db_device.vendor = device_data.get('vendor')
                db_device.device_type = device_data.get('device_type')
                db_device.is_online = True
                db_device.response_time = device_data.get('response_time', 0)
                db_device.last_seen = device_data['last_seen']
                # notes are intentionally left untouched here
        except Exception as e:
            logger.error(f"Could not upsert device {device_data.get('ip')}: {e}")

    def _record_history_event(self, device_ip: str, event_type: str,
                              description: str, old_value: str = None,
                              new_value: str = None):
        """Record a device event to the history database."""
        try:
            from database.session import get_db_session
            from models.models import Device as DeviceModel

            with get_db_session() as session:
                db_device = session.query(DeviceModel).filter_by(
                    ip_address=device_ip
                ).first()
                if db_device:
                    history = DeviceHistory(
                        device_id=db_device.id,
                        event_type=event_type,
                        description=description,
                        old_value=old_value,
                        new_value=new_value,
                    )
                    session.add(history)
        except Exception as e:
            logger.debug(f"Could not record history event: {e}")

    def _on_devices_discovered(self, devices_data: List[dict]):
        try:
            current_ips = set()
            new_devices = []

            for device_data in devices_data:
                ip = device_data['ip']
                mac = device_data.get('mac', '')
                current_ips.add(ip)

                device = Device(
                    ip_address=ip,
                    mac_address=mac,
                    hostname=device_data['hostname'],
                    vendor=device_data['vendor'],
                    device_type=device_data['device_type'],
                    is_online=True,
                    response_time=device_data.get('response_time', 0),
                    last_seen=device_data['last_seen'],
                    first_seen=device_data.get('first_seen', device_data['last_seen'])
                )
                new_devices.append(device)

                # Persist/refresh the device row so notes, history, and traffic
                # logs have a real DB record to attach to.
                self._upsert_device(device_data)

                # Record "joined" event for new devices
                if ip not in self._known_ips:
                    hostname = device_data.get('hostname', '')
                    self._record_history_event(
                        ip, "joined",
                        f"Device {hostname or ip} joined the network"
                    )

                # Record "ip_changed" if MAC had a different IP before
                if mac and mac in self._mac_to_ip and self._mac_to_ip[mac] != ip:
                    self._record_history_event(
                        ip, "ip_changed",
                        f"Device MAC {mac} changed IP",
                        old_value=self._mac_to_ip[mac],
                        new_value=ip
                    )

                if mac:
                    self._mac_to_ip[mac] = ip

            # Record "left" events for devices that disappeared
            departed = self._known_ips - current_ips
            for ip in departed:
                self._record_history_event(
                    ip, "left",
                    f"Device {ip} left the network"
                )

            self._known_ips = current_ips
            self.devices = new_devices
            logger.debug(f"Updated device list: {len(self.devices)} devices")

            for callback in self.update_callbacks:
                try:
                    callback(self.devices)
                except Exception as e:
                    logger.error(f"Error in device update callback: {e}")

        except Exception as e:
            logger.error(f"Error processing discovered devices: {e}")

    def get_devices(self) -> List[Device]:
        return self.devices.copy()

    def get_device_by_ip(self, ip: str) -> Optional[Device]:
        for device in self.devices:
            if device.ip_address == ip:
                return device
        return None

    def get_device_by_mac(self, mac: str) -> Optional[Device]:
        for device in self.devices:
            if device.mac_address and device.mac_address.lower() == mac.lower():
                return device
        return None


# Global network service instance
network_service = NetworkService()
