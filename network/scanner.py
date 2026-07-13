"""
Network scanner for TNCut application.
Handles device discovery using ARP scanning and other network discovery techniques.
"""

import asyncio
import ipaddress
import logging
import subprocess
import time
from typing import List, Dict, Optional, Callable, Tuple
from datetime import datetime
import socket
import platform

import psutil

try:
    from scapy.all import ARP, Ether, srp, conf
    SCAPY_AVAILABLE = True
except ImportError:
    SCAPY_AVAILABLE = False

from models import Device
from utils.logger import get_logger

logger = get_logger(__name__)

logging.getLogger("scapy.runtime").setLevel(logging.WARNING)


def get_local_ip_and_network() -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Detect local IP, subnet, and gateway using psutil + socket.

    Returns:
        (local_ip, network_cidr, gateway_ip) — any may be None
    """
    local_ip = None
    gateway_ip = None

    # Find the local IP by connecting to an external address (no traffic sent)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        pass

    if not local_ip:
        return None, None, None

    # Find the matching interface to get the netmask
    for name, addrs in psutil.net_if_addrs().items():
        for addr in addrs:
            if addr.family == socket.AF_INET and addr.address == local_ip:
                try:
                    network = ipaddress.IPv4Network(
                        f"{local_ip}/{addr.netmask}", strict=False
                    )
                    # Try to find gateway from psutil
                    gateways = psutil.net_if_stats()
                    # Gateway is typically .1 on the network
                    gateway_ip = str(network.network_address + 1)
                    return local_ip, str(network), gateway_ip
                except Exception:
                    pass

    # Fallback: use /24
    try:
        network = ipaddress.IPv4Network(f"{local_ip}/24", strict=False)
        gateway_ip = str(network.network_address + 1)
        return local_ip, str(network), gateway_ip
    except Exception:
        return local_ip, None, None


class NetworkScanner:
    """Network scanner for discovering devices on the local network."""

    def __init__(self):
        self.devices: Dict[str, Device] = {}
        self.is_scanning = False
        self.scan_callback: Optional[Callable] = None
        self._local_ip: Optional[str] = None
        self._network: Optional[str] = None
        self._gateway: Optional[str] = None

        if SCAPY_AVAILABLE:
            conf.verb = 0

        # Detect network on init
        self._local_ip, self._network, self._gateway = get_local_ip_and_network()
        if self._network:
            logger.info(f"Detected network: {self._network} (local IP: {self._local_ip}, gateway: {self._gateway})")
        else:
            logger.warning("Could not auto-detect network")

    @property
    def local_ip(self) -> str:
        return self._local_ip or "Unknown"

    @property
    def gateway(self) -> str:
        return self._gateway or "Unknown"

    def ping_host(self, ip: str, count: int = 1, timeout: int = 2) -> Optional[float]:
        """Ping a host and return average response time in ms, or None if unreachable."""
        try:
            param = "-n" if platform.system().lower() == "windows" else "-c"
            timeout_param = "-w" if platform.system().lower() == "windows" else "-W"
            timeout_val = str(timeout * 1000) if platform.system().lower() == "windows" else str(timeout)
            cmd = ["ping", param, str(count), timeout_param, timeout_val, ip]
            start = time.perf_counter()
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout + 2,
                creationflags=subprocess.CREATE_NO_WINDOW if platform.system().lower() == "windows" else 0
            )
            elapsed = (time.perf_counter() - start) * 1000

            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    line_lower = line.lower()
                    if "average" in line_lower or "avg" in line_lower:
                        import re
                        match = re.search(r'(\d+(?:\.\d+)?)\s*ms', line)
                        if match:
                            return float(match.group(1))
                    if "time=" in line_lower or "time<" in line_lower:
                        import re
                        match = re.search(r'time[=<](\d+(?:\.\d+)?)', line_lower)
                        if match:
                            return float(match.group(1))
                return round(elapsed, 1)
            return None
        except Exception:
            return None

    def set_scan_callback(self, callback: Callable[[List[Dict]], None]):
        self.scan_callback = callback

    def get_local_network(self) -> Optional[str]:
        return self._network

    async def scan_network(self, network_range: Optional[str] = None) -> List[Dict]:
        if self.is_scanning:
            logger.warning("Scan already in progress")
            return []

        if not SCAPY_AVAILABLE:
            logger.error("Scapy not available for network scanning")
            return []

        self.is_scanning = True

        try:
            if network_range is None:
                network_range = self.get_local_network()
                if network_range is None:
                    logger.error("Cannot determine network range")
                    return []

            logger.info(f"Starting network scan on {network_range}")

            arp = ARP(pdst=network_range)
            ether = Ether(dst="ff:ff:ff:ff:ff:ff")
            packet = ether / arp

            result = srp(packet, timeout=3, verbose=0)[0]

            devices = []
            for sent, received in result:
                ip = received.psrc
                mac = received.hwsrc

                hostname = await self._get_hostname(ip)
                vendor = self._get_vendor_from_mac(mac)
                device_type = self._guess_device_type(hostname, vendor, mac)
                response_time = self.ping_host(ip) or 0

                device = Device(
                    ip_address=ip,
                    mac_address=mac,
                    hostname=hostname,
                    vendor=vendor,
                    device_type=device_type,
                    is_online=True,
                    response_time=response_time,
                    last_seen=datetime.now(),
                    first_seen=datetime.now()
                )

                devices.append({
                    'ip': ip,
                    'mac': mac,
                    'hostname': hostname,
                    'vendor': vendor,
                    'device_type': device_type,
                    'status': 'Online',
                    'response_time': response_time,
                    'last_seen': device.last_seen,
                    'first_seen': device.first_seen
                })

                self.devices[ip] = device

            logger.info(f"Network scan completed. Found {len(devices)} devices.")

            if self.scan_callback:
                self.scan_callback(devices)

            return devices

        except Exception as e:
            logger.error(f"Error during network scan: {e}")
            return []
        finally:
            self.is_scanning = False

    async def _get_hostname(self, ip: str) -> str:
        try:
            hostname = socket.gethostbyaddr(ip)[0]
            return hostname
        except (socket.herror, socket.gaierror):
            return ""

    def _get_vendor_from_mac(self, mac: str) -> str:
        oui = mac.upper().replace('-', ':').split(':')[0:3]

        oui_map = {
            '00:50:56': 'VMware',
            '00:0C:29': 'VMware',
            '00:1C:14': 'VMware',
            '00:05:69': 'VMware',
            '00:1C:42': 'VMware',
            '00:16:3E': 'Xen',
            '00:18:00': 'HP',
            '00:1B:21': 'Intel',
            '00:1F:16': 'Intel',
            '00:21:5A': 'Apple',
            '00:23:6C': 'Apple',
            '00:25:00': 'Apple',
            '00:26:08': 'Apple',
            '00:26:BB': 'Apple',
            '00:17:F2': 'Apple',
            '00:1B:63': 'Apple',
            '00:1F:F3': 'Apple',
            '00:22:41': 'Apple',
            '00:23:12': 'Apple',
            '00:23:32': 'Apple',
            '00:23:76': 'Apple',
            '00:25:4B': 'Apple',
            '00:25:BC': 'Apple',
            '00:26:4A': 'Apple',
            '00:26:B0': 'Apple',
        }

        return oui_map.get(':'.join(oui), 'Unknown')

    def _guess_device_type(self, hostname: str, vendor: str, mac: str) -> str:
        hostname_lower = hostname.lower()
        vendor_lower = vendor.lower()

        if any(x in hostname_lower for x in ['phone', 'iphone', 'android', 'mobile']):
            return 'Phone'
        elif any(x in hostname_lower for x in ['laptop', 'notebook', 'thinkpad', 'macbook']):
            return 'Laptop'
        elif any(x in hostname_lower for x in ['desktop', 'pc', 'workstation']):
            return 'PC'
        elif any(x in hostname_lower for x in ['server', 'srv']):
            return 'Server'
        elif any(x in hostname_lower for x in ['router', 'gateway', 'ap', 'access']):
            return 'Router'
        elif any(x in hostname_lower for x in ['printer', 'print']):
            return 'Printer'
        elif any(x in hostname_lower for x in ['tv', 'television']):
            return 'Smart TV'
        elif any(x in hostname_lower for x in ['camera', 'cam']):
            return 'Camera'

        if 'apple' in vendor_lower:
            return 'Apple Device'
        elif 'samsung' in vendor_lower:
            return 'Samsung Device'
        elif 'vmware' in vendor_lower or 'virtual' in vendor_lower:
            return 'Virtual Machine'

        return 'Unknown'

    def stop_scan(self):
        self.is_scanning = False
        logger.info("Network scan stopped")

    def get_discovered_devices(self) -> List[Device]:
        return list(self.devices.values())

    def clear_devices(self):
        self.devices.clear()
        logger.info("Device list cleared")


# Global scanner instance
network_scanner = NetworkScanner()
