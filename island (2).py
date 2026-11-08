"""
Dynamic Island for Windows: prayer times, Pomodoro, live football and a system monitor.

Install:  python -m pip install PySide6 requests psutil
Run:      pythonw island.py      (pythonw = no console window)

Hover the island to expand it. Use the arrows or the mouse wheel to switch pages.
Right-click it (or the tray icon) for reminders, refresh and quit.
"""
import os
import sys
import time
import math
import datetime
import threading
from collections import deque

import psutil
import requests
from PySide6.QtCore import (Qt, QTimer, QRect, QRectF, QPointF, QPropertyAnimation,
                            QVariantAnimation, QEasingCurve, Signal, QObject)
from PySide6.QtGui import (QPainter, QColor, QPainterPath, QPen, QFont, QPixmap, QImage,
                           QConicalGradient, QLinearGradient, QIcon)
from PySide6.QtWidgets import (QApplication, QWidget, QLabel, QPushButton, QHBoxLayout,
                               QVBoxLayout, QStackedWidget, QMenu, QLayout,
                               QGraphicsOpacityEffect, QSizePolicy, QSystemTrayIcon)

try:
    import winsound
except ImportError:
    winsound = None

# ======================= settings =======================
# Prayer times. Leave CITY empty to detect your city automatically from your internet connection.
CITY = ""                  # e.g. "Casablanca"
COUNTRY = ""               # e.g. "Morocco"
METHOD = None              # None = Morocco (21) for Morocco, Muslim World League (3) elsewhere
REMIND_MINUTES = 5         # reminder before each prayer

LEAGUES = {
    "eng.1": "Premier League",
    "esp.1": "LaLiga",
    "ita.1": "Serie A",
    "ger.1": "Bundesliga",
    "fra.1": "Ligue 1",
    "uefa.champions": "Champions League",
}
REFRESH_SECONDS = 30
ROTATE_SECONDS = 8
FOCUS_MIN, SHORT_MIN, LONG_MIN = 25, 5, 15
COLLAPSED = (270, 34)
TINY = (140, 10)           # the thin line the island shrinks to when idle
IDLE_SECONDS = 5           # pill -> line after this many seconds
EXPANDED = (500, 158)

# Apple system colours (dark mode)
RED, GREEN, BLUE = "#ff453a", "#30d158", "#0a84ff"
FILL, FILL_HI = "#2c2c2e", "#3a3a3c"
MUTED = "#8e8e93"
RING_COLORS = [("#fa114f", "#ff6a92"), ("#7ee000", "#c6ff5e"), ("#00c7e6", "#7ff4ff")]
ESPN = "https://site.api.espn.com/apis/site/v2/sports/soccer/{}/scoreboard"
DISK = "C:\\" if os.name == "nt" else "/"
PRAYERS = [("Fajr", "الفجر"), ("Dhuhr", "الظهر"), ("Asr", "العصر"),
           ("Maghrib", "المغرب"), ("Isha", "العشاء")]

STYLE = f"""
QWidget {{ color: white; font-family: 'Segoe UI'; font-size: 12px; background: transparent; }}
QLabel#muted {{ color: {MUTED}; }}
QToolTip {{ color: white; background: #1c1c1e; border: 1px solid #333; }}
QMenu {{ background: #1c1c1e; border: 1px solid #333; border-radius: 8px; padding: 4px; }}
QMenu::item {{ padding: 6px 18px; border-radius: 5px; }}
QMenu::item:selected {{ background: {BLUE}; }}
"""


def blend(a, b, t):
    a, b = QColor(a), QColor(b)
    mix = lambda x, y: int(x + (y - x) * t)
    return QColor(mix(a.red(), b.red()), mix(a.green(), b.green()),
                  mix(a.blue(), b.blue()), mix(a.alpha(), b.alpha()))


def anim(parent, ms, setter, curve=QEasingCurve.OutCubic):
    a = QVariantAnimation(parent)
    a.setDuration(ms)
    a.setEasingCurve(curve)
    a.valueChanged.connect(setter)
    return a


def run_anim(a, start, end):
    a.stop()
    a.setStartValue(float(start))
    a.setEndValue(float(end))
    a.start()


def beep():
    if winsound:
        winsound.MessageBeep(winsound.MB_ICONASTERISK)
    else:
        QApplication.beep()


