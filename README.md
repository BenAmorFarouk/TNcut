<p align="center">
  <img src="logo.png" alt="TNcut Logo" width="140">
</p>

<h1 align="center">TNcut</h1>

<p align="center">
  <strong>Network monitoring and per-device bandwidth control for Windows</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/platform-Windows%2010%20%7C%2011-0078D6?logo=windows&logoColor=white" alt="Platform">
  <img src="https://img.shields.io/badge/python-3.12%2B-3776AB?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/GUI-PySide6%20(Qt%206)-41CD52?logo=qt&logoColor=white" alt="PySide6">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
  <img src="https://img.shields.io/github/v/release/BenAmorFarouk/TNcut?display_name=tag" alt="Release">
</p>

<p align="center">
  <a href="#download">Download</a> &bull;
  <a href="#features">Features</a> &bull;
  <a href="#installation">Installation</a> &bull;
  <a href="#usage">Usage</a> &bull;
  <a href="#how-it-works">How It Works</a> &bull;
  <a href="#build-from-source">Build</a> &bull;
  <a href="#license">License</a>
</p>

---

## Overview

TNcut is a Windows desktop application for monitoring your local network and controlling individual devices' internet access. It discovers every device on your subnet, reports real-time traffic and latency, and lets you throttle or cut any device's bandwidth using ARP-based network control — a modern, open-source take on tools like NetCut.

Built with a clean PySide6 (Qt 6) interface, TNcut ships as a single installer and runs entirely on your machine. No accounts, no cloud, no telemetry.

## Download

Grab the latest signed installer from the [**Releases**](https://github.com/BenAmorFarouk/TNcut/releases/latest) page:

1. Download `TNcut_Setup_x.x.x.exe`
2. Run the installer (Administrator privileges required)
3. Install [Npcap](https://npcap.com/) if you don't already have it — TNcut needs it for raw packet capture

> Prefer to build it yourself? See [Build from source](#build-from-source).

## Features

- **Automatic Device Discovery** — ARP-based subnet scanning with hostname and vendor (OUI) resolution
- **Live Latency** — On-demand ping with min/max/avg statistics per device
- **Internet Speed Monitor** — Real-time upload/download readouts and traffic charts on the dashboard
- **Per-Device Bandwidth Control** — For any device on the network:
  - Cut its internet access entirely
  - Apply a speed limit (KB/s or Mbps) with quick presets
  - Restore full connectivity instantly
- **At-a-Glance Status** — `CUT` (red) and throttle values (orange) surfaced directly in the device table
- **Dark & Light Themes** — Windows 11-style interface with one-click theme switching
- **Persistent Configuration** — Settings stored locally as JSON in `~/.tncut/`
- **Device History & Logs** — SQLite-backed activity tracking over time

## Tech Stack

| Component   | Technology              |
|-------------|-------------------------|
| Language    | Python 3.12+            |
| GUI         | PySide6 (Qt 6)          |
| Networking  | Scapy, psutil           |
| Database    | SQLite via SQLAlchemy   |
| Packaging   | PyInstaller + NSIS      |

## Installation

### Prerequisites

- Windows 10 or 11
- [Npcap](https://npcap.com/) — required by Scapy for raw packet capture
- Python 3.12+ *(source install only)*

### From source

```bash
git clone https://github.com/BenAmorFarouk/TNcut.git
cd TNcut
pip install -r requirements.txt
python main.py
```

> **Administrator required.** Network scanning and ARP operations need elevated privileges. Launch your terminal (or the app) as Administrator.

## Usage

1. **Launch as Administrator** — required for scanning and bandwidth control.
2. **Dashboard** — device count, network status, and live speed charts at a glance.
3. **Devices** — every discovered device with IP, MAC, hostname, vendor, ping, and limit status.
4. **Right-click a device** to:
   - **Ping** — run a 4-packet test with min/max/avg latency
   - **Limit Speed** — set bandwidth (0–100,000 KB/s or Mbps) with presets (128 KB/s, 256 KB/s, 512 KB/s, 1 Mbps, 5 Mbps)
   - **Cut Internet** — block all traffic immediately
   - **Restore Internet** — clear any active limit
5. **Settings** — scan intervals, bandwidth baseline, theme, and notifications.

## How It Works

TNcut controls per-device bandwidth through **ARP spoofing**:

| Mode        | Mechanism                                                                                   |
|-------------|---------------------------------------------------------------------------------------------|
| **Cut**     | Poisons both the target and the gateway so traffic routes through the host machine, where it is dropped. Sends ARP requests and replies so devices reliably cache the spoof. |
| **Limit**   | Duty-cycle throttling — alternates between spoofing (block) and restoring (allow) the target's ARP entry at a ratio proportional to the desired speed limit. |
| **Restore** | Sends corrected ARP replies with the real gateway MAC to repair the target's ARP table.     |

A static ARP entry is pinned on the host to prevent self-poisoning from Npcap packet loopback.

> **Note:** ARP spoofing directly manipulates layer-2 addressing on the local network. Use responsibly — see the [Disclaimer](#disclaimer).

## Build from Source

TNcut is packaged with PyInstaller. Build the standalone executable:

```bash
python -m PyInstaller TNCut.spec --noconfirm
```

Output: `dist/TNCut/TNCut.exe`

The Windows installer is built from `installer.nsi` with [NSIS](https://nsis.sourceforge.io/):

```bash
makensis installer.nsi
```

## Project Structure

```
TNcut/
├── main.py                     # Entry point
├── config/
│   └── settings.py             # Settings dataclasses + JSON persistence
├── network/
│   ├── scanner.py              # ARP-based network scanner + ping
│   └── arp_spoof.py            # Per-device ARP spoofing engine
├── services/
│   └── network_service.py      # Background scan service
├── models/
│   ├── models.py               # Data models
│   └── device_table_model.py   # Qt table model
├── ui/                         # PySide6 views (dashboard, devices, settings, ...)
├── widgets/
│   └── chart_widget.py         # Traffic chart widgets
├── database/
│   └── session.py              # SQLAlchemy session
├── utils/                      # Logger + theming
├── installer.nsi               # NSIS installer script
├── TNCut.spec                  # PyInstaller build spec
├── logo.png
└── requirements.txt
```

## Disclaimer

TNcut is intended for **authorized network administration and educational use only**. ARP spoofing can disrupt network connectivity. Only use TNcut on networks you own or have explicit permission to manage. Unauthorized use may violate local laws.

## License

Released under the [MIT License](LICENSE.txt). © BenAmorFarouk
