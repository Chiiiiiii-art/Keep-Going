import sys
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, 
                             QWidget, QLabel, QLineEdit, QPushButton, QListWidget, 
                             QInputDialog, QMessageBox)
from settings_manager import ConfigManager

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Keep-Going 系統設定")
        self.resize(500, 400)
        self.config_mgr = ConfigManager()
        self.config = self.config_mgr.load_config()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()

        # --- 分頁 1: 分類規則 ---
        self.rules_tab = QWidget()
        rules_layout = QVBoxLayout(self.rules_tab)
        self.category_list = QListWidget()
        self.category_list.addItems(self.config["rules"].keys())
        self.category_list.currentRowChanged.connect(self.update_exe_list)
        
        rules_layout.addWidget(QLabel("1. 選擇分類："))
        rules_layout.addWidget(self.category_list)
        
        rules_layout.addWidget(QLabel("2. 關聯的 .exe 清單 (按右鍵或下方按鈕編輯)："))
        self.exe_list = QListWidget()
        rules_layout.addWidget(self.exe_list)

        exe_btn_layout = QHBoxLayout()
        add_exe_btn = QPushButton("新增 EXE")
        add_exe_btn.clicked.connect(self.add_exe)
        del_exe_btn = QPushButton("刪除選中")
        del_exe_btn.clicked.connect(self.delete_exe)
        exe_btn_layout.addWidget(add_exe_btn)
        exe_btn_layout.addWidget(del_exe_btn)
        rules_layout.addLayout(exe_btn_layout)

        # --- 分頁 2: 黑名單管理 ---
        self.blacklist_tab = QWidget()
        black_layout = QVBoxLayout(self.blacklist_tab)
        
        black_layout.addWidget(QLabel("進程黑名單 (不偵測這些 .exe)："))
        self.black_exe_list = QListWidget()
        self.black_exe_list.addItems(self.config["blacklist_exes"])
        black_layout.addWidget(self.black_exe_list)
        
        self.tabs.addTab(self.rules_tab, "標籤規則")
        self.tabs.addTab(self.blacklist_tab, "過濾設定")

        layout.addWidget(self.tabs)

        # 底部按鈕
        buttons = QHBoxLayout()
        save_btn = QPushButton("儲存設定")
        save_btn.clicked.connect(self.save_and_close)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        buttons.addStretch()
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)

    def update_exe_list(self, row):
        self.exe_list.clear()
        category = self.category_list.item(row).text()
        self.exe_list.addItems(self.config["rules"][category])

    def add_exe(self):
        category_item = self.category_list.currentItem()
        if not category_item: return
        exe, ok = QInputDialog.getText(self, "新增規則", "請輸入進程名稱 (例如: obsidian.exe):")
        if ok and exe:
            category = category_item.text()
            self.config["rules"][category].append(exe)
            self.update_exe_list(self.category_list.currentRow())

    def delete_exe(self):
        category_item = self.category_list.currentItem()
        exe_item = self.exe_list.currentItem()
        if category_item and exe_item:
            self.config["rules"][category_item.text()].remove(exe_item.text())
            self.update_exe_list(self.category_list.currentRow())

    def save_and_close(self):
        self.config_mgr.save_config(self.config)
        self.accept()