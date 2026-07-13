"""
ARP spoofer for per-device bandwidth limiting.
Uses ARP spoofing to control individual devices' internet access.
"""

import threading
import time
import subprocess
from dataclasses import dataclass, field
from typing import Dict, Optional

from utils.logger import get_logger

logger = get_logger(__name__)

try:
    from scapy.all import ARP, Ether, sendp, srp, conf, get_if_hwaddr
    SCAPY_AVAILABLE = True
except ImportError:
    SCAPY_AVAILABLE = False

@dataclass
class TargetInfo:
    ip: str
    mac: str
    limit_kbps: int  # 0=cut, >0=throttle in KB/s
    thread: Optional[threading.Thread] = None
    active: bool = False


class ARPSpoofer:
    """Manages per-device ARP spoofing for bandwidth limiting."""

    def __init__(self):
        self._targets: Dict[str, TargetInfo] = {}
        self._gateway_ip: Optional[str] = None
        self._gateway_mac: Optional[str] = None
        self._local_mac: Optional[str] = None
        self._iface_index: Optional[int] = None
        self._lock = threading.Lock()
        self._static_arp_set = False

    def _ensure_gateway_info(self):
        """Resolve gateway IP and MAC address."""
        if self._gateway_mac and self._gateway_ip:
            return True

        from network.scanner import network_scanner
        self._gateway_ip = network_scanner.gateway
        if not self._gateway_ip or self._gateway_ip == "Unknown":
            logger.error("Cannot determine gateway IP")
            return False

        try:
            self._local_mac = get_if_hwaddr(conf.iface)
        except Exception:
            self._local_mac = "00:00:00:00:00:00"

        self._gateway_mac = self._resolve_mac(self._gateway_ip)
        if not self._gateway_mac:
            logger.error(f"Cannot resolve gateway MAC for {self._gateway_ip}")
            return False

        self._iface_index = self._get_gateway_interface_index()

        logger.info(f"Gateway: {self._gateway_ip} ({self._gateway_mac}), "
                     f"Local MAC: {self._local_mac}, Interface idx: {self._iface_index}")
        return True

    def _get_gateway_interface_index(self) -> Optional[int]:
        """Get the Windows interface index for the interface that reaches the gateway."""
        try:
            result = subprocess.run(
                ["arp", "-a"],
                capture_output=True, text=True, timeout=5,
                creationflags=0x08000000
            )
            current_idx = None
            for line in result.stdout.split('\n'):
                if 'Interface:' in line and '---' in line:
                    hex_part = line.split('---')[-1].strip()
                    try:
                        current_idx = int(hex_part, 16)
                    except ValueError:
                        current_idx = None
                elif self._gateway_ip and self._gateway_ip in line and current_idx is not None:
                    logger.info(f"Found gateway on interface index {current_idx}")
                    return current_idx
        except Exception as e:
            logger.warning(f"Could not determine interface index: {e}")
        return None

    def _set_static_gateway_arp(self):
        """Pin a static ARP entry for the gateway so spoofs don't poison our own cache."""
        if self._static_arp_set or not self._gateway_ip or not self._gateway_mac:
            return
        if self._iface_index is None:
            logger.warning("No interface index — cannot set static ARP")
            return
        mac_dashes = self._gateway_mac.replace(":", "-")
        idx = str(self._iface_index)
        try:
            subprocess.run(
                ["netsh", "interface", "ipv4", "delete", "neighbors",
                 idx, self._gateway_ip],
                capture_output=True, timeout=5,
                creationflags=0x08000000
            )
            result = subprocess.run(
                ["netsh", "interface", "ipv4", "add", "neighbors",
                 idx, self._gateway_ip, mac_dashes],
                capture_output=True, text=True, timeout=5,
                creationflags=0x08000000
            )
            if result.returncode == 0:
                self._static_arp_set = True
                logger.info(f"Static ARP set for gateway {self._gateway_ip} -> {mac_dashes} on iface {idx}")
            else:
                logger.warning(f"netsh add neighbors failed: {result.stderr.strip()}")
        except Exception as e:
            logger.warning(f"Could not set static ARP for gateway: {e}")

    def _remove_static_gateway_arp(self):
        """Remove our static ARP entry for the gateway."""
        if not self._static_arp_set or not self._gateway_ip or self._iface_index is None:
            return
        idx = str(self._iface_index)
        try:
            subprocess.run(
                ["netsh", "interface", "ipv4", "delete", "neighbors",
                 idx, self._gateway_ip],
                capture_output=True, timeout=5,
                creationflags=0x08000000
            )
            self._static_arp_set = False
            logger.info(f"Static ARP removed for gateway {self._gateway_ip}")
        except Exception as e:
            logger.warning(f"Could not remove static ARP: {e}")

    def _resolve_mac(self, ip: str) -> Optional[str]:
        """Resolve an IP address to its MAC address using ARP."""
        if not SCAPY_AVAILABLE:
            return None
        try:
            pkt = Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=ip)
            result = srp(pkt, timeout=3, verbose=0)[0]
            if result:
                return result[0][1].hwsrc
        except Exception as e:
            logger.error(f"Failed to resolve MAC for {ip}: {e}")
        return None

    def _spoof_target(self, target_ip: str, target_mac: str):
        """Send ARP reply telling target that the gateway is at our MAC."""
        if not SCAPY_AVAILABLE:
            return
        pkt = Ether(dst=target_mac) / ARP(
            op=2,
            pdst=target_ip,
            hwdst=target_mac,
            psrc=self._gateway_ip
        )
        sendp(pkt, verbose=0)

    def _restore_target(self, target_ip: str, target_mac: str):
        """Send correct ARP reply to restore the target's gateway entry."""
        if not SCAPY_AVAILABLE or not self._gateway_mac:
            return
        pkt = Ether(dst=target_mac) / ARP(
            op=2,
            pdst=target_ip,
            hwdst=target_mac,
            psrc=self._gateway_ip,
            hwsrc=self._gateway_mac
        )
        for _ in range(3):
            sendp(pkt, verbose=0)
            time.sleep(0.2)

    def _spoof_loop(self, target_ip: str):
        """Background thread loop for continuous ARP spoofing."""
        with self._lock:
            target = self._targets.get(target_ip)
            if not target:
                return

        logger.info(f"Starting ARP spoof for {target_ip} (limit: {target.limit_kbps} KB/s)")

        from config.settings import settings_manager
        max_kbps = getattr(settings_manager.get().network, 'bandwidth_limit', 100) * 1000

        while True:
            with self._lock:
                target = self._targets.get(target_ip)
                if not target or not target.active:
                    break
                limit_kbps = target.limit_kbps
                mac = target.mac

            if limit_kbps == 0:
                self._spoof_target(target_ip, mac)
                time.sleep(0.5)
            else:
                if max_kbps > 0:
                    allow_ratio = min(1.0, limit_kbps / max_kbps)
                else:
                    allow_ratio = 0.5

                cycle_time = 1.0
                allow_time = cycle_time * allow_ratio
                block_time = cycle_time - allow_time

                # Allow phase: restore real gateway MAC so traffic flows normally
                self._restore_target(target_ip, mac)
                elapsed = 0.0
                while elapsed < allow_time:
                    with self._lock:
                        t = self._targets.get(target_ip)
                        if not t or not t.active:
                            return
                    time.sleep(min(0.1, allow_time - elapsed))
                    elapsed += 0.1

                # Block phase: spoof with fake MAC so traffic goes nowhere
                if block_time > 0.05:
                    self._spoof_target(target_ip, mac)
                    elapsed = 0.0
                    while elapsed < block_time:
                        with self._lock:
                            t = self._targets.get(target_ip)
                            if not t or not t.active:
                                return
                        time.sleep(min(0.1, block_time - elapsed))
                        elapsed += 0.1

        with self._lock:
            target = self._targets.get(target_ip)
            if target:
                self._restore_target(target_ip, target.mac)

        logger.info(f"Stopped ARP spoof for {target_ip}")

    def set_limit(self, ip: str, mac: str, limit_kbps: int) -> bool:
        """
        Set bandwidth limit for a device.

        Args:
            ip: Target device IP
            mac: Target device MAC
            limit_kbps: Speed limit in KB/s. 0=cut internet completely.
        """
        if not SCAPY_AVAILABLE:
            logger.error("Scapy not available")
            return False

        if not self._ensure_gateway_info():
            return False

        self._set_static_gateway_arp()

        self._stop_target(ip)

        with self._lock:
            target = TargetInfo(ip=ip, mac=mac, limit_kbps=limit_kbps, active=True)
            self._targets[ip] = target

        thread = threading.Thread(target=self._spoof_loop, args=(ip,), daemon=True)
        with self._lock:
            self._targets[ip].thread = thread
        thread.start()

        logger.info(f"Set limit for {ip}: {limit_kbps} KB/s")
        return True

    def _stop_target(self, ip: str):
        """Stop spoofing a specific target."""
        with self._lock:
            target = self._targets.get(ip)
            if target:
                target.active = False

        if target and target.thread and target.thread.is_alive():
            target.thread.join(timeout=3)

    def restore(self, ip: str):
        """Restore normal connectivity for a device."""
        self._stop_target(ip)
        with self._lock:
            target = self._targets.pop(ip, None)
        if target:
            self._restore_target(ip, target.mac)
            logger.info(f"Restored {ip}")

    def restore_all(self):
        """Restore all spoofed devices. Call on app exit."""
        with self._lock:
            ips = list(self._targets.keys())

        for ip in ips:
            self.restore(ip)

        self._remove_static_gateway_arp()
        logger.info("All devices restored")

    def get_limit(self, ip: str) -> Optional[int]:
        """Get current limit in KB/s for a device, or None if not limited."""
        with self._lock:
            target = self._targets.get(ip)
            if target and target.active:
                return target.limit_kbps
        return None

    def is_limited(self, ip: str) -> bool:
        """Check if a device is currently being limited."""
        return self.get_limit(ip) is not None

    def get_all_limits(self) -> Dict[str, int]:
        """Get all active limits as {ip: kbps}."""
        with self._lock:
            return {ip: t.limit_kbps for ip, t in self._targets.items() if t.active}


# Global instance
arp_spoofer = ARPSpoofer()
