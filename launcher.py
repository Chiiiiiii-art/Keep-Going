# launcher.py

import sys
# 必須在最頂部設定，解決 COM error 0x80010106
sys.coinit_flags = 2 

import os
import ctypes
from datetime import datetime
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QFrame)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QGuiApplication


# 導入功能
from main_gui import KeepGoingUI
from inspector_gui import InspectorUI
from morning_review import MorningReview
from settings_dialog import SettingsDialog

class KeepGoingLauncher(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Keep-Going 控制中心")
        self.setFixedSize(340, 520)
        self.setWindowFlags(Qt.WindowType.WindowCloseButtonHint | Qt.WindowType.WindowMinimizeButtonHint)
        self.init_ui()
        self.center_window() # 核心修正：置中顯示

    def center_window(self):
        """防止視窗在雙螢幕環境下超出邊界"""
        screen = QGuiApplication.primaryScreen()
        if screen:
            rect = screen.availableGeometry()
            self.move(rect.left() + (rect.width() - self.width()) // 2,
                      rect.top() + (rect.height() - self.height()) // 2)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setSpacing(12)
        self.main_layout.setContentsMargins(24, 32, 24, 24)

        title_label = QLabel("Keep Going")
        title_label.setObjectName("TitleLabel")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(title_label)

        subtitle = QLabel("創作者進度管理系統")
        subtitle.setObjectName("SubTitleLabel")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(subtitle)
        self.main_layout.addSpacing(20)

        # 功能按鈕
        self.create_nav_button("🚀", "下班存檔紀錄", self.open_archive)
        self.create_nav_button("🔍", "歷史進度檢閱", self.open_inspector)
        self.create_nav_button("🌅", "手動晨間回顧", self.open_review)
        self.create_nav_button("⚙️", "系統規則設定", self.open_settings)

        self.main_layout.addStretch()
        
        status_frame = QFrame()
        status_frame.setObjectName("StatusFrame")
        status_layout = QVBoxLayout(status_frame)
        status_layout.setContentsMargins(0, 15, 0, 0)
        self.last_save_label = QLabel(f"最後存檔日期：{self.get_last_save_time()}")
        self.last_save_label.setObjectName("StatusLabel")
        self.last_save_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_layout.addWidget(self.last_save_label)
        self.main_layout.addWidget(status_frame)

    def create_nav_button(self, icon_char, text, callback):
        btn = QPushButton()
        btn.setObjectName("NavButton")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        layout = QHBoxLayout(btn)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(15)
        
        icon_label = QLabel(icon_char); icon_label.setObjectName("IconLabel")
        icon_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        text_label = QLabel(text); text_label.setObjectName("ButtonText")
        text_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        layout.addWidget(icon_label); layout.addWidget(text_label); layout.addStretch()
        btn.clicked.connect(callback)
        self.main_layout.addWidget(btn)
        return btn

    def get_last_save_time(self):
        log_dir = Path("WorkSnap_Data/Logs")
        if not log_dir.exists(): return "尚無紀錄"
        logs = sorted(list(log_dir.glob("*.json")), reverse=True)
        return datetime.fromtimestamp(logs[0].stat().st_mtime).strftime("%Y-%m-%d %H:%M") if logs else "尚無紀錄"

    def open_archive(self): self.archive_win = KeepGoingUI(); self.archive_win.show()
    def open_inspector(self): self.inspector_win = InspectorUI(); self.inspector_win.show()
    def open_review(self): self.review_win = MorningReview(); self.review_win.show()
    def open_settings(self): self.settings_win = SettingsDialog(self); self.settings_win.exec()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    qss_path = Path("style.qss")
    if qss_path.exists(): app.setStyleSheet(qss_path.read_text(encoding="utf-8"))
    launcher = KeepGoingLauncher()
    launcher.show()
    sys.exit(app.exec())