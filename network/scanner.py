"""
Network scanner for TNCut application.
Handles device discovery using ARP scanning and other network discovery techniques.
"""

import asyncio
import ipaddress
import logging
import os
import subprocess
import sys
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

def _load_oui_map():
    """Load OUI vendor map from bundled text file."""
    oui_map = {}
    try:
        if getattr(sys, 'frozen', False):
            base = sys._MEIPASS
        else:
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        oui_path = os.path.join(base, 'oui_vendors.txt')
        if not os.path.exists(oui_path):
            with open(os.path.join(os.path.dirname(sys.executable), 'oui_debug.txt'), 'w') as dbg:
                dbg.write(f'frozen={getattr(sys, "frozen", False)}\n')
                dbg.write(f'base={base}\n')
                dbg.write(f'oui_path={oui_path}\n')
                dbg.write(f'exists={os.path.exists(oui_path)}\n')
                dbg.write(f'dir contents={os.listdir(base)[:20]}\n')
            return oui_map
        with open(oui_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    prefix, vendor = line.split('\t', 1)
                    oui_map[prefix] = vendor
    except Exception as e:
        try:
            with open(os.path.join(os.path.dirname(sys.executable), 'oui_debug.txt'), 'w') as dbg:
                dbg.write(f'ERROR: {e}\n')
        except Exception:
            pass
    return oui_map

OUI_MAP = _load_oui_map()

# Debug: write OUI map status on startup
try:
    _dbg_path = os.path.join(os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else '.', 'oui_debug.txt')
    with open(_dbg_path, 'w') as _df:
        _df.write(f"OUI entries: {len(OUI_MAP)}\n")
        _test_mac = '98:ba:5f:a0:20:4d'
        _oui_key = _test_mac.upper().replace('-', ':').replace(':', '')[:6]
        _df.write(f"Test key: {_oui_key}\n")
        _df.write(f"Test result: {OUI_MAP.get(_oui_key, 'NOT FOUND')}\n")
        _df.write(f"Sample keys: {list(OUI_MAP.keys())[:5]}\n")
except:
    pass

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


def get_network_for_ip(local_ip: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Given a specific interface IP, derive (local_ip, network_cidr, gateway_ip).

    Used when the user pins a specific interface instead of auto-detecting.
    """
    if not local_ip:
        return None, None, None
    for name, addrs in psutil.net_if_addrs().items():
        for addr in addrs:
            if addr.family == socket.AF_INET and addr.address == local_ip:
                try:
                    network = ipaddress.IPv4Network(
                        f"{local_ip}/{addr.netmask}", strict=False
                    )
                    gateway_ip = str(network.network_address + 1)
                    return local_ip, str(network), gateway_ip
                except Exception:
                    pass
    # Fallback: assume /24
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
        self._scan_iface: Optional[str] = None

        if SCAPY_AVAILABLE:
            conf.verb = 0

        # Read a user-pinned interface from settings, if any (empty = auto).
        saved_iface = ""
        try:
            from config.settings import settings_manager
            saved_iface = getattr(settings_manager.get().network, 'interface', '') or ""
        except Exception:
            saved_iface = ""

        self._configure_network(saved_iface)

    def _configure_network(self, iface_name: str = "") -> None:
        """
        Resolve the network range, gateway, and scapy interface.

        If iface_name is given, derive everything from that adapter's IP.
        Otherwise auto-detect via the default route.
        """
        if iface_name:
            local_ip = self._ip_for_iface_name(iface_name)
            if local_ip:
                self._local_ip, self._network, self._gateway = get_network_for_ip(local_ip)
                self._scan_iface = iface_name
                logger.info(f"Using pinned interface '{iface_name}': "
                            f"network {self._network} (local IP: {self._local_ip}, gateway: {self._gateway})")
                return
            logger.warning(f"Pinned interface '{iface_name}' not found or has no IPv4; falling back to auto-detect")

        # Auto-detect
        self._local_ip, self._network, self._gateway = get_local_ip_and_network()
        if self._network:
            logger.info(f"Detected network: {self._network} (local IP: {self._local_ip}, gateway: {self._gateway})")
        else:
            logger.warning("Could not auto-detect network")

        # Match the scapy interface whose IP equals our local IP, so ARP
        # packets go out the correct adapter instead of scapy's default.
        self._scan_iface = self._resolve_scan_iface()
        if self._scan_iface:
            logger.info(f"Using scan interface: {self._scan_iface}")
        else:
            logger.warning("Could not match a scapy interface to the local IP; using default")

    def _resolve_scan_iface(self) -> Optional[str]:
        """Find the scapy interface name whose IPv4 address matches our local IP."""
        if not SCAPY_AVAILABLE or not self._local_ip:
            return None
        try:
            from scapy.all import get_working_ifaces
            for iface in get_working_ifaces():
                if getattr(iface, "ip", None) == self._local_ip:
                    return iface.name
        except Exception as e:
            logger.warning(f"Failed to resolve scan interface: {e}")
        return None

    def _ip_for_iface_name(self, iface_name: str) -> Optional[str]:
        """Return the IPv4 address of the scapy interface with the given name."""
        if not SCAPY_AVAILABLE:
            return None
        try:
            from scapy.all import get_working_ifaces
            for iface in get_working_ifaces():
                if iface.name == iface_name:
                    ip = getattr(iface, "ip", None)
                    if ip and ip != "0.0.0.0":
                        return ip
        except Exception as e:
            logger.warning(f"Failed to look up IP for interface '{iface_name}': {e}")
        return None

    def list_interfaces(self) -> List[Dict[str, str]]:
        """
        List selectable network interfaces for the settings UI.

        Returns a list of {'name': ..., 'ip': ...} for adapters that have an IPv4.
        """
        result: List[Dict[str, str]] = []
        if not SCAPY_AVAILABLE:
            return result
        try:
            from scapy.all import get_working_ifaces
            for iface in get_working_ifaces():
                ip = getattr(iface, "ip", None)
                if ip and ip != "0.0.0.0":
                    result.append({'name': iface.name, 'ip': ip})
        except Exception as e:
            logger.warning(f"Failed to list interfaces: {e}")
        return result

    def set_interface(self, iface_name: str = "") -> None:
        """Re-configure the scanner to use a specific interface ('' = auto-detect)."""
        self._configure_network(iface_name)
        # The ARP spoofer caches gateway IP/MAC/interface derived from the old
        # network, so it must re-resolve them against the new interface.
        try:
            from network.arp_spoof import arp_spoofer
            arp_spoofer.reset_gateway_info()
        except Exception as e:
            logger.warning(f"Could not reset ARP spoofer after interface change: {e}")

    @property
    def local_ip(self) -> str:
        return self._local_ip or "Unknown"

    @property
    def gateway(self) -> str:
        return self._gateway or "Unknown"

    @property
    def scan_iface(self) -> Optional[str]:
        """The resolved scapy interface name used for scanning/spoofing (None = default)."""
        return self._scan_iface

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

            if self._scan_iface:
                result = srp(packet, timeout=3, verbose=0, iface=self._scan_iface)[0]
            else:
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
            socket.setdefaulttimeout(2)
            hostname = socket.gethostbyaddr(ip)[0]
            if hostname and hostname != ip:
                return hostname
        except (socket.herror, socket.gaierror, socket.timeout, OSError):
            pass
        finally:
            socket.setdefaulttimeout(None)
        return ""

    def _get_vendor_from_mac(self, mac: str) -> str:
        first_byte = int(mac.split(':')[0].replace('-', ''), 16)
        if first_byte & 0x02:
            return 'Randomized MAC'
        if OUI_MAP:
            oui = mac.upper().replace('-', ':').replace(':', '')[:6]
            vendor = OUI_MAP.get(oui, '')
            if vendor:
                short_names = {
                    'TP-Link Systems Inc.': 'TP-Link',
                    'Hangzhou Hikvision Digital Technology Co.,Ltd.': 'Hikvision',
                    'GUANGDONG OPPO MOBILE TELECOMMUNICATIONS CORP.,LTD': 'OPPO',
                    'Xiaomi Communications Co Ltd': 'Xiaomi',
                    'Samsung Electronics Co.,Ltd': 'Samsung',
                    'Apple, Inc.': 'Apple',
                    'Huawei Technologies Co.,Ltd': 'Huawei',
                    'Intel Corporate': 'Intel',
                    'Realtek Semiconductor Corp.': 'Realtek',
                    'ASUSTek COMPUTER INC.': 'ASUS',
                    'HONOR Device Co., Ltd.': 'HONOR',
                    'Dell Inc.': 'Dell',
                    'Hewlett Packard': 'HP',
                    'Microsoft Corporation': 'Microsoft',
                    'Google, Inc.': 'Google',
                    'Amazon Technologies Inc.': 'Amazon',
                    'Sony Interactive Entertainment Inc.': 'Sony/PlayStation',
                    'Microsoft Xbox': 'Xbox',
                    'VMware, Inc.': 'VMware',
                    'Raspberry Pi': 'Raspberry Pi',
                }
                for long, short in short_names.items():
                    if long.lower() in vendor.lower():
                        return short
                return vendor.split(' ')[0] if len(vendor) > 30 else vendor
        return 'Unknown'

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

        if any(x in vendor_lower for x in ['oppo', 'xiaomi', 'samsung', 'huawei', 'honor', 'oneplus', 'vivo', 'realme']):
            return 'Phone'
        elif 'apple' in vendor_lower:
            return 'Apple Device'
        elif 'tp-link' in vendor_lower or 'netgear' in vendor_lower or 'cisco' in vendor_lower or 'ubiquiti' in vendor_lower:
            return 'Router'
        elif 'hikvision' in vendor_lower or 'dahua' in vendor_lower:
            return 'Camera'
        elif 'sony/playstation' in vendor_lower or 'xbox' in vendor_lower or 'nintendo' in vendor_lower:
            return 'Gaming Console'
        elif 'vmware' in vendor_lower or 'virtual' in vendor_lower:
            return 'Virtual Machine'
        elif 'raspberry' in vendor_lower:
            return 'SBC'
        elif 'amazon' in vendor_lower or 'google' in vendor_lower:
            return 'Smart Device'
        elif vendor_lower == 'randomized mac':
            return 'Phone'

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
