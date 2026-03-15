import sys
import os
import json
import traceback
from datetime import datetime
from pathlib import Path

# 修正：消除 Windows DPI 存取被拒警告 (必須放在 QApplication 之前)
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
os.environ["QT_AUTOSCREENSCALEFACTOR"] = "1"

from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QFrame)
from PyQt6.QtGui import QPixmap, QColor, QPainter, QShortcut, QKeySequence, QGuiApplication
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from settings_manager import ConfigManager

DEBUG_MODE = False

class InteractiveImageLabel(QLabel):
    """自定義的圖片顯示區：支援左右點擊與滾輪切換"""
    next_requested = pyqtSignal()
    prev_requested = pyqtSignal()

    def __init__(self):
        super().__init__("無圖片")
        self.setMinimumHeight(450)
        self.setStyleSheet("background-color: #121212; border-radius: 8px; border: 1px solid #222222; color: #555;")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMouseTracking(True)

    def mouseMoveEvent(self, event):
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if event.pos().x() < self.width() / 2:
                self.prev_requested.emit()
            else:
                self.next_requested.emit()
        super().mousePressEvent(event)

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if abs(delta) < 15: return
        if delta > 0: self.prev_requested.emit()
        else: self.next_requested.emit()
        event.accept()

class MorningReview(QWidget):
    def __init__(self):
        super().__init__()
        try:
            self.config_mgr = ConfigManager() 
            self.cat_map = self.config_mgr.get_category_map() 
        except:
            self.cat_map = {}
            
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(1000, 800) 
        
        self.base_dir = Path("WorkSnap_Data")
        self.progress_items = []
        self.current_idx = 0
        self.review_date_str = ""
        
        self.init_ui()
        self.setup_shortcuts()
        self.center_window()
        self.load_latest_session()

    def center_window(self):
        screen = QGuiApplication.primaryScreen()
        if screen:
            rect = screen.availableGeometry()
            self.move(rect.left() + (rect.width() - self.width()) // 2,
                      rect.top() + (rect.height() - self.height()) // 2)

    def setup_shortcuts(self):
        QShortcut(QKeySequence(Qt.Key.Key_Left), self).activated.connect(self.show_prev)
        QShortcut(QKeySequence(Qt.Key.Key_Right), self).activated.connect(self.show_next)
        QShortcut(QKeySequence(Qt.Key.Key_Escape), self).activated.connect(self.close)
        QShortcut(QKeySequence(Qt.Key.Key_Return), self).activated.connect(self.close)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.card = QFrame()
        self.card.setStyleSheet("QFrame#MainCard { background-color: #191919; border-radius: 12px; border: 1px solid #2C2C2C; }")
        self.card.setObjectName("MainCard")
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(40, 40, 40, 30); card_layout.setSpacing(20)

        self.header = QLabel("早安！正在讀取昨日進度...")
        self.header.setStyleSheet("color: #EBEBEA; font-size: 24px; font-weight: bold;")
        self.header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.header)

        info_layout = QHBoxLayout()
        self.tag_badge = QLabel("標籤")
        self.tag_badge.setAlignment(Qt.AlignmentFlag.AlignCenter); self.tag_badge.setFixedHeight(26)
        
        self.title_label = QLabel("專案名稱")
        self.title_label.setStyleSheet("color: #EBEBEA; font-size: 16px; font-weight: bold;")
        
        self.duration_label = QLabel("⏱️ 0.0h")
        self.duration_label.setStyleSheet("color: #9B9A97; font-size: 15px;")
        
        info_layout.addWidget(self.tag_badge); info_layout.addWidget(self.title_label, stretch=1); info_layout.addWidget(self.duration_label)
        card_layout.addLayout(info_layout)

        self.img_label = InteractiveImageLabel()
        self.img_label.prev_requested.connect(self.show_prev); self.img_label.next_requested.connect(self.show_next)
        card_layout.addWidget(self.img_label, stretch=1)

        nav_layout = QHBoxLayout()
        self.prev_btn = QPushButton("←")
        self.count_label = QLabel("0 / 0")
        self.count_label.setStyleSheet("color: #9B9A97; font-weight: bold;")
        self.next_btn = QPushButton("→")

        nav_btn_style = "QPushButton { background: transparent; color: #9B9A97; border: none; font-size: 18px; padding: 5px 15px; } QPushButton:hover { color: #EBEBEA; background: rgba(255,255,255,0.05); }"
        self.prev_btn.setStyleSheet(nav_btn_style); self.next_btn.setStyleSheet(nav_btn_style)
        self.prev_btn.clicked.connect(self.show_prev); self.next_btn.clicked.connect(self.show_next)
        
        nav_layout.addStretch(); nav_layout.addWidget(self.prev_btn); nav_layout.addSpacing(10)
        nav_layout.addWidget(self.count_label); nav_layout.addSpacing(10); nav_layout.addWidget(self.next_btn); nav_layout.addStretch()
        card_layout.addLayout(nav_layout)

        self.note_label = QLabel("備註內容")
        self.note_label.setWordWrap(True); self.note_label.setMinimumHeight(60)
        self.note_label.setStyleSheet("QLabel { color: #D4D4D4; background: rgba(255, 255, 255, 0.03); padding: 15px 20px; border-radius: 6px; border-left: 4px solid #444444; font-size: 14px; }")
        card_layout.addWidget(self.note_label)

        bottom_layout = QHBoxLayout()
        close_btn = QPushButton("收到，開始今日工作！")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor); close_btn.setFixedHeight(45)
        close_btn.setStyleSheet("QPushButton { background-color: #2F2F2F; color: #EBEBEA; font-weight: bold; border-radius: 6px; padding: 0 30px; border: 1px solid #3F3F3F; } QPushButton:hover { background-color: #3C3C3C; }")
        close_btn.clicked.connect(self.close)
        bottom_layout.addStretch(); bottom_layout.addWidget(close_btn)
        card_layout.addLayout(bottom_layout)
        layout.addWidget(self.card)

    def load_latest_session(self):
        log_dir = self.base_dir / "Logs"
        if not log_dir.exists(): return
        logs = sorted(list(log_dir.glob("*.json")), reverse=True)
        if not logs: 
            self.header.setText("早安！目前尚無紀錄。")
            return
        try:
            with open(logs[0], "r", encoding="utf-8") as f:
                data = json.load(f)
                if not data: return
                latest_date_str = data[-1].get('timestamp', '').split(' ')[0]
                dt = datetime.strptime(latest_date_str, "%Y-%m-%d")
                weekdays = ["一", "二", "三", "四", "五", "六", "日"]
                self.review_date_str = f"{dt.strftime('%m/%d')} (星期{weekdays[dt.weekday()]})"
                self.header.setText(f"早安！這是你 {self.review_date_str} 的進度回顧")
                all_day_projects = {}
                for session in data:
                    if session.get('timestamp', '').startswith(latest_date_str):
                        for p in session.get('projects', []):
                            all_day_projects[p.get('window_title', 'Unknown')] = p
                self.progress_items = list(all_day_projects.values())
                self.progress_items.sort(key=lambda x: len(x.get('note', '')), reverse=True)
                self.display_current_item()
        except: pass

    def update_tag_badge(self, tag):
        """核心修正：安全取得標籤樣式，徹底避免 KeyError"""
        # 建立一個保底的備用樣式 (Notion 灰色)
        fallback = {"icon": "📁", "style": {"bg": "transparent", "fg": "#555555", "border": "1px dashed #333333"}}
        
        # 1. 嘗試找標籤 2. 嘗試找 Uncategorized 3. 用寫死的 fallback
        cat_info = self.cat_map.get(tag)
        if not cat_info:
            cat_info = self.cat_map.get("Uncategorized", fallback)
            
        icon = cat_info.get("icon", "📁")
        style = cat_info.get("style", fallback["style"])
        
        display_name = "(無標籤)" if tag == "Uncategorized" or not tag else tag
        self.tag_badge.setText(f"{icon} {display_name}".strip())
        
        base_style = "border-radius: 4px; padding: 2px 10px; font-size: 12px; font-weight: bold;"
        css = f"background-color: {style['bg']}; color: {style['fg']}; border: {style['border']};"
        self.tag_badge.setStyleSheet(f"QLabel {{ {base_style} {css} }}")
        
    def display_current_item(self):
        if not self.progress_items: return
        item = self.progress_items[self.current_idx]
        self.title_label.setText(item.get('window_title', '無標題'))
        note = item.get('note', '')
        self.note_label.setText(note if note else "<span style='color: #666;'><i>(昨日未留下任何備註)</i></span>")
        dur = item.get('duration', 0.0)
        self.duration_label.setText(f"⏱️ {dur:.1f}h" if dur > 0 else "⏱️ -- h")
        self.count_label.setText(f"{self.current_idx + 1} / {len(self.progress_items)}")
        
        self.update_tag_badge(item.get('tag', 'Uncategorized'))
        
        img_path = self.base_dir / item.get('image_path', '')
        if img_path.exists():
            pixmap = QPixmap(str(img_path))
            self.img_label.setPixmap(pixmap.scaled(self.img_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            self.img_label.setText("找不到圖片紀錄")

        self.prev_btn.setEnabled(self.current_idx > 0)
        self.next_btn.setEnabled(self.current_idx < len(self.progress_items) - 1)

    def show_prev(self):
        if self.current_idx > 0: self.current_idx -= 1; self.display_current_item()
    def show_next(self):
        if self.current_idx < len(self.progress_items) - 1: self.current_idx += 1; self.display_current_item()
    def resizeEvent(self, event):
        super().resizeEvent(event); self.display_current_item()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    review = MorningReview()
    review.show()
    sys.exit(app.exec())