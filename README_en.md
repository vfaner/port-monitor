# 🛡 Port Monitor

A beautifully designed cross-platform desktop tool for **detecting port usage on your machine** and killing the occupying process with a single click.

![platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-blue)
![python](https://img.shields.io/badge/python-3.8%2B-green)
![license](https://img.shields.io/badge/license-Apache--2.0-orange)

**English** · [简体中文](./README.md)

## 📸 Screenshot

![Port Monitor UI](./assets/port-monitor.png)

## ✨ Features

- Scans **all listening ports on your machine** at startup, showing:
  - App name · PID · Port · CPU % · Memory % · Action
- **"Stop" button in the Action column**: after confirmation, the process is killed and the row is immediately removed from the table
- CPU / memory usage is color-coded (red / orange / gray) so resource hogs stand out at a glance
- Top search box: filter by app name / port / PID in real time
- Auto-refreshes every 5 seconds; you can also click **Refresh** manually
- **Frameless, rounded, frosted-glass window** with a custom title bar:
  - ❤ Sponsor: pops up a QR code, with **WeChat / Alipay / QQ** tabs
  - Get latest version: opens the GitHub repository
  - Minimize / Maximize / Close
  - Drag the title bar; double-click to toggle maximize / restore
- Cross-platform: Windows / macOS / Linux (built on `psutil`, no platform-specific commands)

## 📥 Download prebuilt binaries (no Python required)

Grab the file for your OS from the [Releases page](https://github.com/vfaner/port-monitor/releases/latest):

| OS | File | How to use |
|---|---|---|
| Windows 10/11 (x64)   | `PortMonitor-windows-x64.zip`  | Unzip → double-click `PortMonitor.exe` |
| macOS (Apple Silicon) | `PortMonitor-macos-arm64.zip`  | Unzip → double-click `PortMonitor.app`; on first run, right-click → Open if Gatekeeper blocks it |
| macOS (Intel)         | *(no prebuilt binary)*         | See "Run from source" below |
| Linux (x64)           | `PortMonitor-linux-x64.tar.gz` | `tar xzf ...` → `./PortMonitor` |

> Double-click to run — no Python or extra dependencies needed.
> **Intel Mac users**: GitHub Actions is phasing out Intel macOS runners, so prebuilt Intel binaries are no longer produced. Please run from source (see below).

## 🚀 Run from source

```bash
pip install -r requirements.txt
python port_monitor.py
```

> Some system processes belong to other users; scanning or stopping them requires elevated privileges:
> - macOS / Linux: `sudo python port_monitor.py`
> - Windows: run the terminal as Administrator

## 💰 Configure sponsor QR codes

Drop your real QR-code images into the `assets/` directory (see `assets/README.md`):
`wechat.png` / `alipay.png` / `qq.png`. If missing, placeholder images are shown.

## 🔧 Customize

Edit the config section at the top of `port_monitor.py`:

```python
GITHUB_URL = "https://github.com/vfaner/port-monitor"  # URL for the top-right link
APP_NAME   = "端口卫士 · Port Monitor"
```

## 📦 Build a standalone executable (optional)

```bash
pip install pyinstaller
pyinstaller -F -w --add-data "assets:assets" port_monitor.py   # macOS/Linux
pyinstaller -F -w --add-data "assets;assets" port_monitor.py   # Windows
```

Or use the included `PortMonitor.spec`:

```bash
pyinstaller --clean --noconfirm PortMonitor.spec
```

CI builds for all four platforms (Windows x64, macOS Apple Silicon, macOS Intel, Linux x64) are produced automatically by GitHub Actions on every `v*` tag push.

## License

Licensed under **Apache License 2.0**, Copyright © 2026 rgh.

- ✅ Free to use, modify, redistribute, and use commercially
- ⚠️ Redistributions **must retain** the `LICENSE` and `NOTICE` files, which include the author attribution (rgh) and project URL
- ⚠️ Modified files must carry prominent notices stating that you changed them

See [LICENSE](./LICENSE) and [NOTICE](./NOTICE) for the full terms.
