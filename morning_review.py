import sys
import json
from datetime import datetime
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QFrame)
from PyQt6.QtGui import QPixmap, QColor, QPainter, QShortcut, QKeySequence, QGuiApplication
from PyQt6.QtCore import Qt, QSize, pyqtSignal

DEBUG_MODE = False

class InteractiveImageLabel(QLabel):
    """自定義的圖片顯示區：支援左右點擊與滾輪切換"""
    
    # 定義自訂信號，當需要切換圖片時發射
    next_requested = pyqtSignal()
    prev_requested = pyqtSignal()

    def __init__(self):
        super().__init__("無圖片")
        self.setMinimumHeight(450)
        self.setStyleSheet("background-color: #121212; border-radius: 8px; border: 1px solid #222222; color: #555;")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # 啟用滑鼠追蹤，以便改變游標形狀
        self.setMouseTracking(True)

    def mouseMoveEvent(self, event):
        """根據滑鼠在左半邊或右半邊，改變游標樣式"""
        if event.pos().x() < self.width() / 2:
            self.setCursor(Qt.CursorShape.PointingHandCursor) # 可視情況改為向左箭頭
        else:
            self.setCursor(Qt.CursorShape.PointingHandCursor) # 可視情況改為向右箭頭
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        """判斷點擊位置，觸發上一張或下一張"""
        if event.button() == Qt.MouseButton.LeftButton:
            if event.pos().x() < self.width() / 2:
                self.prev_requested.emit()
            else:
                self.next_requested.emit()
        super().mousePressEvent(event)

    def wheelEvent(self, event):
        """支援滑鼠滾輪切換圖片"""
        delta = event.angleDelta().y()
        if abs(delta) < 15: 
            return # 忽略微小滾動
            
        if delta > 0:
            # 向上滾 = 上一張
            self.prev_requested.emit()
        else:
            # 向下滾 = 下一張
            self.next_requested.emit()
        event.accept()


