#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Project: RON_CORE - Ultimate Tactical Linux Voice Assistant & Cyber Grid Daemon
Version: 12.0.0-PRO (Final Stable Architecture)
Architecture: PyQt6 + SpeechRecognition + Synchronous Real-time CLI Pipeline
"""

import os
import sys

os.environ["PYTHONWARNINGS"] = "ignore"
os.environ["PYTHONIOENCODING"] = "utf-8"

import math
import random
import threading
import subprocess
import webbrowser
import logging
import re
from typing import Optional, List

from PyQt6.QtCore import Qt, QTimer, QPoint, QRectF
from PyQt6.QtGui import QFont, QColor, QPainter, QPen, QPainterPath
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, 
    QPushButton, QVBoxLayout, QHBoxLayout, QTextEdit, QDialog, QComboBox
)
import speech_recognition as sr

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)


class SystemConfig:
    APP_TITLE = "RON_CORE // TACTICAL DAEMON v12.0"
    WINDOW_WIDTH = 1024
    WINDOW_HEIGHT = 680
    FPS_INTERVAL = 20
    THEME_BG = QColor(2, 2, 6)
    THEME_ACCENT = QColor(0, 255, 136)
    NODE_COUNT = 500


class LanguageSelectorDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.selected_lang: str = "ar"
        self._init_ui()

    def _init_ui(self) -> None:
        self.setWindowTitle("RON_CORE // SELECT LANGUAGE")
        self.setFixedSize(440, 240)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setStyleSheet("background-color: #04040a; color: #00ff88; border: 1px solid #ff3333;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)

        title_label = QLabel("RON_CORE_V12 // LINGO_GATEWAY")
        title_label.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #ff3333; border: none;")
        layout.addWidget(title_label)

        sub_label = QLabel("Select Operational Language / اختر لغة التشغيل:")
        sub_label.setFont(QFont("Arial", 10))
        sub_label.setStyleSheet("color: #d0d0d8; border: none;")
        layout.addWidget(sub_label)

        self.lang_combo = QComboBox()
        self.lang_combo.addItem("العربية (Arabic)", "ar")
        self.lang_combo.addItem("English (English)", "en")
        self.lang_combo.setStyleSheet("""
            QComboBox {
                background-color: #0c0c12;
                color: #00ff88;
                border: 1px solid #232332;
                padding: 8px;
                font-family: 'Consolas';
                font-size: 11pt;
            }
            QComboBox::drop-down { border: 0px; }
        """)
        layout.addWidget(self.lang_combo)

        layout.addStretch()

        start_btn = QPushButton("INITIALIZE SYSTEM")
        start_btn.setFixedHeight(42)
        start_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff3333;
                color: #040408;
                font-family: 'Consolas';
                font-weight: bold;
                font-size: 11pt;
                border: none;
            }
            QPushButton:hover {
                background-color: #ff5555;
            }
        """)
        start_btn.clicked.connect(self._accept_selection)
        layout.addWidget(start_btn)

    def _accept_selection(self) -> None:
        self.selected_lang = self.lang_combo.currentData()
        self.accept()


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
        elif "nmap" in cmd_lower or "ping" in cmd_lower:
            self.active_color = QColor(255, 128, 0)
        elif "poweroff" in cmd_lower or "shutdown" in cmd_lower or "reboot" in cmd_lower or "rm" in cmd_lower:
            self.active_color = QColor(255, 51, 51)
        elif "ls" in cmd_lower or "mkdir" in cmd_lower or "nano" in cmd_lower or "touch" in cmd_lower:
            self.active_color = QColor(0, 255, 136)
        else:
            self.active_color = QColor(180, 80, 255)

        w, h = self.width(), self.height()
        
        path = QPainterPath()
        path.addText(0, 0, QFont('Consolas', 48, QFont.Weight.Bold), self.display_cmd[:24])
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
            painter.drawEllipse(int(node.x) - 2, int(node.y) - 2, 5, 5)

        for i in range(0, len(self.nodes), 10):
            n1 = self.nodes[i]
            n2 = self.nodes[(i + 1) % len(self.nodes)]
            dist = math.hypot(n1.x - n2.x, n1.y - n2.y)
            if dist < 55:
                alpha = int((1 - dist / 55) * 85)
                line_color = QColor(color.red(), color.green(), color.blue(), alpha)
                painter.setPen(QPen(line_color, 0.8))
                painter.drawLine(int(n1.x), int(n1.y), int(n2.x), int(n2.y))

        painter.setPen(QColor(255, 255, 255, 60))
        painter.setFont(QFont('Consolas', 10))
        status_str = "CYBER_GRID: ACTIVE // ULTIMATE DAEMON" if self.is_active else "CYBER_GRID: STANDBY"
        painter.drawText(25, 35, status_str)
        
        if self.is_morphed:
            painter.setPen(self.active_color)
            painter.setFont(QFont('Consolas', 18, QFont.Weight.Bold))
            painter.drawText(QRectF(0, self.height() / 2 - 90, self.width(), 45), Qt.AlignmentFlag.AlignCenter, f">> [{self.display_cmd}] <<")
            
            painter.setPen(QColor(255, 255, 255, 220))
            painter.setFont(QFont('Arial', 12))
            painter.drawText(QRectF(0, self.height() / 2 + 35, self.width(), 35), Qt.AlignmentFlag.AlignCenter, f"({self.display_text})")


