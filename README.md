<div align="center">

# 🏝️ WinNotch (Dynamic Island for Windows)

**An ultra-smooth, interactive Apple Dynamic Island & Notch experience built natively for Windows 10 & 11.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![GUI](https://img.shields.io/badge/GUI-PySide6%20%2F%20Qt6-41CD52?logo=qt&logoColor=white)](https://doc.qt.io/qtforpython/)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011-0078D6?logo=windows&logoColor=white)](https://www.microsoft.com/windows)
[![Design](https://img.shields.io/badge/Design-Apple%20HIG%20%26%20SF%20Symbols-FF2D55?logo=apple&logoColor=white)](https://developer.apple.com/design/human-interface-guidelines/)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

---

</div>

## 🌟 Overview

**WinNotch** transforms the top center of your Windows screen into a living, responsive **Dynamic Island**. Designed with meticulous adherence to **Apple Human Interface Guidelines (HIG)** and fluid 60 FPS micro-interactions, WinNotch sits quietly at the top of your display as a minimalist notch and smoothly blooms into an interactive multifunction hub upon hover or notification.

From cursor-tracking living eyes to real-time synchronized karaoke lyrics, live Windows notifications, weather forecasts, prayer times, and system metrics—WinNotch elevates your desktop workflow with elegance and craft.

---

## ✨ Features at a Glance

### 1. 👁️ Interactive Collapsed Notch & "Living Eyes"
- **3D Parallax Cursor Tracking**: Minimalist vertical capsules centered in the collapsed notch smoothly tilt and look toward your mouse cursor in real-time.
- **Natural Blinks & Micro-Reactions**: Procedural 120ms blinks every 3.5–5.5s.
- **Playful Expressions State Machine**:
  - **Happy Smiling Arcs (`^  ^`)** and **Playful Winks (`•  <`)** during short pauses.
  - **Side-Eye Squint (`—  •`)** when observing peripheral movement.
  - **Dizzy Spin (`×  ×`)**: Rapidly shaking your cursor triggers an animated dizzy easter egg.
  - **Sleep Breathing**: Gentle slow opacity breathing after prolonged inactivity.
- **Smart Hardware Privacy Indicators**:
  - 🟢 **Apple Green Glow**: Live camera active indicator.
  - 🟠 **Apple Orange Glow**: Microphone active indicator.
  - ⚡ **Charging & Battery**: Transient battery level pill upon charger connection.
- **Auto-Shrink to Minimal Line**: Automatically slims down into an unobtrusive hairline pill when idle.

---

### 2. 🎵 Universal Media Player & Synced Karaoke Lyrics
- **Universal Windows SMTC Listener**: Automatically connects to Spotify, Apple Music, YouTube Music, Chrome, Edge, and native Windows media sessions.
- **Real-Time Synced Lyrics (LRCLIB)**: Automatically fetches line-by-line synchronized karaoke lyrics with smooth auto-scrolling.
- **Click-to-Seek Lyrics**: Click directly on any upcoming lyric line to jump track playback timestamp instantly.
- **Ambient Album Art Glow**: Real-time color extraction from playing track artwork casts a silky, blurred ambient gradient across the island.
- **3 Dynamic Timeline Progress Styles**:
  1. **Classic Line**: Clean, minimalist Apple scrubber.
  2. **Wavy Wiggle**: iOS 16 fluid audio waveform animation.
  3. **Soundwave EQ**: Rhythmic animated audio equalizer bars.
- **Full Media Controls**: Play/pause, track skip, interactive seek scrubbing, and volume adjustment.

---

### 3. 🔔 Live Windows 10/11 Notification Center
- **Zero Fake Mockups**: 100% real live system notifications.
- **Non-Locking SQLite WAL Worker**: Safely queries `%LOCALAPPDATA%\Microsoft\Windows\Notifications\wpndatabase.db` in a background thread without locking OS files.
- **Live Toast Interception**: Instant alert banners for WhatsApp, Chrome, Discord, Slack, Mail, Telegram, and system events.
- **Unread Badge Counters**: Glowing badge count on the collapsed notch and notification header.
- **Apple Frosted Notification Cards**: Rich cards with app icon, sender, message preview, and relative timestamps.
- **Quick Actions**: "Read All", "Clear All", and custom sound notifications.

---

### 4. 🌤️ Immersive Weather & Atmospheric Sky
- **Hyper-Local Forecasts**: Automatic geolocation-based weather or custom city configuration (e.g., Fez, London, Tokyo).
- **Dynamic Sky Surface**: Island background smoothly morphs between atmospheric daylight blue (`#2B82D9` → `#56AEFF`) and midnight indigo (`#0F172A` → `#1E293B`).
- **Daylight Duration Timeline**: Apple SF sunrise & sunset vector glyphs with exact solar hours and daylight span calculation.
- **6-Day Frosted Forecast Capsules**: Smooth pill cards displaying day, weather condition vector, and High/Low temperatures without clipping.
- **Unit Toggle**: Instant conversion between Celsius (°C) and Fahrenheit (°F).

---

### 5. 🕌 Islamic Prayer Times (Awqat Salat)
- **Accurate Astronomical Calculations**: Fajr, Sunrise, Dhuhr, Asr, Maghrib, and Isha calculated for your exact location.
- **Live Countdown Timer**: Displays the time remaining until the next prayer with color-coded alerts (green → amber → red).
- **Adhan Bell Notification**: Visual and audio reminder when prayer time arrives.

---

### 6. ⏱️ Focus Pomodoro Timer
- **Work & Rest Intervals**: 25m Focus, 5m Short Break, and 15m Long Break presets.
- **Radial Circular Progress**: Smooth animated arc showing elapsed and remaining minutes at a glance.

---

### 7. ⚽ Live Football Scoreboard
- **Real-Time Match Tracking**: Live scores, minutes, team crests, and status.
- **Multi-League Coverage**: Premier League, LaLiga, Serie A, Bundesliga, Ligue 1, UEFA Champions League, and Botola Pro.

---

### 8. ⚡ Hardware System Monitor
- **Live Resource Gauges**: Clean circular meters for CPU utilization, RAM usage, and battery percentage.
- **High-Load Alerting**: Instant visual feedback when system resources peak.

---

### 9. ✅ Task To-Do & Quick Capture
- **Fast Inline Task Entry**: Capture reminders and action items without leaving your current window.
- **Interactive Checklists**: One-click completion with strikethrough animations and daily task counters.

---

### 10. ⚙️ macOS / iPadOS Style Settings Window
- **Collapsible Sidebar**: Smooth animated toggle between full 260px navigation pane and a compact 64px icon rail.
- **Full Light & Dark Mode**: Pixel-perfect contrast and specular borders across both themes.
- **Responsive Stretched Layout**: Cards and controls automatically stretch to fill 100% of the window width without artificial constraints.
- **Granular Customization**: Toggle individual carousel widgets, reorder modules, customize idle delay, and fine-tune notification behavior.

---

## 🛠️ Tech Stack & Architecture

- **Language**: Python 3.10+
- **GUI Engine**: [PySide6 (Qt for Python 6)](https://pypi.org/project/PySide6/)
- **Graphics Pipeline**: `QPainter` custom vector drawing with antialiasing and sub-pixel typography.
- **System APIs**: Windows SMTC (`winsdk`), `psutil`, `winreg`, Windows Notification SQLite Database.
- **Network Services**: LRCLIB (synchronized lyrics), Open-Meteo & Nominatim (weather/geo), Aladhan API (prayer times).

---

## 🚀 Installation & Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/ismailatif/WiNotch.git
cd WiNotch
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```
*(Or install manually: `pip install PySide6 requests psutil`)*

### 3. Run WinNotch
```bash
# Standard execution
python island.py

# Or background execution (no terminal window)
pythonw island.py
```

---

## ⌨️ Controls & Gestures

| Action | Micro-Interaction |
| :--- | :--- |
| **Hover Notch** | Smoothly expands the island into full widget mode. |
| **Move Cursor Away** | Automatically collapses back to the compact capsule notch. |
| **Mouse Wheel / Arrow Buttons** | Glide smoothly between active carousel pages (Media, Weather, Notifications, etc.). |
| **Click Gear Icon / Right-Click** | Opens the Apple-style Settings Window. |
| **System Tray Icon** | Access quick actions, page switching, or quit the application. |

---

## 📸 Screenshots

> *Add your screenshots and animated GIFs here to showcase WinNotch in action!*

| Collapsed Living Notch | Universal Media Player | Immersive Weather |
| :---: | :---: | :---: |
| *Minimalist Capsule & Eyes* | *Synced Lyrics & Ambient Glow* | *Daylight Arc & 6-Day Forecast* |

---

## 📄 License

This project is licensed under the **MIT License** - feel free to use, modify, and distribute with attribution.