# ======================= icons (drawn, so they're crisp at any size) =======================
def draw_icon(p, name, rect, color):
    c, s = rect.center(), min(rect.width(), rect.height())
    color = QColor(color)
    line = QPen(color, max(1.6, s * 0.075), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    p.save()
    if name in ("play", "skip"):
        k = s * 0.22
        off = -k * 0.35 if name == "skip" else k * 0.15
        tri = QPainterPath()
        tri.moveTo(c.x() - k * 0.8 + off, c.y() - k)
        tri.lineTo(c.x() + k * 0.9 + off, c.y())
        tri.lineTo(c.x() - k * 0.8 + off, c.y() + k)
        tri.closeSubpath()
        p.setPen(QPen(color, s * 0.06, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(color)
        p.drawPath(tri)
        if name == "skip":
            p.setPen(line)
            x = c.x() + k * 1.05 + off
            p.drawLine(QPointF(x, c.y() - k), QPointF(x, c.y() + k))
    elif name == "pause":
        w, h = s * 0.12, s * 0.42
        p.setPen(Qt.NoPen)
        p.setBrush(color)
        for dx in (-s * 0.1 - w / 2, s * 0.1 - w / 2):
            p.drawRoundedRect(QRectF(c.x() + dx, c.y() - h / 2, w, h), w / 3, w / 3)
    elif name == "reset":
        r = s * 0.24
        p.setPen(line)
        p.setBrush(Qt.NoBrush)
        p.drawArc(QRectF(c.x() - r, c.y() - r, 2 * r, 2 * r), 80 * 16, 290 * 16)
        tip = QPointF(c.x() + r * math.cos(math.radians(80)) + s * 0.06,
                      c.y() - r * math.sin(math.radians(80)))
        a = s * 0.1
        p.drawLine(tip, QPointF(tip.x() - a, tip.y() - a))
        p.drawLine(tip, QPointF(tip.x() - a, tip.y() + a))
    elif name in ("left", "right"):
        d = s * 0.11 * (1 if name == "left" else -1)
        p.setPen(line)
        p.drawPolyline([QPointF(c.x() + d, c.y() - abs(d) * 1.9), QPointF(c.x() - d, c.y()),
                        QPointF(c.x() + d, c.y() + abs(d) * 1.9)])
    elif name in ("bell", "bell-off"):
        b = s * 0.24
        body = QPainterPath()
        body.moveTo(c.x() - b, c.y() + b * 0.65)
        body.lineTo(c.x() - b * 0.78, c.y() - b * 0.05)
        body.cubicTo(c.x() - b * 0.78, c.y() - b * 1.2, c.x() + b * 0.78, c.y() - b * 1.2,
                     c.x() + b * 0.78, c.y() - b * 0.05)
        body.lineTo(c.x() + b, c.y() + b * 0.65)
        body.closeSubpath()
        p.setPen(Qt.NoPen)
        p.setBrush(color)
        p.drawPath(body)
        p.drawEllipse(QPointF(c.x(), c.y() + b * 0.95), b * 0.24, b * 0.24)
        if name == "bell-off":
            p.setPen(QPen(QColor(FILL), s * 0.16, Qt.SolidLine, Qt.RoundCap))
            p.drawLine(QPointF(c.x() - b * 1.1, c.y() - b * 1.1), QPointF(c.x() + b * 1.1, c.y() + b * 1.1))
            p.setPen(line)
            p.drawLine(QPointF(c.x() - b * 1.1, c.y() - b * 1.1), QPointF(c.x() + b * 1.1, c.y() + b * 1.1))
    p.restore()


# ======================= Apple-style controls =======================
class AppleButton(QPushButton):
    """Round button with a drawn icon, a soft hover glow and a press 'squish'.
    kind: 'circle' (grey), 'accent' (coloured), 'ghost' (no background until hover)."""

    def __init__(self, icon, kind="circle", size=28, tip="", color=RED):
        super().__init__()
        self.icon_name, self.kind, self.color = icon, kind, QColor(color)
        self.hover = self.press = 0.0
        self.setFixedSize(size, size)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)
        self.setToolTip(tip)
        self.hover_anim = anim(self, 180, lambda v: self._set("hover", v))
        self.press_anim = anim(self, 110, lambda v: self._set("press", v))

    def _set(self, name, value):
        setattr(self, name, float(value))
        self.update()

    def set_icon(self, name):
        self.icon_name = name
        self.update()

    def set_color(self, color):
        self.color = QColor(color)
        self.update()

    def enterEvent(self, e):
        run_anim(self.hover_anim, self.hover, 1)
        super().enterEvent(e)

    def leaveEvent(self, e):
        run_anim(self.hover_anim, self.hover, 0)
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        run_anim(self.press_anim, self.press, 1)
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        run_anim(self.press_anim, self.press, 0)
        super().mouseReleaseEvent(e)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w = self.width()
        scale = 1 - 0.09 * self.press
        p.translate(w / 2, w / 2); p.scale(scale, scale); p.translate(-w / 2, -w / 2)
        r = QRectF(0.5, 0.5, w - 1, w - 1)
        if self.kind == "accent":
            bg = blend(self.color, self.color.lighter(125), self.hover)
        elif self.kind == "ghost":
            bg = blend(QColor(44, 44, 46, 0), QColor(FILL), self.hover)
        else:
            bg = blend(FILL, FILL_HI, self.hover)
        p.setPen(Qt.NoPen)
        p.setBrush(bg)
        p.drawEllipse(r)
        if self.kind != "ghost":
            gloss = QLinearGradient(0, 0, 0, w)
            gloss.setColorAt(0, QColor(255, 255, 255, 40))
            gloss.setColorAt(0.55, QColor(255, 255, 255, 0))
            p.setBrush(gloss)
            p.drawEllipse(r)
        icon_color = blend(MUTED, "#ffffff", self.hover) if self.kind == "ghost" else QColor("white")
        draw_icon(p, self.icon_name, r, icon_color)


class Segmented(QWidget):
    """iOS segmented control with a sliding thumb."""
    changed = Signal(int)

    def __init__(self, labels, width=210):
        super().__init__()
        self.labels = labels
        self.index, self.pos = 0, 0.0
        self.setFixedSize(width, 28)
        self.setCursor(Qt.PointingHandCursor)
        self.slide = anim(self, 280, self._move)

    def _move(self, v):
        self.pos = float(v)
        self.update()

    def set_index(self, i):
        self.index = i
        run_anim(self.slide, self.pos, i)

    def mousePressEvent(self, e):
        i = min(int(e.position().x() // (self.width() / len(self.labels))), len(self.labels) - 1)
        if i != self.index:
            self.set_index(i)
            self.changed.emit(i)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h, n = self.width(), self.height(), len(self.labels)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#1c1c1e"))
        p.drawRoundedRect(QRectF(0, 0, w, h), h / 2, h / 2)
        seg = (w - 4) / n
        thumb = QRectF(2 + self.pos * seg, 2, seg, h - 4)
        p.setBrush(QColor("#48484a"))
        p.drawRoundedRect(thumb, (h - 4) / 2, (h - 4) / 2)
        f = QFont("Segoe UI", 9)
        f.setWeight(QFont.DemiBold)
        p.setFont(f)
        for i, label in enumerate(self.labels):
            t = max(0.0, 1 - abs(self.pos - i))
            p.setPen(blend(MUTED, "#ffffff", t))
            p.drawText(QRectF(2 + i * seg, 0, seg, h), Qt.AlignCenter, label)


# ======================= prayer times =======================
class PrayerFetcher(QObject):
    done = Signal(object)

    def __init__(self):
        super().__init__()
        self.busy = False
        self.last_try = 0.0

    def fetch(self, force=False):
        if self.busy or (not force and time.monotonic() - self.last_try < 120):
            return
        self.busy, self.last_try = True, time.monotonic()
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        city, country = CITY, COUNTRY
        if not city:
            try:
                info = requests.get("https://ipwho.is/", timeout=8).json()
                city, country = info.get("city", ""), info.get("country", "")
            except Exception:
                pass
        city, country = city or "Casablanca", country or "Morocco"
        method = METHOD if METHOD is not None else (21 if "morocco" in country.lower() else 3)
        result = {"city": city, "date": datetime.date.today(), "days": {}, "hijri": ""}
        for offset in (0, 1):
            day = datetime.date.today() + datetime.timedelta(days=offset)
            try:
                data = requests.get(f"https://api.aladhan.com/v1/timingsByCity/{day:%d-%m-%Y}",
                                    params={"city": city, "country": country, "method": method},
                                    timeout=10).json()["data"]
                times = {}
                for name, _ in PRAYERS:
                    hh, mm = data["timings"][name][:5].split(":")
                    times[name] = datetime.datetime.combine(day, datetime.time(int(hh), int(mm)))
                result["days"][offset] = times
                if offset == 0:
                    h = data["date"]["hijri"]
                    result["hijri"] = f"{h['day']} {h['month']['en']} {h['year']}"
            except Exception:
                continue
        self.busy = False
        self.done.emit(result if 0 in result["days"] else None)


class ProgressLine(QWidget):
    def __init__(self, color):
        super().__init__()
        self.color, self.value = QColor(color), 0.0
        self.setFixedHeight(4)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 30))
        p.drawRoundedRect(QRectF(0, 0, self.width(), 4), 2, 2)
        grad = QLinearGradient(0, 0, self.width(), 0)
        grad.setColorAt(0, self.color.darker(140))
        grad.setColorAt(1, self.color)
        p.setBrush(grad)
        p.drawRoundedRect(QRectF(0, 0, max(4, self.width() * self.value), 4), 2, 2)


class PrayerCell(QWidget):
    def __init__(self, name, arabic):
        super().__init__()
        self.name, self.arabic, self.time = name, arabic, "--:--"
        self.active, self.glow = False, 0.0
        self.setToolTip(arabic)
        self.setFixedHeight(36)
        self.glow_anim = anim(self, 350, self._set_glow)

    def _set_glow(self, v):
        self.glow = float(v)
        self.update()

    def set_active(self, active):
        if active != self.active:
            self.active = active
            run_anim(self.glow_anim, self.glow, 1 if active else 0)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(1, 0, self.width() - 2, self.height())
        bg = QColor(GREEN)
        bg.setAlpha(int(48 * self.glow))
        p.setPen(Qt.NoPen)
        p.setBrush(bg)
        p.drawRoundedRect(r, 9, 9)
        f = QFont("Segoe UI", 8)
        p.setFont(f)
        p.setPen(blend(MUTED, GREEN, self.glow))
        p.drawText(QRectF(r.x(), 3, r.width(), 14), Qt.AlignCenter, self.name)
        f.setPointSize(10); f.setWeight(QFont.Bold)
        p.setFont(f)
        p.setPen(QColor("white"))
        p.drawText(QRectF(r.x(), 16, r.width(), 18), Qt.AlignCenter, self.time)


class PrayerPage(QWidget):
    title = "Prayer times"

    def __init__(self):
        super().__init__()
        self.data = None
        self.reminders = True

        self.caption = QLabel("Next prayer", objectName="muted")
        self.next_name = QLabel("Loading…")
        self.next_name.setStyleSheet("font-size: 17px; font-weight: 700;")
        self.countdown = QLabel("")
        self.countdown.setStyleSheet(f"font-size: 22px; font-weight: 700; color: {GREEN};")
        self.at_lbl = QLabel("", objectName="muted")
        self.bell = AppleButton("bell", "circle", 28, "Turn reminders off")
        self.bell.clicked.connect(self.toggle_reminders)

        left = QVBoxLayout(); left.setSpacing(0)
        left.addWidget(self.caption); left.addWidget(self.next_name)
        right = QVBoxLayout(); right.setSpacing(0)
        right.addWidget(self.countdown, alignment=Qt.AlignRight)
        right.addWidget(self.at_lbl, alignment=Qt.AlignRight)
        top = QHBoxLayout()
        top.addLayout(left); top.addStretch(); top.addLayout(right)
        top.addSpacing(8); top.addWidget(self.bell)

        self.bar = ProgressLine(GREEN)
        self.cells = {name: PrayerCell(name, ar) for name, ar in PRAYERS}
        cells = QHBoxLayout(); cells.setSpacing(4)
        for c in self.cells.values():
            cells.addWidget(c)

        col = QVBoxLayout(self)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(5)
        col.addLayout(top)
        col.addWidget(self.bar)
        col.addLayout(cells)

    def toggle_reminders(self):
        self.reminders = not self.reminders
        self.bell.set_icon("bell" if self.reminders else "bell-off")
        self.bell.setToolTip("Turn reminders off" if self.reminders else "Turn reminders on")

    def set_data(self, data):
        if data:
            self.data = data
            for name, cell in self.cells.items():
                cell.time = data["days"][0][name].strftime("%H:%M")
                cell.update()
        self.tick()

    def all_times(self):
        out = []
        for offset in sorted(self.data["days"]):
            out += [(n, t) for n, t in self.data["days"][offset].items()]
        return sorted(out, key=lambda x: x[1])

    def upcoming(self):
        """(name, datetime) of the next prayer, or None."""
        if not self.data:
            return None
        now = datetime.datetime.now()
        for name, t in self.all_times():
            if t > now:
                return name, t
        return None

    def tick(self):
        nxt = self.upcoming()
        if not nxt:
            self.next_name.setText("Loading…" if not self.data else "—")
            return
        name, t = nxt
        now = datetime.datetime.now()
        secs = int((t - now).total_seconds())
        arabic = dict(PRAYERS)[name]
        self.next_name.setText(f"{name}  <span style='color:{MUTED}; font-weight:400'>{arabic}</span>")
        h, rem = divmod(secs, 3600)
        m, s = divmod(rem, 60)
        self.countdown.setText(f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}")
        soon = secs <= REMIND_MINUTES * 60
        self.countdown.setStyleSheet(f"font-size: 22px; font-weight: 700; color: {RED if soon else GREEN};")
        self.at_lbl.setText(f"at {t:%H:%M}  ·  {self.data['city']}")
        past = [x for x in self.all_times() if x[1] <= now]
        prev = past[-1][1] if past else t - datetime.timedelta(hours=8)
        self.bar.value = 1 - secs / max((t - prev).total_seconds(), 1)
        self.bar.update()
        for n, cell in self.cells.items():
            cell.set_active(n == name)

    def mini_text(self):
        nxt = self.upcoming()
        if not nxt:
            return "", False
        name, t = nxt
        mins = math.ceil((t - datetime.datetime.now()).total_seconds() / 60)
        if mins <= REMIND_MINUTES:
            return f"<span style='color:{GREEN}'>●</span> {name} in {mins} min", True
        return f"{name} {t:%H:%M}", False


# ======================= football =======================
class ScoreFetcher(QObject):
    done = Signal(list)

    def __init__(self):
        super().__init__()
        self.logo_cache = {}
        self.busy = False

    def fetch(self):
        if not self.busy:
            self.busy = True
            threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        matches = []
        for code, league in LEAGUES.items():
            try:
                data = requests.get(ESPN.format(code), timeout=10).json()
            except Exception:
                continue
            for ev in data.get("events", []):
                try:
                    comp = ev["competitions"][0]
                    teams = {c["homeAway"]: c for c in comp["competitors"]}
                    status = ev["status"]["type"]
                    m = {"league": league, "state": status.get("state", "pre"),
                         "detail": status.get("shortDetail", ""), "date": ev.get("date", "")}
                    for side in ("home", "away"):
                        t = teams[side]
                        m[side] = {"abbr": t["team"].get("abbreviation", "?"),
                                   "name": t["team"].get("displayName", ""),
                                   "score": t.get("score", "0"),
                                   "logo": self._logo(t["team"].get("logo", ""))}
                    matches.append(m)
                except (KeyError, IndexError):
                    continue
        order = {"in": 0, "pre": 1, "post": 2}
        matches.sort(key=lambda m: (order.get(m["state"], 3), m["date"]))
        self.busy = False
        self.done.emit(matches)

    def _logo(self, url):
        if not url:
            return None
        if url not in self.logo_cache:
            try:
                img = QImage()
                img.loadFromData(requests.get(url, timeout=10).content)
                self.logo_cache[url] = img.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            except Exception:
                self.logo_cache[url] = None
        return self.logo_cache[url]


class FootballPage(QWidget):
    title = "Football"

    def __init__(self):
        super().__init__()
        self.matches, self.i = [], 0

        def logo():
            lbl = QLabel()
            lbl.setFixedSize(40, 40)
            lbl.setAlignment(Qt.AlignCenter)
            return lbl

        self.home_logo, self.away_logo = logo(), logo()
        self.home_name, self.away_name = QLabel(), QLabel()
        for n in (self.home_name, self.away_name):
            n.setStyleSheet("font-size: 14px; font-weight: 600;")
        self.score = QLabel("Loading…")
        self.status = QLabel(objectName="muted", textFormat=Qt.RichText)
        prev = AppleButton("left", "ghost", 22)
        nxt = AppleButton("right", "ghost", 22)
        prev.clicked.connect(lambda: self.step(-1))
        nxt.clicked.connect(lambda: self.step(1))
        self.counter = QLabel(objectName="muted")

        teams = QHBoxLayout()
        teams.addWidget(self.home_logo); teams.addWidget(self.home_name); teams.addStretch()
        teams.addWidget(self.score); teams.addStretch()
        teams.addWidget(self.away_name); teams.addWidget(self.away_logo)
        nav = QHBoxLayout()
        nav.addStretch(); nav.addWidget(prev); nav.addWidget(self.counter); nav.addWidget(nxt)
        nav.addStretch()
        col = QVBoxLayout(self)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(2)
        col.addLayout(teams)
        col.addWidget(self.status, alignment=Qt.AlignHCenter)
        col.addLayout(nav)

        self.rotate = QTimer(self)
        self.rotate.setInterval(ROTATE_SECONDS * 1000)
        self.rotate.timeout.connect(lambda: self.step(1))
        self.rotate.start()
        self.show_match()

    def set_matches(self, matches):
        self.matches = matches
        self.i = min(self.i, max(len(matches) - 1, 0))
        self.show_match()

    def step(self, delta):
        if self.matches:
            self.i = (self.i + delta) % len(self.matches)
            self.rotate.start()
            self.show_match()

    def show_match(self):
        if not self.matches:
            for w in (self.home_logo, self.away_logo, self.home_name, self.away_name):
                w.clear()
            self.score.setText("No matches today")
            self.score.setStyleSheet("font-size: 18px; font-weight: 700;")
            self.status.setText("Scores refresh automatically")
            self.counter.clear()
            self.layout().invalidate()
            return
        m = self.matches[self.i]
        for side, logo_lbl, name_lbl in (("home", self.home_logo, self.home_name),
                                         ("away", self.away_logo, self.away_name)):
            img = m[side]["logo"]
            if img is not None and not img.isNull():
                logo_lbl.setPixmap(QPixmap.fromImage(img).scaled(
                    40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                logo_lbl.clear()
            name_lbl.setText(m[side]["abbr"])
            name_lbl.setToolTip(m[side]["name"])
        self.score.setStyleSheet("font-size: 26px; font-weight: 700;")
        if m["state"] == "pre":
            self.score.setText(self.kickoff(m["date"]))
        else:
            self.score.setText(f"{m['home']['score']} – {m['away']['score']}")
        if m["state"] == "in":
            self.status.setText(f"<span style='color:{RED}'>● Live {m['detail']}</span>"
                                f"&nbsp;&nbsp;{m['league']}")
        else:
            self.status.setText(f"{m['detail']}&nbsp;&nbsp;{m['league']}")
        self.counter.setText(f"{self.i + 1}/{len(self.matches)}")
        self.layout().invalidate()

    @staticmethod
    def kickoff(iso):
        try:
            dt = datetime.datetime.fromisoformat(iso.replace("Z", "+00:00"))
            return dt.astimezone().strftime("%H:%M")
        except ValueError:
            return "vs"

    def live_text(self):
        for m in self.matches:
            if m["state"] == "in":
                return (f"{m['home']['abbr']} {m['home']['score']}–"
                        f"{m['away']['score']} {m['away']['abbr']}")
        return ""


# ======================= pomodoro =======================
class TimerRing(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(92, 92)
        self.progress, self.color = 1.0, QColor(RED)
        self.time_text, self.sub_text = "25:00", "Focus"

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(5, 5, 82, 82)
        track = QColor(self.color); track.setAlpha(50)
        p.setPen(QPen(track, 7))
        p.drawEllipse(r)
        pen = QPen(self.color, 7)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.drawArc(r, 90 * 16, int(-360 * 16 * self.progress))
        f = QFont("Segoe UI", 15)
        f.setWeight(QFont.Bold)
        p.setFont(f)
        p.setPen(QColor("white"))
        p.drawText(QRectF(0, 26, 92, 26), Qt.AlignCenter, self.time_text)
        f.setPointSize(8); f.setWeight(QFont.Normal)
        p.setFont(f)
        p.setPen(QColor(MUTED))
        p.drawText(QRectF(0, 50, 92, 16), Qt.AlignCenter, self.sub_text)


class PomodoroPage(QWidget):
    title = "Pomodoro"
    MODES = [("focus", FOCUS_MIN, "Focus", RED),
             ("short", SHORT_MIN, "Short break", GREEN),
             ("long", LONG_MIN, "Long break", BLUE)]

    def __init__(self):
        super().__init__()
        self.sessions, self.running, self.mode_i = 0, False, 0
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.tick)

        self.ring = TimerRing()
        self.seg = Segmented(["Focus", "Short", "Long"])
        self.seg.changed.connect(self.set_mode)
        reset = AppleButton("reset", "circle", 32, "Reset")
        reset.clicked.connect(lambda: self.set_mode(self.mode_i))
        self.play = AppleButton("play", "accent", 40, "Start")
        self.play.clicked.connect(self.toggle)
        skip = AppleButton("skip", "circle", 32, "Skip to next")
        skip.clicked.connect(self.next_mode)
        self.session_lbl = QLabel(objectName="muted")

        controls = QHBoxLayout()
        controls.setSpacing(12)
        controls.addStretch(); controls.addWidget(reset); controls.addWidget(self.play)
        controls.addWidget(skip); controls.addStretch()
        right = QVBoxLayout()
        right.setSpacing(4)
        right.addWidget(self.seg, alignment=Qt.AlignHCenter)
        right.addLayout(controls)
        right.addWidget(self.session_lbl, alignment=Qt.AlignHCenter)

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self.ring)
        row.addSpacing(14)
        row.addLayout(right, 1)
        self.set_mode(0)

    def set_mode(self, i):
        self.mode_i = i
        _, minutes, label, color = self.MODES[i]
        self.total = self.left = minutes * 60
        self.ring.color = QColor(color)
        self.ring.sub_text = label
        self.play.set_color(color)
        if self.seg.index != i:
            self.seg.set_index(i)
        self.stop()
        self.refresh()

    def next_mode(self):
        if self.mode_i == 0:
            self.sessions += 1
            self.set_mode(2 if self.sessions % 4 == 0 else 1)
        else:
            self.set_mode(0)

    def toggle(self):
        if self.running:
            self.stop()
        else:
            self.running = True
            self.play.set_icon("pause")
            self.play.setToolTip("Pause")
            self.timer.start()

    def stop(self):
        self.running = False
        self.play.set_icon("play")
        self.play.setToolTip("Start")
        self.timer.stop()

    def tick(self):
        self.left -= 1
        if self.left <= 0:
            beep()
            self.next_mode()
            return
        self.refresh()

    def refresh(self):
        m, s = divmod(self.left, 60)
        self.ring.time_text = f"{m:02d}:{s:02d}"
        self.ring.progress = self.left / self.total
        self.ring.update()
        done = self.sessions % 4
        dots = "".join(f"<span style='color:{RED if k < done else '#48484a'}'>●</span> " for k in range(4))
        self.session_lbl.setText(f"{dots}&nbsp;Session {done + 1} of 4")

    def status_text(self):
        if not self.running:
            return ""
        m, s = divmod(self.left, 60)
        return f"<span style='color:{self.MODES[self.mode_i][3]}'>●</span> {m:02d}:{s:02d}"


# ======================= system monitor =======================
class ActivityRings(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(84, 84)
        self.values = [0.0, 0.0, 0.0]

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        width = 9.5
        for i, (v, (c1, c2)) in enumerate(zip(self.values, RING_COLORS)):
            inset = 5 + i * 12.5
            r = QRectF(inset, inset, 84 - 2 * inset, 84 - 2 * inset)
            track = QColor(c1); track.setAlpha(55)
            p.setPen(QPen(track, width))
            p.drawEllipse(r)
            if v <= 0.005:
                continue
            grad = QConicalGradient(r.center(), 90)
            grad.setColorAt(0.0, QColor(c2))
            grad.setColorAt(max(0.01, 1 - v), QColor(c2))
            grad.setColorAt(1.0, QColor(c1))
            pen = QPen(grad, width)
            pen.setCapStyle(Qt.RoundCap)
            p.setPen(pen)
            p.drawArc(r, 90 * 16, int(-360 * 16 * min(v, 1.0)))


class Sparkline(QWidget):
    def __init__(self, color):
        super().__init__()
        self.color = QColor(color)
        self.history = deque([0.0] * 60, maxlen=60)
        self.setFixedHeight(28)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def push(self, v):
        self.history.append(v)
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 14))
        p.drawRoundedRect(QRectF(0, 0, w, h), 7, 7)
        pts = [QPointF(i * w / (len(self.history) - 1), h - 3 - v * (h - 6))
               for i, v in enumerate(self.history)]
        line = QPainterPath(pts[0])
        for a, b in zip(pts, pts[1:]):
            mid = (a.x() + b.x()) / 2
            line.cubicTo(QPointF(mid, a.y()), QPointF(mid, b.y()), b)
        fill = QPainterPath(line)
        fill.lineTo(w, h); fill.lineTo(0, h); fill.closeSubpath()
        grad = QLinearGradient(0, 0, 0, h)
        top = QColor(self.color); top.setAlpha(110)
        bottom = QColor(self.color); bottom.setAlpha(0)
        grad.setColorAt(0, top); grad.setColorAt(1, bottom)
        p.fillPath(fill, grad)
        p.setPen(QPen(self.color, 1.6))
        p.setBrush(Qt.NoBrush)
        p.drawPath(line)


class Stat(QWidget):
    def __init__(self, name, color):
        super().__init__()
        self.value = QLabel("0%")
        self.value.setStyleSheet("font-size: 18px; font-weight: 700;")
        label = QLabel(f"<span style='color:{color}'>●</span> {name}",
                       objectName="muted", textFormat=Qt.RichText)
        col = QVBoxLayout(self)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(0)
        col.addWidget(self.value)
        col.addWidget(label)


def fmt_speed(bps):
    for unit in ("B/s", "KB/s", "MB/s", "GB/s"):
        if bps < 1024 or unit == "GB/s":
            return f"{bps:.0f} {unit}" if unit == "B/s" else f"{bps:.1f} {unit}"
        bps /= 1024


class SystemPage(QWidget):
    title = "System"

    def __init__(self):
        super().__init__()
        self.targets = [0.0, 0.0, 0.0]
        self.shown = [0.0, 0.0, 0.0]
        psutil.cpu_percent(None)
        self.last_net = psutil.net_io_counters()
        self.last_time = time.monotonic()

        self.rings = ActivityRings()
        self.cpu = Stat("CPU", RING_COLORS[0][0])
        self.mem = Stat("Memory", RING_COLORS[1][0])
        self.disk = Stat("Disk", RING_COLORS[2][0])
        self.spark = Sparkline(RING_COLORS[0][0])
        self.net = QLabel(objectName="muted")
        self.battery = QLabel(objectName="muted")

        stats = QHBoxLayout()
        stats.setSpacing(14)
        for s in (self.cpu, self.mem, self.disk):
            stats.addWidget(s)
        stats.addStretch()
        bottom = QHBoxLayout()
        bottom.setSpacing(10)
        bottom.addWidget(self.spark, 1)
        info = QVBoxLayout()
        info.setSpacing(0)
        info.addWidget(self.net)
        info.addWidget(self.battery)
        bottom.addLayout(info)
        right = QVBoxLayout()
        right.setSpacing(6)
        right.addLayout(stats)
        right.addLayout(bottom)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self.rings)
        row.addSpacing(12)
        row.addLayout(right, 1)

        self.sampler = QTimer(self)
        self.sampler.setInterval(1000)
        self.sampler.timeout.connect(self.sample)
        self.sampler.start()
        self.animator = QTimer(self)
        self.animator.setInterval(16)
        self.animator.timeout.connect(self.animate)
        self.sample()

    def sample(self):
        cpu = psutil.cpu_percent(None)
        mem = psutil.virtual_memory()
        try:
            disk = psutil.disk_usage(DISK).percent
        except OSError:
            disk = 0.0
        self.targets = [cpu / 100, mem.percent / 100, disk / 100]
        self.spark.push(cpu / 100)
        self.mem.setToolTip(f"{mem.used / 2**30:.1f} of {mem.total / 2**30:.1f} GB used")
        now, net = time.monotonic(), psutil.net_io_counters()
        dt = max(now - self.last_time, 0.001)
        down = (net.bytes_recv - self.last_net.bytes_recv) / dt
        up = (net.bytes_sent - self.last_net.bytes_sent) / dt
        self.last_net, self.last_time = net, now
        self.net.setText(f"↓ {fmt_speed(down)}   ↑ {fmt_speed(up)}")
        try:
            bat = psutil.sensors_battery()
        except Exception:
            bat = None
        if bat:
            self.battery.setText(f"{'Charging' if bat.power_plugged else 'Battery'} {bat.percent:.0f}%")
        else:
            up_h = (time.time() - psutil.boot_time()) / 3600
            self.battery.setText(f"Up {int(up_h)}h {int(up_h % 1 * 60)}m")
        if self.isVisible() and not self.animator.isActive():
            self.animator.start()

    def animate(self):
        done = True
        for i in range(3):
            diff = self.targets[i] - self.shown[i]
            if abs(diff) > 0.001:
                self.shown[i] += diff * 0.12
                done = False
            else:
                self.shown[i] = self.targets[i]
        self.rings.values = list(self.shown)
        self.rings.update()
        for stat, v in zip((self.cpu, self.mem, self.disk), self.shown):
            stat.value.setText(f"{v * 100:.0f}%")
        if done:
            self.animator.stop()

    def showEvent(self, e):
        self.shown = [0.0, 0.0, 0.0]
        self.animator.start()
        super().showEvent(e)

    def hideEvent(self, e):
        self.animator.stop()
        super().hideEvent(e)


# ======================= the island window =======================
def tray_icon():
    pm = QPixmap(64, 64)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("black"))
    p.drawRoundedRect(QRectF(2, 18, 60, 28), 14, 14)
    p.setBrush(QColor(GREEN))
    p.drawEllipse(QPointF(46, 32), 6, 6)
    p.end()
    return QIcon(pm)