class CoreEngine(QMainWindow):
    def __init__(self, lang: str = "ar") -> None:
        super().__init__()
        self.lang = lang
        self.active_state = False
        self.drag_pos = QPoint()
        self.sr_recognizer = sr.Recognizer()
        self.mic = sr.Microphone()
        
        self._init_ui()

    def _init_ui(self) -> None:
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.resize(SystemConfig.WINDOW_WIDTH, SystemConfig.WINDOW_HEIGHT)
        
        self.canvas = CyberCanvas(self)
        self.setCentralWidget(self.canvas)
        
        layout = QVBoxLayout(self.canvas)
        layout.setContentsMargins(18, 18, 18, 18)

        top_bar = QHBoxLayout()
        lang_tag = f"[{self.lang.upper()}]"
        self.title_label = QLabel(f"RON_CORE // LINUX TACTICAL DAEMON v12.0 {lang_tag}")
        self.title_label.setStyleSheet("color: #ff3333; font-weight: bold; font-size: 10pt; font-family: 'Consolas'; background: transparent;")
        
        min_btn = QPushButton("—")
        min_btn.setFixedSize(32, 28)
        min_btn.clicked.connect(self.showMinimized)
        
        max_btn = QPushButton("□")
        max_btn.setFixedSize(32, 28)
        max_btn.clicked.connect(self._toggle_maximize)
        
        exit_btn = QPushButton("×")
        exit_btn.setFixedSize(32, 28)
        exit_btn.clicked.connect(self.close)
        
        for btn in [min_btn, max_btn, exit_btn]:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(12, 12, 18, 220);
                    color: #d0d0d8;
                    border: 1px solid rgba(35, 35, 50, 220);
                    font-family: 'Consolas';
                }
                QPushButton:hover {
                    background-color: #ff3333;
                    color: #040408;
                }
            """)
        
        top_bar.addWidget(self.title_label)
        top_bar.addStretch()
        top_bar.addWidget(min_btn)
        top_bar.addWidget(max_btn)
        top_bar.addWidget(exit_btn)
        layout.addLayout(top_bar)

        layout.addStretch()

        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setFixedHeight(160)
        self.console.setStyleSheet("""
            background-color: rgba(2, 2, 6, 230);
            color: #00ff88;
            border: 1px solid rgba(20, 20, 35, 230);
            font-family: 'Consolas', 'Courier New', monospace;
            font-size: 9.5pt;
        """)
        self.console.append(f"[+] RON_CORE v12.0 online. Mode: [{self.lang.upper()}]")
        self.console.append("[+] Ultimate Assistant Engine Active. Ready for voice commands...\n")
        layout.addWidget(self.console)

        controls = QHBoxLayout()
        self.trigger_btn = QPushButton("INITIALIZE STREAM")
        self.trigger_btn.setFixedHeight(38)
        self.trigger_btn.clicked.connect(self._toggle_stream)
        
        purge_btn = QPushButton("PURGE LOGS")
        purge_btn.setFixedWidth(140)
        purge_btn.setFixedHeight(38)
        purge_btn.clicked.connect(lambda: self.console.clear())

        for btn in [self.trigger_btn, purge_btn]:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(12, 12, 18, 230);
                    color: #d0d0d8;
                    border: 1px solid rgba(35, 35, 50, 230);
                    font-family: 'Consolas';
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #ff3333;
                    color: #040408;
                }
            """)

        controls.addWidget(self.trigger_btn)
        controls.addWidget(purge_btn)
        layout.addLayout(controls)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event) -> None:
        if event.buttons() == Qt.MouseButton.LeftButton and not self.isMaximized():
            delta = event.globalPosition().toPoint() - self.drag_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.drag_pos = event.globalPosition().toPoint()

    def _toggle_maximize(self) -> None:
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def _toggle_stream(self) -> None:
        if not self.active_state:
            self.active_state = True
            self.canvas.set_active(True)
            self.trigger_btn.setText("TERMINATE STREAM")
            self.trigger_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ff3333;
                    color: #040408;
                    border: 1px solid #ff3333;
                    font-family: 'Consolas';
                    font-weight: bold;
                }
            """)
            lang_code = "ar-AR" if self.lang == "ar" else "en-US"
            self.console.append(f"[~] Audio stream linked. Listening in [{lang_code}]...")
            threading.Thread(target=self._listen_loop, daemon=True).start()
        else:
            self.active_state = False
            self.canvas.set_active(False)
            self.trigger_btn.setText("INITIALIZE STREAM")
            self.trigger_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(12, 12, 18, 230);
                    color: #d0d0d8;
                    border: 1px solid rgba(35, 35, 50, 230);
                    font-family: 'Consolas';
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #ff3333;
                    color: #040408;
                }
            """)
            self.console.append("[-] Stream closed.\n")

    def _listen_loop(self) -> None:
        try:
            with self.mic as source:
                self.sr_recognizer.adjust_for_ambient_noise(source, duration=0.5)
        except Exception:
            pass
            
        lang_code = "ar-AR" if self.lang == "ar" else "en-US"
            
        while self.active_state:
            try:
                with self.mic as source:
                    audio = self.sr_recognizer.listen(source, timeout=5, phrase_time_limit=8)
                
                text = ""
                try:
                    text = self.sr_recognizer.recognize_google(audio, language=lang_code).strip()
                except Exception:
                    pass
                
                if text:
                    self._process_command(text)
                    
            except sr.WaitTimeoutError:
                continue
            except Exception:
                pass

    def _execute_and_capture(self, sys_cmd: str) -> str:
        try:
            res = subprocess.run(sys_cmd, shell=True, capture_output=True, text=True, timeout=15)
            output = res.stdout.strip() if res.stdout else res.stderr.strip()
            return output if output else "[*] Command executed successfully with no output."
        except Exception as err:
            return f"[-] Execution Error: {str(err)}"

    def _parse_arabic_intent(self, text: str) -> str:
        t = text.strip()
        
        # أوامر إيقاف التشغيل وإغلاق الحاسبة (مدمج مع كلمة سر kali لتنفيذ فوري)
        if any(keyword in t for keyword in ["إغلاق النظام", "أغلق الجهاز", "إيقاف التشغيل", "اطفاء", "poweroff", "shutdown"]):
            return "echo 'kali' | sudo -S poweroff"

        if re.search(r'(انشاء|إنشئ|عمل|اصنع|تكوين)\s+(مجلد|فلدر|ديركتوري)', t):
            target = re.sub(r'.*(مجلد|فلدر|ديركتوري)\s*', '', t).strip()
            return f"mkdir -p '{target if target else 'new_folder'}'"
        elif t.startswith("مجلد جديد"):
            target = t.replace("مجلد جديد", "").strip()
            return f"mkdir -p '{target if target else 'new_folder'}'"

        if re.search(r'(انشاء|إنشئ|عمل|اصنع|تكوين)\s+(ملف|فايل)', t):
            target = re.sub(r'.*(ملف|فايل)\s*', '', t).strip()
            return f"touch '{target if target else 'file.txt'}'"
        elif t.startswith("ملف جديد"):
            target = t.replace("ملف جديد", "").strip()
            return f"touch '{target if target else 'file.txt'}'"

        if "تحديث الحزم" in t or "تحديث النظام" in t:
            return "sudo apt update"
        if "ترقية النظام" in t:
            return "sudo apt upgrade -y"

        if "فحص المنافذ" in t or "انماب" in t or "أنماب" in t:
            target = re.sub(r'.*(انماب|أنماب|المنافذ)\s*', '', t).strip()
            return f"nmap -sS {target if target else '127.0.0.1'}"
        if "بنج" in t or "بنغ" in t:
            target = re.sub(r'.*(بنج|بنغ)\s*', '', t).strip()
            return f"ping -c 3 {target if target else '8.8.8.8'}"

        if "عرض الملفات" in t or "عرض المجلدات" in t or t == "ملفات":
            return "ls -la"
        if "المسار الحالي" in t or "أين أنا" in t:
            return "pwd"
        if "عنوان الايب" in t or "شبكتي" in t:
            return "ip a"

        return t

    def _process_command(self, voice_text: str) -> None:
        self.console.append(f"[>] Voice Vector: '{voice_text}'")
        
        cmd_lower = voice_text.strip().lower()

        if cmd_lower in ["خروج", "إغلاق الواجهة", "توقف", "stop", "exit"]:
            self.canvas.morph_to_command(voice_text, "exit")
            self.console.append("[!] Terminating daemon workflow...")
            QTimer.singleShot(1000, self.close)
            return
        elif cmd_lower in ["مسح الشاشة", "تطهير", "clear"]:
            self.canvas.morph_to_command(voice_text, "clear")
            self.console.clear()
            return
        elif cmd_lower in ["فتح المتصفح", "open browser"]:
            self.canvas.morph_to_command(voice_text, "browser")
            self.console.append("[+] Launching web browser interface...")
            webbrowser.open("https://www.google.com")
            return

        sys_cmd = self._parse_arabic_intent(voice_text)
        self.canvas.morph_to_command(voice_text, sys_cmd)
        self.console.append(f"[+] Executing: {sys_cmd}")
        
        output = self._execute_and_capture(sys_cmd)
        for line in output.splitlines()[:15]:
            self.console.append(f"    {line}")
        self.console.append("")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    selector = LanguageSelectorDialog()
    if selector.exec() == QDialog.DialogCode.Accepted:
        engine_window = CoreEngine(lang=selector.selected_lang)
        engine_window.show()
        sys.exit(app.exec())
    else:
        sys.exit(0)
