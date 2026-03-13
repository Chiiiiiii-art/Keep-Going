import sys
import json
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QListWidget, QLabel, QScrollArea, 
                             QFrame, QSplitter, QComboBox)
from PyQt6.QtGui import QPixmap, QFont
from PyQt6.QtCore import Qt

class InspectorUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Keep-Going | 歷史進度比對檢視器")
        self.resize(1400, 850)
        self.base_dir = Path("WorkSnap_Data")
        self.init_ui()
        self.refresh_tags()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # --- 左側控制台 ---
        control_panel = QVBoxLayout()
        control_panel.addWidget(QLabel("<b>1. 選擇分類</b>"))
        self.tag_list = QListWidget()
        self.tag_list.currentRowChanged.connect(self.load_date_list)
        control_panel.addWidget(self.tag_list)

        control_panel.addWidget(QLabel("<b>2. 選擇紀錄項目</b>"))
        control_panel.addWidget(QLabel("<font color='gray'>點擊第一下設為 [左對照]<br>點擊第二下設為 [右目標]</font>"))
        self.file_list = QListWidget()
        self.file_list.itemClicked.connect(self.handle_selection)
        control_panel.addWidget(self.file_list, stretch=2)
        
        main_layout.addLayout(control_panel, stretch=1)

        # --- 右側展示區：使用 Splitter 讓使用者自由調整左右比例 ---
        self.viewer_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左槽位 (Before)
        self.pane_left = self.create_image_pane("左對照 (過往進度)")
        # 右槽位 (After)
        self.pane_right = self.create_image_pane("右目標 (最新進度)")
        
        self.viewer_splitter.addWidget(self.pane_left)
        self.viewer_splitter.addWidget(self.pane_right)
        
        main_layout.addWidget(self.viewer_splitter, stretch=4)

        # 狀態紀錄
        self.current_pane = "left"

    def create_image_pane(self, title):
        """建立帶有標題與備註的圖片顯示區域"""
        container = QFrame()
        container.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(container)
        
        header = QLabel(title)
        header.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 圖片區域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        img_label = QLabel("尚未選擇圖片")
        img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        img_label.setStyleSheet("background-color: #1e1e1e; color: #555;")
        scroll.setWidget(img_label)
        
        # 備註區域
        note_label = QLabel("備註：無")
        note_label.setWordWrap(True)
        note_label.setStyleSheet("color: #2ecc71; padding: 10px; background: #252525;")
        note_label.setMinimumHeight(80)
        
        layout.addWidget(header)
        layout.addWidget(scroll)
        layout.addWidget(note_label)
        
        # 方便後續存取組件
        container.img_view = img_label
        container.note_view = note_label
        container.header_view = header
        return container

    def refresh_tags(self):
        """掃描資料夾獲取所有標籤"""
        self.tag_list.clear()
        if not self.base_dir.exists(): return
        
        # 排除 Logs 資料夾
        tags = [d.name for d in self.base_dir.iterdir() if d.is_dir() and d.name != "Logs"]
        self.tag_list.addItems(tags)

    def load_date_list(self):
        """載入該標籤下的所有截圖"""
        self.file_list.clear()
        tag = self.tag_list.currentItem().text()
        tag_path = self.base_dir / tag
        
        # 依日期排序（最新的在前）
        images = sorted(list(tag_path.glob("*.png")), reverse=True)
        for img in images:
            # 格式化顯示名稱: YYYY-MM-DD HH:MM - Title
            parts = img.stem.split('_')
            date_str = f"{parts[0][:4]}-{parts[0][4:6]}-{parts[0][6:]}"
            time_str = f"{parts[1][:2]}:{parts[1][2:4]}"
            title = "_".join(parts[2:])
            self.file_list.addItem(f"{date_str} {time_str} | {title}")
            # 存儲真實路徑在 Item 中
            self.file_list.item(self.file_list.count()-1).setData(Qt.ItemDataRole.UserRole, str(img))

    def handle_selection(self, item):
        """輪流填充左右槽位"""
        img_path = item.data(Qt.ItemDataRole.UserRole)
        
        if self.current_pane == "left":
            self.update_pane(self.pane_left, img_path)
            self.current_pane = "right"
        else:
            self.update_pane(self.pane_right, img_path)
            self.current_pane = "left"

    def update_pane(self, pane, img_path):
        """更新指定槽位的圖片與備註"""
        path = Path(img_path)
        
        # 1. 顯示圖片
        pixmap = QPixmap(str(path))
        # 依據視窗大小自動縮放
        scaled_pixmap = pixmap.scaled(pane.img_view.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        pane.img_view.setPixmap(scaled_pixmap)
        
        # 2. 顯示標題與時間
        parts = path.stem.split('_')
        pane.header_view.setText(f"{parts[0]} - {parts[1]}")
        
        # 3. 嘗試從日誌中讀取備註 (邏輯需要對應你的 ArchiveController 存檔格式)
        # 這裡簡化為從檔名抓取 Title，實務上應讀取 Logs/*.json
        self.load_note_from_logs(pane, path)

    def load_note_from_logs(self, pane, img_path):
        """讀取該截圖對應的備註資訊"""
        date_str = img_path.stem.split('_')[0]
        log_file = self.base_dir / "Logs" / f"{date_str}.json"
        
        note_text = "找不到對應的日誌備註。"
        if log_file.exists():
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    logs = json.load(f)
                    # 依據檔案名稱比對日誌中的項目
                    for entry in logs:
                        if entry['title'][:20] in img_path.name: # 模糊比對
                            note_text = entry.get('note', '未輸入備註')
                            break
            except: pass
        
        pane.note_view.setText(f"<b>進度紀錄：</b><br>{note_text}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # 使用暗色風格提升創作者體驗
    app.setStyle("Fusion")
    window = InspectorUI()
    window.show()
    sys.exit(app.exec())