class Island(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet(STYLE)
        self.state = "pill"          # 'full', 'pill' or 'line'
        self.notified = set()
        self.alert_glow = 0.0

        # collapsed pill
        self.mini = QWidget()
        ml = QHBoxLayout(self.mini)
        ml.setContentsMargins(18, 0, 18, 2)
        self.mini_left = QLabel()
        self.mini_left.setStyleSheet("font-weight: 700;")
        self.mini_right = QLabel(textFormat=Qt.RichText)
        ml.addWidget(self.mini_left); ml.addStretch(); ml.addWidget(self.mini_right)

        # expanded card
        self.full = QWidget()
        fl = QVBoxLayout(self.full)
        fl.setContentsMargins(16, 9, 16, 6)
        fl.setSpacing(6)
        header = QHBoxLayout()
        self.title_lbl = QLabel()
        self.title_lbl.setStyleSheet("font-size: 13px; font-weight: 700;")
        self.title_lbl.setFixedWidth(100)
        self.date_lbl = QLabel(objectName="muted")
        self.clock_lbl = QLabel()
        self.clock_lbl.setStyleSheet("font-weight: 700;")
        self.clock_lbl.setFixedWidth(100)
        self.clock_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        header.addWidget(self.title_lbl); header.addStretch()
        header.addWidget(self.date_lbl); header.addStretch(); header.addWidget(self.clock_lbl)

        self.prayer = PrayerPage()
        self.pomo = PomodoroPage()
        self.foot = FootballPage()
        self.system = SystemPage()
        self.stack = QStackedWidget()
        for page in (self.prayer, self.pomo, self.foot, self.system):
            self.stack.addWidget(page)
        left = AppleButton("left", "ghost", 24)
        right = AppleButton("right", "ghost", 24)
        left.clicked.connect(lambda: self.go(-1))
        right.clicked.connect(lambda: self.go(1))
        body = QHBoxLayout()
        body.setSpacing(6)
        body.addWidget(left); body.addWidget(self.stack, 1); body.addWidget(right)
        self.dots = QLabel(textFormat=Qt.RichText)
        self.dots.setAlignment(Qt.AlignCenter)
        fl.addLayout(header)
        fl.addLayout(body, 1)
        fl.addWidget(self.dots)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSizeConstraint(QLayout.SetNoConstraint)
        root.addWidget(self.mini)
        root.addWidget(self.full)
        self.full.hide()

        self.fade_fx = QGraphicsOpacityEffect(self.full)
        self.fade_fx.setOpacity(1.0)
        self.fade_fx.setEnabled(False)
        self.full.setGraphicsEffect(self.fade_fx)
        self.fade = QPropertyAnimation(self.fade_fx, b"opacity", self)
        self.fade.setDuration(220)
        self.fade.setEasingCurve(QEasingCurve.OutCubic)
        self.fade.finished.connect(lambda: self.fade_fx.setEnabled(False))

        self.anim = QPropertyAnimation(self, b"geometry", self)
        self.anim.finished.connect(self.anim_done)
        self.collapse_timer = QTimer(self)
        self.collapse_timer.setSingleShot(True)
        self.collapse_timer.timeout.connect(self.collapse)
        self.idle_timer = QTimer(self)
        self.idle_timer.setSingleShot(True)
        self.idle_timer.setInterval(IDLE_SECONDS * 1000)
        self.idle_timer.timeout.connect(self.to_line)
        self.glow_anim = anim(self, 900, self._set_glow, QEasingCurve.InOutSine)
        self.glow_anim.setLoopCount(6)
        self.glow_anim.setKeyValueAt(0.5, 1.0)

        # tray icon: native Windows notifications + menu
        self.tray = QSystemTrayIcon(tray_icon(), self)
        self.tray.setToolTip("Island")
        self.tray.setContextMenu(self.build_menu())
        self.tray.show()

        # data
        self.prayer_fetcher = PrayerFetcher()
        self.prayer_fetcher.done.connect(self.prayer.set_data)
        self.prayer_fetcher.fetch(force=True)
        self.fetcher = ScoreFetcher()
        self.fetcher.done.connect(self.foot.set_matches)
        self.fetcher.fetch()
        self.refresh = QTimer(self)
        self.refresh.setInterval(REFRESH_SECONDS * 1000)
        self.refresh.timeout.connect(self.fetcher.fetch)
        self.refresh.start()

        self.clock = QTimer(self)
        self.clock.setInterval(1000)
        self.clock.timeout.connect(self.update_clock)
        self.clock.start()

        self.setGeometry(self.rect_for(*COLLAPSED))
        self.go(0, animate=False)
        self.update_clock()
        self.idle_timer.start()

    def build_menu(self):
        menu = QMenu()
        menu.setStyleSheet(STYLE)
        self.remind_action = menu.addAction("Prayer reminders")
        self.remind_action.setCheckable(True)
        self.remind_action.setChecked(True)
        self.remind_action.triggered.connect(lambda: self.prayer.toggle_reminders())
        menu.addAction("Refresh", lambda: (self.fetcher.fetch(), self.prayer_fetcher.fetch(True)))
        menu.addSeparator()
        menu.addAction("Quit", QApplication.quit)
        return menu

    # --- geometry & animation ---
    def rect_for(self, w, h):
        screen = QApplication.primaryScreen().availableGeometry()
        return QRect(screen.x() + (screen.width() - w) // 2, screen.y(), w, h)

    def animate_to(self, size, opening):
        self.anim.stop()
        self.anim.setDuration(440 if opening else 260)
        curve = QEasingCurve(QEasingCurve.OutBack if opening else QEasingCurve.InOutCubic)
        if opening:
            curve.setOvershoot(1.0)
        self.anim.setEasingCurve(curve)
        self.anim.setStartValue(self.geometry())
        self.anim.setEndValue(self.rect_for(*size))
        self.anim.start()

    def fade_in(self, start=0.0):
        self.fade.stop()
        self.fade_fx.setEnabled(True)
        self.fade.setStartValue(start)
        self.fade.setEndValue(1.0)
        self.fade.start()

    @property
    def is_expanded(self):
        return self.state == "full"

    def expand(self):
        if self.state != "full":
            self.idle_timer.stop()
            self.state = "full"
            self.mini.hide()
            self.animate_to(EXPANDED, opening=True)

    def collapse(self):
        if self.state == "full":
            self.state = "pill"
            self.full.hide()
            self.animate_to(COLLAPSED, opening=False)
            self.idle_timer.start()

    def to_line(self):
        """Shrink the pill to a thin line, unless a prayer is a few minutes away."""
        if self.state == "pill" and not self.underMouse() and not self.prayer.mini_text()[1]:
            self.state = "line"
            self.mini.hide()
            self.animate_to(TINY, opening=False)

    def to_pill(self):
        if self.state == "line":
            self.state = "pill"
            self.animate_to(COLLAPSED, opening=True)

    def anim_done(self):
        if self.state == "full":
            self.full.show()
            self.fade_in()
        elif self.state == "pill":
            self.mini.show()

    def enterEvent(self, _):
        self.collapse_timer.stop()
        self.expand()

    def leaveEvent(self, _):
        self.collapse_timer.start(450)

    def _set_glow(self, v):
        self.alert_glow = float(v)
        self.update()

    # --- pages ---
    def go(self, delta, animate=True):
        idx = (self.stack.currentIndex() + delta) % self.stack.count()
        self.stack.setCurrentIndex(idx)
        self.title_lbl.setText(self.stack.currentWidget().title)
        dots = [f"<span style='color:{'white' if i == idx else '#48484a'}'>●</span>"
                for i in range(self.stack.count())]
        self.dots.setText("<span style='font-size:6px'>" + "&nbsp;&nbsp;".join(dots) + "</span>")
        self.update_header()
        if animate and self.is_expanded:
            self.fade_in(0.2)

    def wheelEvent(self, e):
        self.go(-1 if e.angleDelta().y() > 0 else 1)

    # --- prayer reminders ---
    def notify(self, title, body):
        self.tray.showMessage(title, body, QSystemTrayIcon.Information, 12000)
        beep()
        self.go(self.stack.indexOf(self.prayer) - self.stack.currentIndex(), animate=False)
        self.expand()
        self.collapse_timer.start(12000)           # stay open for 12 s unless you hover it
        self.glow_anim.stop()
        self.glow_anim.setStartValue(0.0)
        self.glow_anim.setEndValue(0.0)
        self.glow_anim.start()

    def check_prayers(self):
        if not self.prayer.data or not self.prayer.reminders:
            return
        now = datetime.datetime.now()
        for name, t in self.prayer.all_times():
            secs = (t - now).total_seconds()
            key = f"{t:%Y%m%d%H%M}"
            if 0 < secs <= REMIND_MINUTES * 60 and key + "pre" not in self.notified:
                self.notified.add(key + "pre")
                mins = math.ceil(secs / 60)
                self.notify(f"{name} in {mins} minutes",
                            f"{dict(PRAYERS)[name]}  ·  {name} at {t:%H:%M}")
            elif -60 < secs <= 0 and key + "now" not in self.notified:
                self.notified.add(key + "now")
                self.notify(f"It's time for {name}", f"{dict(PRAYERS)[name]}  ·  {t:%H:%M}")

    # --- clock & collapsed text ---
    def update_header(self):
        now = datetime.datetime.now()
        hijri = self.prayer.data["hijri"] if self.prayer.data else ""
        if self.stack.currentWidget() is self.prayer and hijri:
            self.date_lbl.setText(hijri)
        else:
            self.date_lbl.setText(now.strftime("%a %d %b %Y"))
        self.clock_lbl.setText(now.strftime("%H:%M"))

    def update_clock(self):
        now = datetime.datetime.now()
        if not self.prayer.data or self.prayer.data["date"] != now.date():
            self.prayer_fetcher.fetch()
        self.prayer.tick()
        self.check_prayers()
        self.remind_action.setChecked(self.prayer.reminders)
        self.update_header()
        prayer_text, soon = self.prayer.mini_text()
        if soon and self.state == "line":
            self.to_pill()                            # a prayer is close: show the pill again
        elif (self.state == "pill" and not soon and not self.idle_timer.isActive()
              and not self.underMouse() and self.anim.state() != QPropertyAnimation.Running):
            self.idle_timer.start()
        if self.state == "line" and self.pomo.running:
            self.update()                             # keep the Pomodoro progress on the line moving
        self.mini_left.setText(now.strftime("%H:%M"))
        self.mini_right.setText(self.pomo.status_text() if self.pomo.running and not soon
                                else (prayer_text if soon else
                                      self.foot.live_text() or prayer_text or now.strftime("%a %d %b")))
        self.mini.layout().invalidate()

    # --- menu & painting ---
    def contextMenuEvent(self, e):
        self.tray.contextMenu().exec(e.globalPos())

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        # t = 0 for the thin line, 1 for the pill and larger; blends shape and colour smoothly
        t = max(0.0, min(1.0, (h - TINY[1]) / (COLLAPSED[1] - TINY[1])))
        vis_h = h - (TINY[1] - 5) * (1 - t)          # the line itself is drawn 5 px tall
        if t < 1:
            p.fillRect(self.rect(), QColor(0, 0, 0, 1))   # invisible, but still catches the mouse
        r = min(24, vis_h / 2)
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, -r, w, vis_h + r), r, r)
        p.fillPath(path, blend("#5a5a5e", "#000000", t))
        if t < 1 and self.pomo.running:               # Pomodoro progress shows on the line
            done = 1 - self.pomo.left / self.pomo.total
            prog = QPainterPath()
            prog.addRoundedRect(QRectF(0, -r, max(vis_h, w * done), vis_h + r), r, r)
            c = QColor(self.pomo.MODES[self.pomo.mode_i][3])
            c.setAlpha(int(255 * (1 - t)))
            p.fillPath(prog, c)
        if self.alert_glow > 0.01:                   # soft green pulse during a reminder
            glow = QColor(GREEN)
            glow.setAlpha(int(200 * self.alert_glow))
            p.setPen(QPen(glow, 2))
            p.drawPath(path)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    island = Island()
    island.show()
    sys.exit(app.exec())

