import sys
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QListWidget, QLabel, QScrollArea, QFrame)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt

class InspectorUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Keep-Going | 歷史進度檢視器")
        self.resize(1200, 800)
        self.base_dir = Path("WorkSnap_Data")
        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # 左側：類別與日期選擇
        left_panel = QVBoxLayout()
        left_panel.addWidget(QLabel("1. 選擇標籤"))
        self.tag_list = QListWidget()
        self.tag_list.addItems(["Art", "Dev", "Writing", "Uncategorized"])
        self.tag_list.currentRowChanged.connect(self.load_images)
        left_panel.addWidget(self.tag_list)
        
        main_layout.addLayout(left_panel, stretch=1)

        # 右側：圖片展示區
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.display_container = QWidget()
        self.display_layout = QHBoxLayout(self.display_container) # 並排顯示
        self.scroll.setWidget(self.display_container)
        
        main_layout.addWidget(self.scroll, stretch=4)

    def load_images(self):
        # 清除舊內容
        for i in reversed(range(self.display_layout.count())): 
            self.display_layout.itemAt(i).widget().setParent(None)

        tag = self.tag_list.currentItem().text()
        tag_path = self.base_dir / tag
        
        if not tag_path.exists():
            return

        # 獲取該標籤下的所有截圖並排序（最新的在右邊）
        images = sorted(list(tag_path.glob("*.png")))
        
        # 為了演示「並排比對」，我們顯示最近的 3 張
        for img_path in images[-3:]:
            v_layout = QVBoxLayout()
            
            # 顯示日期標籤
            date_str = img_path.stem.split('_')[0]
            label = QLabel(f"日期: {date_str}")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # 顯示縮圖
            img_label = QLabel()
            pixmap = QPixmap(str(img_path))
            # 縮放圖片以適應螢幕，同時保持比例
            scaled_pixmap = pixmap.scaled(500, 500, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            img_label.setPixmap(scaled_pixmap)
            img_label.setFrameShape(QFrame.Shape.Box)
            
            v_layout.addWidget(label)
            v_layout.addWidget(img_label)
            
            container = QWidget()
            container.setLayout(v_layout)
            self.display_layout.addWidget(container)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = InspectorUI()
    window.show()
    sys.exit(app.exec())