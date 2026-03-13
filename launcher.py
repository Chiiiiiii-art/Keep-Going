import sys
import os
from datetime import datetime
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QFrame)
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtCore import Qt

# 導入各個功能視窗
from main_gui import KeepGoingUI
from inspector_gui import InspectorUI
from morning_review import MorningReview
from settings_dialog import SettingsDialog

class KeepGoingLauncher(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Keep-Going 控制中心")
        self.setFixedSize(320, 480)
        
        # 設為工具視窗樣式
        self.setWindowFlags(Qt.WindowType.WindowCloseButtonHint | Qt.WindowType.WindowMinimizeButtonHint)
        
        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setSpacing(15)
        self.main_layout.setContentsMargins(20, 20, 20, 20)

        # --- 標題區域 ---
        title_label = QLabel("KEEP GOING")
        title_label.setFont(QFont("Impact", 28))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: #27ae60; letter-spacing: 2px;")
        self.main_layout.addWidget(title_label)

        subtitle = QLabel("創作者進度管理系統")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #7f8c8d; font-size: 12px; margin-bottom: 10px;")
        self.main_layout.addWidget(subtitle)

        # --- 功能按鈕區 ---
        self.btn_archive = self.create_nav_button("🚀 下班存檔紀錄", "#27ae60", self.open_archive)
        self.btn_inspector = self.create_nav_button("🔍 歷史進度檢閱", "#3498db", self.open_inspector)
        self.btn_review = self.create_nav_button("🌅 手動晨間回顧", "#e67e22", self.open_review)
        self.btn_settings = self.create_nav_button("⚙ 系統規則設定", "#95a5a6", self.open_settings)

        # --- 底部狀態欄 ---
        self.main_layout.addStretch()
        
        status_frame = QFrame()
        status_frame.setStyleSheet("background-color: #1a252f; border-radius: 10px;")
        status_layout = QVBoxLayout(status_frame)
        
        self.last_save_label = QLabel(f"最後存檔: {self.get_last_save_time()}")
        self.last_save_label.setStyleSheet("color: #bdc3c7; font-size: 11px;")
        self.last_save_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_layout.addWidget(self.last_save_label)
        
        self.main_layout.addWidget(status_frame)

    def create_nav_button(self, text, color, callback):
        btn = QPushButton(text)
        btn.setFixedHeight(55)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #2c3e50;
                color: {color};
                border: 2px solid {color};
                border-radius: 10px;
                font-size: 15px;
                font-weight: bold;
                text-align: left;
                padding-left: 20px;
            }}
            QPushButton:hover {{
                background-color: {color};
                color: white;
            }}
        """)
        btn.clicked.connect(callback)
        self.main_layout.addWidget(btn)
        return btn

    def get_last_save_time(self):
        log_dir = Path("WorkSnap_Data/Logs")
        if not log_dir.exists(): return "尚無紀錄"
        logs = sorted(list(log_dir.glob("*.json")), reverse=True)
        if not logs: return "尚無紀錄"
        
        # 這裡簡化為抓取最後一個檔案的修改日期
        mtime = datetime.fromtimestamp(logs[0].stat().st_mtime)
        return mtime.strftime("%Y-%m-%d %H:%M")

    # --- 導航邏輯 ---
    def open_archive(self):
        self.archive_win = KeepGoingUI()
        self.archive_win.show()

    def open_inspector(self):
        self.inspector_win = InspectorUI()
        self.inspector_win.show()

    def open_review(self):
        self.review_win = MorningReview()
        self.review_win.show()

    def open_settings(self):
        self.settings_win = SettingsDialog(self)
        self.settings_win.exec()
        # 設定完後刷新標題（如果有的話）

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # 設定全局暗色調
    palette = app.palette()
    from PyQt6.QtGui import QColor, QPalette
    dark_palette = QPalette()
    dark_palette.setColor(QPalette.ColorRole.Window, QColor(44, 62, 80))
    dark_palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
    app.setPalette(dark_palette)
    
    launcher = KeepGoingLauncher()
    launcher.show()
    sys.exit(app.exec())