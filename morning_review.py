import sys
import json
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QFrame)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt

DEBUG_MODE = True # 測試完改 False 或刪除

class MorningReview(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(550, 720)
        self.base_dir = Path("WorkSnap_Data")
        self.progress_items = []
        self.current_idx = 0
        self.init_ui()
        self.load_latest_session()

    def init_ui(self):
        layout = QVBoxLayout(self)
        self.card = QFrame()
        self.card.setStyleSheet("background-color: #2c3e50; border-radius: 20px; border: 2px solid #34495e;")
        card_layout = QVBoxLayout(self.card)
        
        self.header = QLabel("早安！這是你昨天的進度回顧")
        self.header.setStyleSheet("color: #ecf0f1; font-size: 18px; font-weight: bold; margin: 10px;")
        self.header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.header)

        self.img_label = QLabel("正在讀取截圖...")
        self.img_label.setFixedSize(510, 320)
        self.img_label.setStyleSheet("background-color: #1e1e1e; border-radius: 10px; color: #555;")
        self.img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.img_label)

        self.title_label = QLabel("")
        self.title_label.setStyleSheet("font-weight: bold; color: #3498db; font-size: 15px;")
        self.title_label.setWordWrap(True)
        card_layout.addWidget(self.title_label)

        self.note_label = QLabel("")
        self.note_label.setWordWrap(True)
        self.note_label.setMinimumHeight(100)
        self.note_label.setStyleSheet("color: #2ecc71; background: #1a252f; padding: 10px; border-radius: 5px;")
        card_layout.addWidget(self.note_label)

        nav_layout = QHBoxLayout()
        self.prev_btn = QPushButton("← 上一個")
        self.next_btn = QPushButton("下一個 →")
        self.count_label = QLabel("0 / 0")
        self.count_label.setStyleSheet("color: white;")
        
        self.prev_btn.clicked.connect(self.show_prev)
        self.next_btn.clicked.connect(self.show_next)
        
        nav_layout.addWidget(self.prev_btn)
        nav_layout.addStretch()
        nav_layout.addWidget(self.count_label)
        nav_layout.addStretch()
        nav_layout.addWidget(self.next_btn)
        card_layout.addLayout(nav_layout)

        close_btn = QPushButton("收到，開始今日工作！")
        close_btn.setStyleSheet("background-color: #27ae60; color: white; padding: 12px; border-radius: 10px; font-weight: bold;")
        close_btn.clicked.connect(self.close)
        card_layout.addWidget(close_btn)
        layout.addWidget(self.card)

    def load_latest_session(self):
        log_dir = self.base_dir / "Logs"
        logs = sorted(list(log_dir.glob("*.json")), reverse=True)
        if not logs: return
        
        try:
            with open(logs[0], "r", encoding="utf-8") as f:
                data = json.load(f)
                if not data: return
                
                # 1. 找出最後出現的日期 (YYYY-MM-DD)
                latest_date = data[-1].get('timestamp', '').split(' ')[0]
                if DEBUG_MODE: print(f"[DEBUG] 鎖定回顧日期: {latest_date}")
                
                # 2. 收集該日期的所有項目
                all_day_projects = {}
                for session in data:
                    if session.get('timestamp', '').startswith(latest_date):
                        for p in session.get('projects', []):
                            # 使用 window_title 作為 Key 進行去重
                            # 後面的存檔會覆蓋前面的，確保看到的是該視窗當天最後的狀態
                            title = p.get('window_title', 'Unknown')
                            all_day_projects[title] = p
                
                # 3. 轉回列表並排序（將有備註的排在前面）
                self.progress_items = list(all_day_projects.values())
                self.progress_items.sort(key=lambda x: len(x.get('note', '')), reverse=True)
                
                if DEBUG_MODE:
                    print(f"[DEBUG] 成功聚合全日資料，共 {len(self.progress_items)} 個不重複項目")

                self.current_idx = 0
                self.display_current_item()
        except Exception as e:
            if DEBUG_MODE: print(f"[DEBUG] 讀取失敗: {e}")

    def display_current_item(self):
        if not self.progress_items: return
        
        item = self.progress_items[self.current_idx]
        
        # 修正欄位名稱對應 [ window_title, tag, image_path ]
        title = item.get('window_title', '無標題')
        note = item.get('note', '(未留下備註)')
        tag = item.get('tag', 'Uncategorized')
        img_rel_path = item.get('image_path', '')

        self.title_label.setText(f"[{tag}] {title}")
        self.note_label.setText(note)
        self.count_label.setText(f"{self.current_idx + 1} / {len(self.progress_items)}")
        
        # 直接使用路徑讀取圖片
        full_img_path = self.base_dir / img_rel_path
        if full_img_path.exists():
            pixmap = QPixmap(str(full_img_path))
            self.img_label.setPixmap(pixmap.scaled(self.img_label.size(), 
                                                  Qt.AspectRatioMode.KeepAspectRatio, 
                                                  Qt.TransformationMode.SmoothTransformation))
        else:
            self.img_label.setText(f"找不到圖片\n{img_rel_path}")
            self.img_label.setPixmap(QPixmap())

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

if __name__ == "__main__":
    app = QApplication(sys.argv)
    review = MorningReview()
    review.show()
    sys.exit(app.exec())