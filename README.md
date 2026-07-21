<p align="center">
  <img src="logo.png" alt="TNcut Logo" width="160">
</p>

<h1 align="center">TNcut</h1>

<p align="center">
  <strong>Network monitoring and per-device bandwidth control tool for Windows</strong>
</p>

<p align="center">
  <a href="#features">Features</a> &bull;
  <a href="#installation">Installation</a> &bull;
  <a href="#usage">Usage</a> &bull;
  <a href="#build">Build</a> &bull;
  <a href="#license">License</a>
</p>

---

## About

TNcut is a Windows desktop application for monitoring your local network and controlling individual devices' internet access. It discovers all devices on your subnet, displays real-time traffic statistics, and lets you limit or cut any device's bandwidth through ARP-based network control — similar to NetCut.

## Features

- **Device Discovery** — Automatic ARP-based scanning of your local network with hostname resolution
- **Live Ping** — Real-time latency measurement for each device (right-click context menu)
- **Internet Speed Monitor** — Live upload/download speed on the dashboard with traffic charts
- **Per-Device Bandwidth Control** — Right-click any device to:
  - Cut its internet access entirely
  - Set a speed limit (KB/s or Mbps) with quick presets
  - Restore full connectivity
- **Visual Limit Indicators** — "CUT" (red) and throttle values (orange) shown directly in the device table
- **Dark/Light Themes** — Modern Windows 11-style interface with theme switching
- **Persistent Settings** — JSON-based configuration saved to `~/.tncut/`
- **Device History & Logs** — SQLite database tracking device activity over time

## Tech Stack

| Component    | Technology                     |
|-------------|-------------------------------|
| Language    | Python 3.12+                  |
| GUI         | PySide6 (Qt 6)                |
| Networking  | Scapy, psutil                 |
| Database    | SQLite via SQLAlchemy         |
| Packaging   | PyInstaller                   |

## Installation

### Prerequisites

- Windows 10/11
- Python 3.12+
- [Npcap](https://npcap.com/) (required by Scapy for raw packet capture)

### From source

```bash
git clone https://github.com/BenAmorFarouk/TNcut.git
cd TNcut
pip install -r requirements.txt
python main.py
```

> **Note:** Must be run as Administrator for network scanning and ARP operations.

## Usage

1. **Launch as Administrator** — required for ARP scanning and bandwidth control
2. **Dashboard** — view device count, network status, and live speed charts
3. **Devices tab** — see all discovered devices with IP, MAC, hostname, ping, and limit status
4. **Right-click a device** to:
   - **Ping** — run a 4-packet ping test with min/max/avg stats
   - **Limit Speed** — open a dialog to set bandwidth (0–100,000 KB/s or Mbps), with quick presets (128 KB/s, 256 KB/s, 512 KB/s, 1 Mbps, 5 Mbps)
   - **Cut Internet** — immediately block all traffic
   - **Restore Internet** — remove any active limit
5. **Settings tab** — configure scan intervals, bandwidth baseline, theme, and notifications

## How It Works

TNcut uses **ARP spoofing** to control per-device bandwidth:

| Mode       | Mechanism                                                                 |
|-----------|---------------------------------------------------------------------------|
| **Cut**   | Sends spoofed ARP replies telling the target that the gateway is at our MAC. Traffic is sent to us and dropped. |
| **Limit** | Duty-cycle throttling — alternates between spoofing (block) and restoring (allow) the target's ARP entry at a ratio proportional to the desired speed limit. |
| **Restore** | Sends correct ARP replies (3x) with the real gateway MAC to fix the target's ARP table. |

A static ARP entry is pinned on the host machine to prevent self-poisoning from Npcap packet loopback.

## Build

Build a standalone Windows executable:

```bash
python -m PyInstaller main.py --name TNCut --noconsole ^
  --add-data "logo.png;." ^
  --hidden-import scapy.all ^
  --hidden-import scapy.layers.l2 ^
  --hidden-import scapy.layers.inet ^
  --hidden-import scapy.arch.windows ^
  --hidden-import scapy.arch.windows.native ^
  --hidden-import psutil
```

Output: `dist/TNCut/TNCut.exe`

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
│   └── device_table_model.py   # Qt table model (9 columns)
├── ui/
│   ├── main_window.py          # Main window + live speed
│   ├── dashboard.py            # Dashboard widget
│   ├── devices.py              # Device list + context menu
│   ├── speed_limit_dialog.py   # Speed limit dialog
│   ├── traffic.py              # Traffic page
│   ├── settings.py             # Settings panel
│   ├── logs.py                 # Logs viewer
│   ├── history.py              # History viewer
│   ├── sidebar.py              # Navigation sidebar
│   ├── splash_screen.py        # Splash screen
│   └── about.py                # About page
├── widgets/
│   └── chart_widget.py         # Traffic chart widgets
├── database/
│   └── session.py              # SQLAlchemy session
├── utils/
│   ├── logger.py               # Logging setup
│   └── theme.py                # Dark/light theme
├── logo.png
└── requirements.txt
```

## Disclaimer

This tool is intended for **authorized network administration and educational purposes only**. ARP spoofing can disrupt network connectivity. Only use TNcut on networks you own or have explicit permission to manage. Unauthorized use may violate local laws.

## License

MIT License © BenAmorFarouk
