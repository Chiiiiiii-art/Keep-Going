import sys
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QWidget, 
                             QLabel, QPushButton, QListWidget, QInputDialog)
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

        layout.addWidget(QLabel("<b>進程黑名單</b><br><span style='color:gray;'>被加入的 .exe 將不會出現在掃描清單中</span>"))
        
        self.black_exe_list = QListWidget()
        self.black_exe_list.addItems(self.config.get("blacklist_exes", []))
        self.black_exe_list.setStyleSheet("background: transparent; border: 1px solid #333; border-radius: 5px;")
        layout.addWidget(self.black_exe_list)
        
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("➕ 新增進程")
        add_btn.clicked.connect(self.add_exe)
        del_btn = QPushButton("🗑 刪除選中")
        del_btn.clicked.connect(self.delete_exe)
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(del_btn)
        layout.addLayout(btn_layout)

        layout.addSpacing(20)

        # 底部按鈕
        buttons = QHBoxLayout()
        save_btn = QPushButton("儲存設定")
        save_btn.setStyleSheet("background-color: #EBEBEA; color: #191919; font-weight: bold;")
        save_btn.clicked.connect(self.save_and_close)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        
        buttons.addStretch()
        buttons.addWidget(cancel_btn)
        buttons.addWidget(save_btn)
        layout.addLayout(buttons)

    def add_exe(self):
        exe, ok = QInputDialog.getText(self, "新增黑名單", "請輸入進程名稱 (例如: obsidian.exe):")
        if ok and exe:
            self.black_exe_list.addItem(exe)

    def delete_exe(self):
        item = self.black_exe_list.currentItem()
        if item:
            self.black_exe_list.takeItem(self.black_exe_list.row(item))

    def save_and_close(self):
        # 收集列表中的項目更新到 config
        new_list = [self.black_exe_list.item(i).text() for i in range(self.black_exe_list.count())]
        self.config["blacklist_exes"] = new_list
        self.config_mgr.save_config(self.config)
        self.accept()