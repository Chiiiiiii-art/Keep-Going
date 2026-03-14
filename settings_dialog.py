import sys
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QWidget, 
                             QLabel, QPushButton, QListWidget, QInputDialog, QFrame)
from PyQt6.QtCore import Qt
from settings_manager import ConfigManager

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Keep-Going 系統設定 - 視窗過濾")
        self.resize(450, 500)
        self.config_mgr = ConfigManager()
        self.config = self.config_mgr.load_config()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)

        # --- 標題區域 ---
        header_title = QLabel("程序黑名單")
        header_title.setStyleSheet("font-size: 18px; font-weight: bold;") # 局部微調標題大小
        
        header_desc = QLabel("被加入的 .exe 將不會出現在掃描清單中")
        header_desc.setObjectName("SubTitleLabel") # 套用 QSS 的灰色字
        
        layout.addWidget(header_title)
        layout.addWidget(header_desc)
        
        # --- 列表區域 ---
        self.black_exe_list = QListWidget()
        self.black_exe_list.addItems(self.config.get("blacklist_exes", []))
        # 移除硬編碼樣式，讓 QSS 透過 QListWidget 選擇器處理
        layout.addWidget(self.black_exe_list)
        
        # --- 控制按鈕 ---
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("➕ 新增程序")
        add_btn.setObjectName("SettingsButton") # 套用次要按鈕樣式
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        
        del_btn = QPushButton("🗑 刪除選中")
        del_btn.setObjectName("SettingsButton") # 套用次要按鈕樣式
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(del_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        layout.addSpacing(10)
        
        # 分隔線 (Notion 常見的細線)
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: rgba(255, 255, 255, 0.05); border: none; min-height: 1px;")
        layout.addWidget(line)

        # --- 底部功能按鈕 ---
        buttons = QHBoxLayout()
        buttons.setSpacing(12)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("SettingsButton") # 取消按鈕也採用次要樣式
        cancel_btn.clicked.connect(self.reject)
        
        save_btn = QPushButton("儲存設定")
        save_btn.setObjectName("ArchiveButton") # 套用主按鈕樣式（細邊框版本）
        save_btn.clicked.connect(self.save_and_close)
        
        buttons.addStretch()
        buttons.addWidget(cancel_btn)
        buttons.addWidget(save_btn)
        layout.addLayout(buttons)

    def add_exe(self):
        exe, ok = QInputDialog.getText(self, "新增黑名單", "請輸入程序名稱 (例如: obsidian.exe):") # 程序改程序
        if ok and exe:
            self.black_exe_list.addItem(exe)

    def delete_exe(self):
        item = self.black_exe_list.currentItem()
        if item:
            self.black_exe_list.takeItem(self.black_exe_list.row(item))

    def save_and_close(self):
        new_list = [self.black_exe_list.item(i).text() for i in range(self.black_exe_list.count())]
        self.config["blacklist_exes"] = new_list
        self.config_mgr.save_config(self.config)
        self.accept()