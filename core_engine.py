#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Project: RON_CORE - Ultimate Tactical Linux Voice Assistant & Cyber Grid Daemon
Version: 18.0.0-PRO (Unified Refactor: Service Layer + CyberCanvas + Secure Terminal Execution)
Architecture: PyQt6 + SpeechRecognition + QThread Safety + Full System Binary Indexing
"""

import os
import sys

# ضمان العمل من أي مسار بالنظام
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir:
    os.chdir(script_dir)

os.environ["PYTHONWARNINGS"] = "ignore"
os.environ["PYTHONIOENCODING"] = "utf-8"

import math
import random
import threading
import subprocess
import webbrowser
import logging
import shutil
import tempfile
import re
import shlex
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple, Set, FrozenSet, Callable

from PyQt6.QtCore import Qt, QTimer, QPoint, QRectF, QThread, pyqtSignal, QObject
from PyQt6.QtGui import QFont, QColor, QPainter, QPen, QPainterPath
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, 
    QPushButton, QVBoxLayout, QHBoxLayout, QTextEdit, QDialog, QComboBox, QLineEdit
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)


class SystemConfig:
    APP_TITLE = "RON_CORE // TACTICAL DAEMON v18.0"
    WINDOW_WIDTH = 1024
    WINDOW_HEIGHT = 680
    FPS_INTERVAL = 16
    THEME_BG = QColor(2, 2, 6)
    THEME_ACCENT = QColor(0, 255, 136)
    NODE_COUNT = 950


# قائمة محطات الطرفية المتاحة في كالي لينكس (QTerminal كخيار افتراضي أول)
TERMINALS = [
    ("qterminal", "-e"),
    ("xfce4-terminal", "-e"),
    ("gnome-terminal", "--"),
    ("terminator", "-x"),
    ("lxterminal", "-e"),
    ("alacritty", "-e"),
    ("kitty", "--"),
    ("xterm", "-e"),
    ("x-terminal-emulator", "-e")
]


# ----------------------------------------------------------------------------- 
# Text Helpers & Binary Indexing
# -----------------------------------------------------------------------------
_FOLD = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي", "ة": "ه"})
_W, _WE = r"(?<!\w)", r"(?!\w)"


def spoken_fix(s: str) -> str:
    s = re.sub(rf"\s+{_W}(?:double dash|شرطتين){_WE}\s*", " --", s, flags=re.I)
    s = re.sub(rf"\s+{_W}(?:dash|minus|شرط[هة]){_WE}\s*", " -", s, flags=re.I)
    s = re.sub(rf"\s*{_W}(?:dot|نقط[هة]){_WE}\s*", ".", s, flags=re.I)
    s = re.sub(rf"\s*{_W}(?:slash|سلاش|سلش){_WE}\s*", "/", s, flags=re.I)
    return re.sub(rf"\s+{_W}(?:pipe|بايب){_WE}\s+", " | ", s, flags=re.I).strip()


def index_binaries() -> FrozenSet[str]:
    found = set()
    search_paths = ["/bin", "/sbin", "/usr/bin", "/usr/sbin", "/usr/local/bin", "/usr/local/sbin"]
    for path in search_paths:
        if os.path.isdir(path):
            try:
                for f in os.listdir(path):
                    full_path = os.path.join(path, f)
                    if os.access(full_path, os.X_OK) and not os.path.isdir(full_path):
                        found.add(f.lower())
            except Exception:
                pass
    return frozenset(found)


# ----------------------------------------------------------------------------- 
# Validators & Security
# -----------------------------------------------------------------------------
def _is_root() -> bool:
    return hasattr(os, "geteuid") and os.geteuid() == 0


def _text(v: str) -> str:
    v = v.strip()
    if not v:
        raise ValueError("required")
    return shlex.quote(v)


def _host(v: str, host_only: bool = False) -> str:
    v = v.strip()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.\-:/_?=&%@+,~#\[\]]*", v):
        raise ValueError("invalid IP / host / URL")
    if host_only:
        v = re.sub(r"^[a-z][a-z0-9+.\-]*://", "", v, flags=re.I).split("/")[0]
    return shlex.quote(v)


def _pkg(v: str) -> str:
    v = v.strip().lower()
    if not re.fullmatch(r"[a-z0-9][a-z0-9+.\-]*", v):
        raise ValueError("invalid package name")
    return v


def _user(v: str) -> str:
    v = (v.strip() or "root")
    if not re.fullmatch(r"[a-z_][a-z0-9_\-]*", v):
        raise ValueError("invalid user name")
    return v


# ----------------------------------------------------------------------------- 
# Data Models & Command Service
# -----------------------------------------------------------------------------
@dataclass(frozen=True)
class Field:
    key: str
    label: str
    default: str = ""


@dataclass(frozen=True)
class Action:
    id: str
    title: str
    triggers: Tuple[str, ...]
    fields: Tuple[Field, ...] = ()
    build: Callable[[Dict[str, str]], str] = lambda v: ""
    confirm: str = ""


@dataclass
class Plan:
    kind: str  # ui | form | run | none
    ui: str = ""
    action: Optional[Action] = None
    values: Dict[str, str] = field(default_factory=dict)
    command: str = ""
    label: str = ""


def _f(key: str, label: str, default: str = "") -> Field:
    return Field(key, label, default)


ACTIONS: Tuple[Action, ...] = (
    Action("poweroff", "POWER OFF", ("اغلاق النظام", "ايقاف التشغيل", "اطفاء الجهاز", "poweroff", "shutdown"),
           build=lambda v: "sudo systemctl poweroff", confirm="هل أنت متأكد من إطفاء النظام؟"),
    Action("reboot", "REBOOT", ("اعاده تشغيل", "reboot"),
           build=lambda v: "sudo systemctl reboot", confirm="هل أنت متأكد من إعادة تشغيل الجهاز؟"),
    Action("install", "INSTALL PACKAGE", ("تثبيت حزمه", "تثبيت برنامج", "تحميل برنامج", "تثبيت", "install"),
           (_f("pkg", "اسم الحزمة (Package Name):"),),
           lambda v: f"sudo apt update && sudo apt install -y {_pkg(v['pkg'])}"),
    Action("update", "UPDATE SYSTEM", ("تحديث النظام", "تحديث الحزم"), (),
           lambda v: "sudo apt update && sudo apt upgrade -y"),
    Action("nmap", "NETWORK SCAN (NMAP)", ("فحص شبكه", "فحص المنافذ", "افحص", "فحص", "اسكن", "scan", "انماب", "nmap"),
           (_f("target", "IP الهدف أو الرابط (Target IP/URL):"),),
           lambda v: ("" if _is_root() else "sudo ") + f"nmap -sS -T4 {_host(v['target'], True)}"),
    Action("ping", "PING", ("بنج", "بنغ", "ping"),
           (_f("target", "IP أو الموقع (Target IP/Domain):"),),
           lambda v: f"ping -c 4 {_host(v['target'], True)}"),
    Action("mkdir", "CREATE DIRECTORY", ("انشاء مجلد", "عمل مجلد", "مجلد جديد", "فلدر"),
           (_f("name", "اسم المجلد (Directory Name):"),), lambda v: f"mkdir -p -- {_text(v['name'])}"),
    Action("touch", "CREATE FILE", ("انشاء ملف", "عمل ملف", "ملف جديد", "فايل"),
           (_f("name", "اسم الملف مع الامتداد (File Name):"),), lambda v: f"touch -- {_text(v['name'])}"),
    Action("nano", "EDIT FILE", ("تعديل ملف", "فتح نانو", "نانو", "nano"),
           (_f("path", "اسم أو مسار الملف (File Path):"),), lambda v: f"nano -- {_text(v['path'])}"),
    Action("kernel", "KERNEL", ("معلومات الكيرنل", "اصدار النواه"), (), lambda v: "uname -r"),
    Action("cpu", "CPU", ("معلومات المعالج", "بروسيسور"), (), lambda v: "lscpu"),
    Action("mem", "MEMORY", ("استهلاك الذاكره", "الرامات"), (), lambda v: "free -h"),
    Action("disk", "DISK", ("مساحه الهارد", "التخزين"), (), lambda v: "df -h"),
    Action("lsblk", "BLOCK DEVICES", ("عرض الاقراص", "lsblk"), (), lambda v: "lsblk"),
    Action("ls", "LIST FILES", ("عرض الملفات", "اعرض الملفات", "^ملفات$"), (), lambda v: "ls -la"),
    Action("pwd", "PWD", ("المسار الحالي", "اين انا"), (), lambda v: "pwd"),
    Action("ip", "IP ADDRESSES", ("عنوان الايب", "شبكتي", "ip a"), (), lambda v: "ip a"),
)

SU_ACTION = Action("su", "ROOT SU TERMINAL", (), (_f("user", "اسم المستخدم (Username):", "root"),),
                   lambda v: f"echo '--- su ---'; su - {_user(v['user'])}")

EXIT_WORDS = {"خروج", "اغلاق الواجهه", "توقف", "stop", "exit", "quit"}
CLEAR_WORDS = {"مسح الشاشه", "تطهير", "clear"}
BROWSER_WORDS = {"فتح المتصفح", "open browser"}
ALIASES = {"انماب": "nmap", "نمب": "nmap", "هيدرا": "hydra", "نيكتو": "nikto", "جوبستر": "gobuster",
           "سكل ماب": "sqlmap", "هاشكات": "hashcat", "ميتاسبلويت": "msfconsole", "كيرل": "curl"}
SHORT_OK = frozenset({"ls", "ps", "df", "du", "id", "ip", "ss", "nc", "w"})
AMBIGUOUS = frozenset({"yes", "test", "time", "who", "man", "look", "write", "talk", "wall", "last", "at", "as",
                       "on", "it", "do", "go", "see", "can", "now", "new", "not", "for", "off", "out", "more",
                       "less", "sort", "join", "head", "tail", "read", "stop", "install", "which", "watch"})
ASK_ARGS = frozenset({"nmap", "hydra", "sqlmap", "nikto", "gobuster", "hashcat", "john", "curl", "wget", "dig",
                      "whois", "traceroute", "find", "grep", "cat", "cp", "mv", "rm", "tcpdump", "tshark"})

_RUN_PREFIX = re.compile(r"^(?:نفذ|شغل|run|execute|exec)\s+(.+)$", re.I)
_TERMINAL = re.compile(r"(?<!\w)(?:فتح تيرمنال|فتح موجه|تيرمنال|terminal)(?!\w)", re.I)
_ROOT = re.compile(r"جذر|(?<!\w)(?:root|su)(?!\w)", re.I)
_OPTION = re.compile(r"(?:^|\s)-{1,2}[A-Za-z]")
_NOISE = re.compile(r"^(?:(?:ip|ايبي|ايب|اي بي|عنوان|موقع|هدف|المنافذ|منافذ|شبكه|host|ports?|target|the|on|for|الى|على|ال)(?:\s+|$))+", re.I)


class CommandService:
    def __init__(self, binaries: Optional[FrozenSet[str]] = None) -> None:
        self.bins = index_binaries() if binaries is None else binaries
        self._compiled: List[Tuple[Action, "re.Pattern[str]"]] = [
            (a, re.compile("|".join(t if t.startswith("^") else rf"{_W}{re.escape(t)}{_WE}" for t in a.triggers), re.I))
            for a in ACTIONS
        ]

    def resolve(self, text: str) -> Plan:
        clean = " ".join(text.split())
        if not clean:
            return Plan("none")
        folded = clean.translate(_FOLD)
        low = folded.lower()

        if low in EXIT_WORDS:
            return Plan("ui", ui="exit")
        if low in CLEAR_WORDS:
            return Plan("ui", ui="clear")
        if low in BROWSER_WORDS:
            return Plan("ui", ui="browser")
        if _TERMINAL.search(folded):
            if _ROOT.search(folded):
                return Plan("form", action=SU_ACTION, values={"user": "root"})
            return Plan("run", command="exec bash", label="USER TERMINAL")

        m = _RUN_PREFIX.match(folded)
        if m:
            return Plan("run", command=spoken_fix(clean[m.start(1):]), label="RUN")

        if not _OPTION.search(spoken_fix(clean)):
            for action, pattern in self._compiled:
                hit = pattern.search(folded)
                if hit:
                    return self._from_action(action, clean[hit.end():].strip())
        return self._direct(clean)

    def build(self, action: Action, values: Dict[str, str]) -> str:
        return action.build({f.key: (values.get(f.key) or f.default).strip() for f in action.fields})

    def _from_action(self, action: Action, rest: str) -> Plan:
        values: Dict[str, str] = {f.key: f.default for f in action.fields}
        noise = _NOISE.match(rest.translate(_FOLD))
        rest = rest[noise.end():].strip() if noise else rest
        if rest and len(action.fields) == 1:
            values[action.fields[0].key] = spoken_fix(" " + rest)
        if all(values[f.key] for f in action.fields):
            try:
                return Plan("run", command=self.build(action, values), action=action, label=action.title)
            except ValueError:
                pass
        return Plan("form", action=action, values=values)

    def _resolve_name(self, words: List[str]) -> Tuple[str, int]:
        for n in (2, 1):
            key = " ".join(words[:n]).translate(_FOLD).lower()
            if len(words) >= n and key in ALIASES:
                return ALIASES[key], n
        w = words[0]
        return (w, 1) if w in self.bins else ((w.lower(), 1) if w.lower() in self.bins else ("", 0))

    def _runnable(self, name: str) -> bool:
        if name not in self.bins or name in AMBIGUOUS:
            return False
        return len(name) > 2 or name in SHORT_OK

    def _direct(self, clean: str) -> Plan:
        body = spoken_fix(clean)
        words = body.split()
        if not words:
            return Plan("none")
        name, used = self._resolve_name(words)
        if not name or not self._runnable(name):
            return Plan("none")
        rest = body.split(None, used)[used] if len(words) > used else ""
        if not rest and name in ASK_ARGS:
            act = Action(f"exec:{name}", f"EXECUTE: {name.upper()}", (), (_f("args", f"معاملات {name} (Arguments):"),),
                         lambda v, n=name: f"{n} {v['args']}".strip())
            return Plan("form", action=act, values={"args": ""})
        return Plan("run", command=f"{name} {rest}".strip(), label=name.upper())


# ----------------------------------------------------------------------------- 
# CyberNode & CyberCanvas (الشبكة العصبية البصرية والـ Morphing)
# -----------------------------------------------------------------------------
class CyberNode:
    def __init__(self, x: float, y: float, max_w: float, max_h: float) -> None:
        self.x = x
        self.y = y
        self.base_x = x
        self.base_y = y
        self.target_x = x
        self.target_y = y
        self.norm_x = x / max_w if max_w > 0 else x
        self.norm_y = y / max_h if max_h > 0 else y
        self.speed = 0.08

    def update_normalization(self, max_w: float, max_h: float) -> None:
        if max_w > 0 and max_h > 0:
            self.base_x = self.norm_x * max_w
            self.base_y = self.norm_y * max_h

    def update_idle(self, time_val: float) -> None:
        wave1 = math.sin(time_val * 0.8 + self.base_x * 0.005) * 25
        wave2 = math.cos(time_val * 0.6 + self.base_y * 0.005) * 20
        self.target_x = self.base_x + wave1
        self.target_y = self.base_y + wave2
        self.x += (self.target_x - self.x) * self.speed
        self.y += (self.target_y - self.y) * self.speed

    def update_morph(self) -> None:
        self.x += (self.target_x - self.x) * (self.speed * 1.6)
        self.y += (self.target_y - self.y) * (self.speed * 1.6)


class CyberCanvas(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.nodes: List[CyberNode] = []
        self.phase = 0.0
        self.is_active = False
        self.is_morphed = False
        self.active_color = SystemConfig.THEME_ACCENT
        self.display_text = "STANDBY"
        self.display_cmd = ""
        self._init_nodes(SystemConfig.NODE_COUNT)
        
        self.render_timer = QTimer(self)
        self.render_timer.timeout.connect(self._animate_frame)
        self.render_timer.start(SystemConfig.FPS_INTERVAL)

    def _init_nodes(self, count: int) -> None:
        self.nodes.clear()
        w = max(self.width(), SystemConfig.WINDOW_WIDTH)
        h = max(self.height(), SystemConfig.WINDOW_HEIGHT)
        for _ in range(count):
            rx = random.uniform(50, w - 50)
            ry = random.uniform(50, h - 50)
            self.nodes.append(CyberNode(rx, ry, w, h))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        w, h = self.width(), self.height()
        for node in self.nodes:
            node.update_normalization(w, h)

    def _animate_frame(self) -> None:
        self.phase += 0.03
        for node in self.nodes:
            if not self.is_morphed:
                node.update_idle(self.phase)
            else:
                node.update_morph()
        self.update()

    def set_active(self, state: bool) -> None:
        self.is_active = state
        if not state:
            self.is_morphed = False
            self.active_color = SystemConfig.THEME_ACCENT
            self.display_text = "STANDBY"
            self.display_cmd = ""

    def morph_to_command(self, voice_text: str, sys_cmd: str) -> None:
        self.is_morphed = True
        self.display_text = voice_text
        self.display_cmd = sys_cmd.upper()
        
        cmd_lower = sys_cmd.lower()
        if "apt" in cmd_lower or "update" in cmd_lower or "install" in cmd_lower:
            self.active_color = QColor(0, 150, 255)
        elif "nmap" in cmd_lower or "ping" in cmd_lower or "netstat" in cmd_lower:
            self.active_color = QColor(255, 140, 0)
        elif "poweroff" in cmd_lower or "shutdown" in cmd_lower or "reboot" in cmd_lower or "rm" in cmd_lower:
            self.active_color = QColor(255, 51, 85)
        elif "ls" in cmd_lower or "mkdir" in cmd_lower or "nano" in cmd_lower or "touch" in cmd_lower:
            self.active_color = QColor(0, 255, 136)
        else:
            self.active_color = QColor(190, 90, 255)

        w, h = self.width(), self.height()
        path = QPainterPath()
        path.addText(0, 0, QFont('Consolas', 48, QFont.Weight.Bold), self.display_cmd[:28])
        rect = path.boundingRect()
        
        scale_x = (w * 0.7) / rect.width() if rect.width() > 0 else 1.0
        scale_y = (h * 0.5) / rect.height() if rect.height() > 0 else 1.0
        scale = min(scale_x, scale_y, 2.0)
        
        center_x = (w - rect.width() * scale) / 2 - rect.x() * scale
        center_y = (h - rect.height() * scale) / 2 - rect.y() * scale

        sample_points = []
        for i in range(len(self.nodes)):
            t = i / len(self.nodes)
            pt = path.pointAtPercent(t)
            nx = pt.x() * scale + center_x
            ny = pt.y() * scale + center_y
            sample_points.append((nx, ny))

        random.shuffle(sample_points)
        for idx, node in enumerate(self.nodes):
            target = sample_points[idx % len(sample_points)]
            node.target_x = target[0] + random.uniform(-1.5, 1.5)
            node.target_y = target[1] + random.uniform(-1.5, 1.5)

        QTimer.singleShot(3500, self._reset_morph)

    def _reset_morph(self) -> None:
        self.is_morphed = False
        self.active_color = SystemConfig.THEME_ACCENT

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), SystemConfig.THEME_BG)

        color = self.active_color if self.is_active else QColor(0, 150, 210, 100)
        
        for node in self.nodes:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawEllipse(int(node.x) - 2, int(node.y) - 2, 4, 4)

        for i in range(0, len(self.nodes), 12):
            n1 = self.nodes[i]
            n2 = self.nodes[(i + 1) % len(self.nodes)]
            dist = math.hypot(n1.x - n2.x, n1.y - n2.y)
            if dist < 45:
                alpha = int((1 - dist / 45) * 70)
                line_color = QColor(color.red(), color.green(), color.blue(), alpha)
                painter.setPen(QPen(line_color, 0.8))
                painter.drawLine(int(n1.x), int(n1.y), int(n2.x), int(n2.y))

        painter.setPen(QColor(255, 255, 255, 70))
        painter.setFont(QFont('Consolas', 10))
        status_str = "CYBER_GRID: ACTIVE // ULTIMATE DAEMON v18" if self.is_active else "CYBER_GRID: STANDBY"
        painter.drawText(25, 35, status_str)
        
        if self.is_morphed:
            painter.setPen(self.active_color)
            painter.setFont(QFont('Consolas', 18, QFont.Weight.Bold))
            painter.drawText(QRectF(0, self.height() / 2 - 90, self.width(), 45), Qt.AlignmentFlag.AlignCenter, f">> [{self.display_cmd}] <<")
            
            painter.setPen(QColor(255, 255, 255, 220))
            painter.setFont(QFont('Arial', 12))
            painter.drawText(QRectF(0, self.height() / 2 + 35, self.width(), 35), Qt.AlignmentFlag.AlignCenter, f"({self.display_text})")


# ----------------------------------------------------------------------------- 
# Terminal Launcher & Voice Listener
# -----------------------------------------------------------------------------
class TerminalLauncher:
    CANDIDATES = ("qterminal", "xfce4-terminal", "gnome-terminal", "terminator", "lxterminal",
                  "alacritty", "kitty", "xterm", "x-terminal-emulator")

    def __init__(self, cwd: str = os.path.expanduser("~")) -> None:
        self.cwd = cwd

    @staticmethod
    def _argv(term: str, script: str) -> List[str]:
        if term in ("qterminal", "xfce4-terminal", "lxterminal"):
            return [term, "-e", f"bash {shlex.quote(script)}"]
        if term == "gnome-terminal":
            return [term, "--", "bash", script]
        if term == "kitty":
            return [term, "bash", script]
        if term == "terminator":
            return [term, "-x", "bash", script]
        return [term, "-e", "bash", script]

    def run(self, command: str) -> bool:
        fd, path = tempfile.mkstemp(prefix="ron_", suffix=".sh")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write("#!/bin/bash\n"
                     "trap 'rm -f -- \"$0\"' EXIT\n"
                     "echo '--- RON_CORE // TACTICAL EXECUTION ---'\n"
                     f"printf '$ %s\\n' {shlex.quote(command)}\n"
                     "echo '---------------------------------------'\n"
                     f"{command}\n"
                     "echo; read -r -p '[اضغط Enter أو أغلق النافذة للإنهاء] '\n")
        os.chmod(path, 0o700)
        for term in self.CANDIDATES:
            if shutil.which(term):
                try:
                    subprocess.Popen(self._argv(term, path), cwd=self.cwd, start_new_session=True)
                    return True
                except OSError:
                    continue
        os.unlink(path)
        return False


class VoiceListener(QObject):
    heard = pyqtSignal(str)
    log = pyqtSignal(str)
    CODES = {"ar": ["ar-IQ"], "en": ["en-US"], "auto": ["ar-IQ", "en-US"]}

    def __init__(self, lang: str, probe: Callable[[str], bool]) -> None:
        super().__init__()
        self.codes, self.probe, self._stop = self.CODES.get(lang, ["ar-IQ"]), probe, None
        self._on = False

    def start(self) -> None:
        self._on = True
        threading.Thread(target=self._boot, daemon=True).start()

    def stop(self) -> None:
        self._on = False
        if self._stop:
            self._stop(wait_for_stop=False)
            self._stop = None

    def _boot(self) -> None:
        import speech_recognition as sr
        self._sr = sr
        try:
            rec, mic = sr.Recognizer(), sr.Microphone()
            rec.pause_threshold, rec.non_speaking_duration, rec.phrase_threshold = 0.55, 0.35, 0.25
            with mic as source:
                rec.adjust_for_ambient_noise(source, duration=0.6)
        except (OSError, AttributeError) as err:
            self.log.emit(f"[-] Microphone unavailable: {err}")
            return
        if self._on:
            self._stop = rec.listen_in_background(mic, self._on_audio, phrase_time_limit=9)
            self.log.emit(f"[~] Listening [{', '.join(self.codes)}]...")

    def _on_audio(self, rec, audio) -> None:
        best = ""
        for code in self.codes:
            try:
                text = rec.recognize_google(audio, language=code).strip()
            except self._sr.UnknownValueError:
                continue
            except self._sr.RequestError as err:
                self.log.emit(f"[-] Speech service error: {err}")
                return
            best = best or text
            if self.probe(text):
                best = text
                break
        if best:
            self.heard.emit(best)


# ----------------------------------------------------------------------------- 
# UI Dialogs & Main Core Engine
# -----------------------------------------------------------------------------
INPUT_QSS = ("QLineEdit, QComboBox { background-color:#0c0c12; color:#00ffc8; border:1px solid #232332; padding:8px;"
             " font-family:'Consolas'; font-size:11pt; } QLineEdit:focus { border:1px solid #00ffc8; }")


def button_qss(primary: bool = False) -> str:
    bg, fg, border = ("#ff3333", "#040408", "none") if primary else ("#1a1a24", "#d0d0d8", "1px solid #333345")
    return (f"QPushButton {{ background-color:{bg}; color:{fg}; border:{border}; font-family:'Consolas';"
            f" font-weight:bold; }} QPushButton:hover {{ background-color:{'#ff5555' if primary else '#2a2a3a'}; }}")


class DarkDialog(QDialog):
    def __init__(self, title: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"RON_CORE // {title}")
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)
        self.setStyleSheet("QDialog { background-color:#04040a; border:1px solid #ff3333; } QLabel { color:#d0d0d8; }"
                           + INPUT_QSS)
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(25, 22, 25, 22)
        head = QLabel(title)
        head.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
        head.setStyleSheet("color:#ff3333;")
        self.lay.addWidget(head)

    def buttons(self, ok_text: str, ok_slot: Callable[[], None]) -> QPushButton:
        row = QHBoxLayout()
        cancel, ok = QPushButton("CANCEL / إلغاء"), QPushButton(ok_text)
        for b, primary in ((cancel, False), (ok, True)):
            b.setFixedHeight(40)
            b.setStyleSheet(button_qss(primary))
            row.addWidget(b)
        cancel.clicked.connect(self.reject)
        ok.clicked.connect(ok_slot)
        self.lay.addLayout(row)
        return ok


class LanguageDialog(DarkDialog):
    def __init__(self) -> None:
        super().__init__("LINGO_GATEWAY")
        self.setFixedWidth(460)
        self.lay.addWidget(QLabel("Select recognition language / اختر لغة التعرف على الصوت:"))
        self.combo = QComboBox()
        for label, code in (("العربية (Iraqi Arabic)", "ar"), ("English (US)", "en"),
                            ("Auto: Arabic + English", "auto")):
            self.combo.addItem(label, code)
        self.lay.addWidget(self.combo)
        self.buttons("START / بدء", self.accept)

    @property
    def language(self) -> str:
        return self.combo.currentData()


class FormDialog(DarkDialog):
    def __init__(self, action: Action, values: Dict[str, str], service: CommandService, parent: QWidget) -> None:
        super().__init__(action.title, parent)
        self.action, self.service = action, service
        self.setMinimumWidth(520)
        self.edits: Dict[str, QLineEdit] = {}
        for f in action.fields:
            self.lay.addWidget(QLabel(f.label))
            edit = QLineEdit(values.get(f.key) or f.default)
            edit.textChanged.connect(self._refresh)
            edit.returnPressed.connect(self._submit)
            self.lay.addWidget(edit)
            self.edits[f.key] = edit
        self.preview = QLabel()
        self.preview.setWordWrap(True)
        self.lay.addWidget(self.preview)
        self.run_btn = self.buttons("EXECUTE / تنفيذ", self._submit)
        self._refresh()
        next((e for e in self.edits.values() if not e.text()), next(iter(self.edits.values()), self)).setFocus()

    def values_dict(self) -> Dict[str, str]:
        return {k: e.text().strip() for k, e in self.edits.items()}

    def _refresh(self) -> None:
        try:
            cmd = self.service.build(self.action, self.values_dict())
            self.preview.setText(f"$ {cmd}")
            self.preview.setStyleSheet("color:#00ffc8; font-family:'Consolas';")
            self.run_btn.setEnabled(True)
        except ValueError as err:
            self.preview.setText(f"! {err}")
            self.preview.setStyleSheet("color:#ffb347; font-family:'Consolas';")
            self.run_btn.setEnabled(False)

    def _submit(self) -> None:
        if self.run_btn.isEnabled():
            self.accept()


class ConfirmDialog(DarkDialog):
    def __init__(self, command: str, warning: str, parent: QWidget) -> None:
        super().__init__("CONFIRMATION", parent)
        self.setFixedWidth(480)
        msg = QLabel(f"{warning}\n\n$ {command}")
        msg.setWordWrap(True)
        self.lay.addWidget(msg)
        self.buttons("CONFIRM / تأكيد", self.accept)


class CoreEngine(QMainWindow):
    def __init__(self, lang: str = "ar") -> None:
        super().__init__()
        self.lang = lang
        self.service = CommandService()
        self.terminal = TerminalLauncher()
        self.voice: Optional[VoiceListener] = None
        self._drag = QPoint()
        self._build_ui()

    def _build_ui(self) -> None:
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.resize(SystemConfig.WINDOW_WIDTH, SystemConfig.WINDOW_HEIGHT)
        self.canvas = CyberCanvas(self)
        self.setCentralWidget(self.canvas)
        lay = QVBoxLayout(self.canvas)
        lay.setContentsMargins(18, 18, 18, 18)

        top = QHBoxLayout()
        title = QLabel(f"RON_CORE // TACTICAL DAEMON v18 [{self.lang.upper()}]")
        title.setStyleSheet("color:#ff3333; font-weight:bold; font-size:10pt; font-family:'Consolas'; background:transparent;")
        top.addWidget(title)
        top.addStretch()
        for text, slot in (("—", self.showMinimized), ("□", self._toggle_max), ("×", self.close)):
            b = QPushButton(text)
            b.setFixedSize(32, 28)
            b.setStyleSheet(button_qss())
            b.clicked.connect(slot)
            top.addWidget(b)
        lay.addLayout(top)
        lay.addStretch()

        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setFixedHeight(150)
        self.console.setStyleSheet("background-color:rgba(2,2,6,230); color:#00ff88; border:1px solid rgba(20,20,35,230);"
                                   " font-family:'Consolas','Courier New',monospace; font-size:9.5pt;")
        self.log(f"[+] RON_CORE v18 online - {len(self.service.bins)} executables indexed.\n")
        lay.addWidget(self.console)

        self.cmdbar = QLineEdit()
        self.cmdbar.setPlaceholderText("type a command or phrase + Enter (e.g. scan 192.168.1.1)")
        self.cmdbar.setStyleSheet(INPUT_QSS)
        self.cmdbar.returnPressed.connect(self._typed)
        lay.addWidget(self.cmdbar)

        row = QHBoxLayout()
        self.mic_btn = QPushButton("INITIALIZE STREAM")
        self.mic_btn.setFixedHeight(38)
        self.mic_btn.setStyleSheet(button_qss())
        self.mic_btn.clicked.connect(self.toggle_listening)
        purge = QPushButton("PURGE LOGS")
        purge.setFixedSize(140, 38)
        purge.setStyleSheet(button_qss())
        purge.clicked.connect(self.console.clear)
        row.addWidget(self.mic_btn)
        row.addWidget(purge)
        lay.addLayout(row)

    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag = e.globalPosition().toPoint()

    def mouseMoveEvent(self, e) -> None:
        if e.buttons() == Qt.MouseButton.LeftButton and not self.isMaximized():
            cur = e.globalPosition().toPoint()
            self.move(self.pos() + (cur - self._drag))
            self._drag = cur

    def closeEvent(self, e) -> None:
        if self.voice:
            self.voice.stop()
        super().closeEvent(e)

    def _toggle_max(self) -> None:
        self.showNormal() if self.isMaximized() else self.showMaximized()

    def log(self, text: str) -> None:
        self.console.append(text)

    def toggle_listening(self) -> None:
        if self.voice is None:
            self.voice = VoiceListener(self.lang, lambda t: self.service.resolve(t).kind != "none")
            self.voice.heard.connect(self.handle_text)
            self.voice.log.connect(self.log)
            self.voice.start()
            self.canvas.set_active(True)
            self.mic_btn.setText("TERMINATE STREAM")
            self.mic_btn.setStyleSheet(button_qss(True))
        else:
            self.voice.stop()
            self.voice = None
            self.canvas.set_active(False)
            self.mic_btn.setText("INITIALIZE STREAM")
            self.mic_btn.setStyleSheet(button_qss())
            self.log("[-] Stream closed.\n")

    def _typed(self) -> None:
        text = self.cmdbar.text().strip()
        self.cmdbar.clear()
        self.handle_text(text)

    def handle_text(self, text: str) -> None:
        if not text:
            return
        self.log(f"[>] {text}")
        plan = self.service.resolve(text)
        if plan.kind == "ui":
            self._ui(plan, text)
        elif plan.kind == "form":
            self._form(plan, text)
        elif plan.kind == "run":
            self._launch(plan.command, text, plan.label, plan.action)
        else:
            self.log("[?] Not understood - try a tool name or: نفذ <command>")

    def _ui(self, plan: Plan, text: str) -> None:
        self.canvas.morph_to_command(text, plan.ui)
        if plan.ui == "exit":
            QTimer.singleShot(1000, self.close)
        elif plan.ui == "clear":
            self.console.clear()
        elif plan.ui == "browser":
            webbrowser.open("https://www.google.com")

    def _form(self, plan: Plan, text: str) -> None:
        assert plan.action is not None
        dlg = FormDialog(plan.action, plan.values, self.service, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            self.log("[*] Cancelled.")
            return
        try:
            command = self.service.build(plan.action, dlg.values_dict())
        except ValueError as err:
            self.log(f"[-] {err}")
            return
        self._launch(command, text, plan.action.title, plan.action)

    def _launch(self, command: str, voice: str, label: str, action: Optional[Action]) -> None:
        self.canvas.morph_to_command(voice, command if len(command) <= 28 else label)
        self.log(f"[+] $ {command}")
        if not self.terminal.run(command):
            self.log("[-] No terminal emulator found (install qterminal or xterm).")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    lang_dialog = LanguageDialog()
    if lang_dialog.exec() == QDialog.DialogCode.Accepted:
        window = CoreEngine(lang_dialog.language)
        window.show()
        sys.exit(app.exec())
    else:
        sys.exit(0)