class MorningReview(QWidget):
    def __init__(self):
        super().__init__()
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
        
        # --- 主卡片 ---
        self.card = QFrame()
        self.card.setStyleSheet("""
            QFrame#MainCard {
                background-color: #191919; 
                border-radius: 12px; 
                border: 1px solid #2C2C2C;
            }
        """)
        self.card.setObjectName("MainCard")
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(40, 40, 40, 30)
        card_layout.setSpacing(20)

        # --- 頂部 ---
        self.header = QLabel("早安！正在讀取昨日進度...")
        self.header.setStyleSheet("color: #EBEBEA; font-size: 24px; font-weight: bold; letter-spacing: 1px;")
        self.header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.header)

        # --- 專案資訊列 ---
        info_layout = QHBoxLayout()
        self.tag_badge = QLabel("標籤")
        self.tag_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tag_badge.setFixedHeight(26)
        
        self.title_label = QLabel("專案名稱")
        self.title_label.setStyleSheet("color: #EBEBEA; font-size: 16px; font-weight: bold;")
        
        self.duration_label = QLabel("⏱️ 0.0h")
        self.duration_label.setStyleSheet("color: #9B9A97; font-size: 15px; font-weight: bold;")
        
        info_layout.addWidget(self.tag_badge)
        info_layout.addWidget(self.title_label, stretch=1)
        info_layout.addWidget(self.duration_label)
        card_layout.addLayout(info_layout)

        # --- 核心：可互動的圖片展示區 ---
        self.img_label = InteractiveImageLabel()
        # 綁定自訂信號到切換函數
        self.img_label.prev_requested.connect(self.show_prev)
        self.img_label.next_requested.connect(self.show_next)
        card_layout.addWidget(self.img_label, stretch=1)

        # --- 圖片下方的導航列 (緊貼圖片) ---
        nav_layout = QHBoxLayout()
        nav_layout.setContentsMargins(0, 0, 0, 10) # 稍微加上底部間距
        
        self.prev_btn = QPushButton("←")
        self.prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.prev_btn.setToolTip("上一張 (Left Arrow)")
        
        self.count_label = QLabel("0 / 0")
        self.count_label.setStyleSheet("color: #9B9A97; font-size: 14px; font-weight: bold;")
        self.count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.next_btn = QPushButton("→")
        self.next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.next_btn.setToolTip("下一張 (Right Arrow)")

        nav_btn_style = """
            QPushButton { background: transparent; color: #9B9A97; border: none; font-size: 16px; padding: 5px 15px; font-weight: bold; }
            QPushButton:hover { color: #EBEBEA; background: rgba(255,255,255,0.05); border-radius: 6px; }
            QPushButton:disabled { color: #333333; background: transparent; }
        """
        self.prev_btn.setStyleSheet(nav_btn_style)
        self.next_btn.setStyleSheet(nav_btn_style)
        
        self.prev_btn.clicked.connect(self.show_prev)
        self.next_btn.clicked.connect(self.show_next)
        
        nav_layout.addStretch()
        nav_layout.addWidget(self.prev_btn)
        nav_layout.addSpacing(10)
        nav_layout.addWidget(self.count_label)
        nav_layout.addSpacing(10)
        nav_layout.addWidget(self.next_btn)
        nav_layout.addStretch()
        
        card_layout.addLayout(nav_layout)

        # --- 備註區 ---
        self.note_label = QLabel("備註內容")
        self.note_label.setWordWrap(True)
        self.note_label.setMinimumHeight(60)
        self.note_label.setStyleSheet("""
            QLabel {
                color: #D4D4D4; 
                background: rgba(255, 255, 255, 0.03); 
                padding: 15px 20px; 
                border-radius: 6px;
                border-left: 4px solid #444444;
                font-size: 15px;
                line-height: 1.5;
            }
        """)
        card_layout.addWidget(self.note_label)

        # --- 最底部的確認按鈕 ---
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 15, 0, 0)
        
        close_btn = QPushButton("收到，開始今日工作！")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setFixedHeight(45)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #2F2F2F; color: #EBEBEA; 
                font-weight: bold; font-size: 15px; border-radius: 6px;
                padding: 0 30px; border: 1px solid #3F3F3F;
            }
            QPushButton:hover { background-color: #3C3C3C; border: 1px solid #4F4F4F; }
        """)
        close_btn.clicked.connect(self.close)

        bottom_layout.addStretch() # 將按鈕推向右側
        bottom_layout.addWidget(close_btn)

        card_layout.addLayout(bottom_layout)
        layout.addWidget(self.card)

    def load_latest_session(self):
        log_dir = self.base_dir / "Logs"
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
                            title = p.get('window_title', 'Unknown')
                            all_day_projects[title] = p
                
                self.progress_items = list(all_day_projects.values())
                self.progress_items.sort(key=lambda x: len(x.get('note', '')), reverse=True)

                self.current_idx = 0
                self.display_current_item()
        except Exception as e:
            if DEBUG_MODE: print(f"[DEBUG] 讀取失敗: {e}")

    def update_tag_badge(self, tag):
        colors = {
            "Art": "background-color: #4D2D2D; color: #FFA3A3;",
            "Dev": "background-color: #2D3D4D; color: #A3D1FF;",
            "Writing": "background-color: #2D4D3D; color: #A3FFD1;",
            "Uncategorized": "background-color: transparent; color: #9B9A97; border: 1px dashed #333333;"
        }
        icons = {"Art": "🎨 ", "Dev": "💻 ", "Writing": "📝 ", "Uncategorized": ""}
        
        display_name = "(無標籤)" if tag == "Uncategorized" else tag
        self.tag_badge.setText(f"{icons.get(tag, '')}{display_name}")
        
        base_style = "border-radius: 4px; padding: 2px 8px; font-size: 12px; font-weight: bold;"
        self.tag_badge.setStyleSheet(f"QLabel {{ {base_style} {colors.get(tag, colors['Uncategorized'])} }}")

    def display_current_item(self):
        if not self.progress_items: return
        
        item = self.progress_items[self.current_idx]
        
        title = item.get('window_title', '無標題')
        note = item.get('note', '')
        tag = item.get('tag', 'Uncategorized')
        img_rel_path = item.get('image_path', '')
        duration = item.get('duration', 0.0)

        self.title_label.setText(title)
        self.note_label.setText(note if note else "<span style='color: #666;'><i>(昨日未留下任何備註)</i></span>")
        self.duration_label.setText(f"⏱️ {duration}h" if duration > 0 else "⏱️ -- h")
        self.count_label.setText(f"{self.current_idx + 1} / {len(self.progress_items)}")
        
        self.update_tag_badge(tag)
        
        full_img_path = self.base_dir / img_rel_path
        if full_img_path.exists():
            pixmap = QPixmap(str(full_img_path))
            self.img_label.setPixmap(pixmap.scaled(self.img_label.size(), 
                                                  Qt.AspectRatioMode.KeepAspectRatio, 
                                                  Qt.TransformationMode.SmoothTransformation))
        else:
            self.img_label.setText("找不到圖片紀錄")
            self.img_label.setPixmap(QPixmap())

        # 根據是否到了邊界來停用按鈕，避免多餘操作
        self.prev_btn.setEnabled(self.current_idx > 0)
        self.next_btn.setEnabled(self.current_idx < len(self.progress_items) - 1)

    def show_prev(self):
        if self.current_idx > 0:
            self.current_idx -= 1
            self.display_current_item()

    def show_next(self):
        if self.current_idx < len(self.progress_items) - 1:
            self.current_idx += 1
            self.display_current_item()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.display_current_item()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    review = MorningReview()
    review.show()
    sys.exit(app.exec())