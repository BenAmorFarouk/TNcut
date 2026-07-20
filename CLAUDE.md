# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

TNcut is a Windows desktop app (PySide6/Qt6) that discovers devices on the local subnet and controls per-device bandwidth via ARP spoofing, similar to NetCut. See `README.md` for user-facing features.

## Commands

```powershell
# Install deps
pip install -r requirements.txt

# Run (must be launched as Administrator — ARP scanning and spoofing need raw sockets)
python main.py

# Build standalone exe (uses the committed spec)
python -m PyInstaller TNCut.spec
# Output: dist/TNCut/TNCut.exe
```

There is no test suite, linter, or test runner configured.

## Runtime prerequisites

- **Administrator privileges** are required — scanning and ARP operations use raw packets. The app will start without them but network features silently fail.
- **[Npcap](https://npcap.com/)** must be installed; Scapy depends on it. Scanner/spoofer modules degrade gracefully via a `SCAPY_AVAILABLE` flag when the import fails, so a missing Npcap won't crash the app but disables all network functions.

## Architecture

Threading model matters here. Qt runs the UI on the main thread; network work runs on background threads and must not touch Qt widgets directly.

- **`main.py`** — entry point. Shows splash, calls `initialize_system()` (logging → database → theme), creates `MainWindow`, then starts `network_service`.
- **`services/network_service.py`** — singleton `network_service`. Owns a daemon thread (`_run_scanner`) that runs `network_scanner.scan_network()` on a loop (default 30s). Notifies the UI through `update_callbacks`. This is the bridge between background scanning and the Qt layer.
- **`network/scanner.py`** — singleton `network_scanner`. ARP-based discovery, hostname resolution, ping, gateway detection. Loads `oui_vendors.txt` into `OUI_MAP` at import for MAC→vendor lookup (this file must be bundled by PyInstaller — see the `.spec`).
- **`network/arp_spoof.py`** — singleton `ARPSpoofer`. Per-device bandwidth control. Each target gets a `TargetInfo` and its own spoof thread. `limit_kbps == 0` means full cut (continuous spoof); `> 0` means duty-cycle throttle (alternate spoof/restore). Pins a **static ARP entry** for the gateway via `netsh` so our own cache isn't poisoned by Npcap loopback. Always call restore/cleanup to undo static ARP entries.
- **`config/settings.py`** — dataclass-based settings (`NetworkSettings`, `UISettings`, `DatabaseSettings`, `NotificationSettings`) with JSON persistence via singleton `settings_manager`. Note `settings_manager.get()` may return a dict or a dataclass; call sites defensively handle both (see `main.py`).
- **`database/session.py`** — SQLAlchemy setup; `init_database(db_path, echo)`. DB at `data/tncut.db`. Logging can write to DB via `enable_db_logging()` once the DB is ready.
- **`models/`** — `models.py` (SQLAlchemy/data models like `Device`, `DeviceHistory`) and `device_table_model.py` (Qt `QAbstractTableModel` for the device table).
- **`ui/`** — one module per page (`dashboard`, `devices`, `traffic`, `settings`, `logs`, `history`, `about`), plus `main_window`, `sidebar`, `splash_screen`, `speed_limit_dialog`. `utils/theme.py` provides dark/light theming via `ThemeManager`.

## Conventions

- Core network components are module-level singletons imported directly (`network_scanner`, `network_service`, `settings_manager`). Don't instantiate new copies.
- Subprocess calls to Windows tools (`arp`, `netsh`) use `creationflags=0x08000000` (CREATE_NO_WINDOW) to suppress console popups. Keep this when adding new subprocess calls.
- PyInstaller bundling: added data files (e.g. `oui_vendors.txt`, `logo.png`, `logo.ico`) resolve their base path via `sys._MEIPASS` when `sys.frozen` is set. New bundled resources need entries in `TNCut.spec` and matching frozen-path handling.
