import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QListWidget, QListWidgetItem, QCheckBox, 
                             QLineEdit, QPushButton, QLabel, QTextEdit, QComboBox)
from PyQt6.QtCore import Qt
from core_engine import KeepGoingEngine
from archive_controller import ArchiveController

class WindowItemWidget(QWidget):
    """自定義清單項目組件"""
    def __init__(self, item_data):
        super().__init__()
        self.data = item_data
        layout = QHBoxLayout()
        
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(True) # 預設勾選
        
        # 顯示標題與類別
        label_text = f"[{item_data['category']}] {item_data['title'][:50]}"
        self.label = QLabel(label_text)
        
        layout.addWidget(self.checkbox)
        layout.addWidget(self.label)
        layout.addStretch()
        self.setLayout(layout)

class KeepGoingUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Keep-Going | 下班進度紀錄")
        self.resize(900, 600)
        
        self.engine = KeepGoingEngine()
        self.controller = ArchiveController()
        self.items_widgets = []

        self.init_ui()
        self.refresh_list()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # 上半部：左右分割
        content_layout = QHBoxLayout()
        
        # 左側：視窗清單
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("請勾選要紀錄的項目："))
        self.list_widget = QListWidget()
        self.list_widget.itemClicked.connect(self.on_item_clicked)
        left_layout.addWidget(self.list_widget)
        
        # 右側：編輯區域
        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel("進度備註："))
        self.note_edit = QTextEdit()
        self.note_edit.setPlaceholderText("輸入今天的進度，例如：完成登入頁面 UI...")
        self.note_edit.textChanged.connect(self.save_current_note)
        right_layout.addWidget(self.note_edit)
        
        right_layout.addWidget(QLabel("手動分類："))
        self.cat_combo = QComboBox()
        self.cat_combo.addItems(["Art", "Dev", "Writing", "Uncategorized"])
        self.cat_combo.currentIndexChanged.connect(self.save_current_category)
        right_layout.addWidget(self.cat_combo)
        right_layout.addStretch()

        content_layout.addLayout(left_layout, stretch=2)
        content_layout.addLayout(right_layout, stretch=1)

        # 下半部：按鈕
        btn_layout = QHBoxLayout()
        refresh_btn = QPushButton("重新掃描視窗")
        refresh_btn.clicked.connect(self.refresh_list)
        
        self.archive_btn = QPushButton("確認存檔並下班！")
        self.archive_btn.setStyleSheet("background-color: #2ecc71; color: white; font-weight: bold; height: 40px;")
        self.archive_btn.clicked.connect(self.start_archive)
        
        btn_layout.addWidget(refresh_btn)
        btn_layout.addWidget(self.archive_btn)

        main_layout.addLayout(content_layout)
        main_layout.addLayout(btn_layout)

    def refresh_list(self):
        """刷新視窗掃描清單"""
        self.list_widget.clear()
        self.items_widgets = []
        raw_items = self.engine.get_full_status()
        
        for item in raw_items:
            # 預設幫每個項目加一個空的 note 欄位
            item['note'] = ""
            
            list_item = QListWidgetItem(self.list_widget)
            widget = WindowItemWidget(item)
            list_item.setSizeHint(widget.sizeHint())
            
            self.list_widget.addItem(list_item)
            self.list_widget.setItemWidget(list_item, widget)
            self.items_widgets.append(widget)

    def on_item_clicked(self, list_item):
        """當點選清單時，將右側編輯器內容更新為該項目的資料"""
        widget = self.list_widget.itemWidget(list_item)
        self.current_selected_widget = widget
        self.note_edit.setText(widget.data['note'])
        self.cat_combo.setCurrentText(widget.data['category'])

    def save_current_note(self):
        """即時將編輯器的備註存回資料結構中"""
        if hasattr(self, 'current_selected_widget'):
            self.current_selected_widget.data['note'] = self.note_edit.toPlainText()

    def save_current_category(self):
        """即時將編輯器的分類存回資料結構中"""
        if hasattr(self, 'current_selected_widget'):
            new_cat = self.cat_combo.currentText()
            self.current_selected_widget.data['category'] = new_cat
            # 更新顯示文字
            self.current_selected_widget.label.setText(f"[{new_cat}] {self.current_selected_widget.data['title'][:50]}")

    def start_archive(self):
        """收集所有勾選的項目並呼叫後端執行存檔"""
        selected_data = []
        for widget in self.items_widgets:
            if widget.checkbox.isChecked():
                selected_data.append(widget.data)
        
        if not selected_data:
            print("請至少勾選一個項目！")
            return

        self.archive_btn.setEnabled(False)
        self.archive_btn.setText("存檔執行中...")
        
        # 執行存檔 (目前會稍微阻塞 UI，未來可改用 QThread)
        self.controller.run_archive_flow(selected_data)
        
        self.archive_btn.setEnabled(True)
        self.archive_btn.setText("存檔完成！")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = KeepGoingUI()
    window.show()
    sys.exit(app.exec())