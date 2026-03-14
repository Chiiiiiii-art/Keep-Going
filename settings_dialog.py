import sys
from pathlib import Path
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, 
                             QWidget, QLabel, QLineEdit, QPushButton, QListWidget, 
                             QInputDialog, QComboBox, QFrame, QListWidgetItem, QMessageBox)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor, QPixmap, QIcon, QPainter
from settings_manager import ConfigManager, TAG_THEMES

def create_color_icon(hex_color, size=16):
    """產生圓角顏色方塊圖標"""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(hex_color))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(0, 0, size, size, 4, 4)
    painter.end()
    return QIcon(pixmap)

class CategoryEditDialog(QDialog):
    """新增/編輯標籤的對話框"""
    def __init__(self, parent=None, edit_data=None):
        super().__init__(parent)
        self.edit_data = edit_data
        self.setWindowTitle("編輯分類標籤" if edit_data else "新增分類標籤")
        self.setFixedWidth(350)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)
        
        layout.addWidget(QLabel("分類名稱"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("例如: Design, Study...")
        if self.edit_data: self.name_input.setText(self.edit_data.get("name", ""))
        layout.addWidget(self.name_input)
        
        layout.addWidget(QLabel("Emoji 圖示"))
        self.icon_input = QLineEdit()
        self.icon_input.setPlaceholderText("貼上一個 Emoji (如 🎨)...")
        if self.edit_data: self.icon_input.setText(self.edit_data.get("icon", ""))
        layout.addWidget(self.icon_input)
        
        layout.addWidget(QLabel("標籤色調"))
        self.theme_combo = QComboBox()
        index_to_set = 0
        for i, (theme_name, theme_data) in enumerate(TAG_THEMES.items()):
            if theme_name == "Uncategorized": continue
            icon = create_color_icon(theme_data["fg"])
            self.theme_combo.addItem(icon, theme_name)
            if self.edit_data and self.edit_data.get("theme") == theme_name:
                index_to_set = self.theme_combo.count() - 1
        if self.edit_data: self.theme_combo.setCurrentIndex(index_to_set)
        layout.addWidget(self.theme_combo)
        
        layout.addSpacing(15)
        btns = QHBoxLayout()
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("CancelButton")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        
        ok_btn = QPushButton("儲存變更" if self.edit_data else "確認建立")
        ok_btn.setObjectName("PrimaryButton")
        ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        ok_btn.clicked.connect(self.accept)
        
        btns.addWidget(cancel_btn)
        btns.addWidget(ok_btn)
        layout.addLayout(btns)
        
    def get_data(self):
        return {
            "name": self.name_input.text().strip(),
            "icon": self.icon_input.text().strip(),
            "theme": self.theme_combo.currentText()
        }

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Keep-Going 系統設定")
        self.resize(480, 580)
        self.config_mgr = ConfigManager()
        self.config = self.config_mgr.load_config()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("SettingsTabs")

        # --- 分頁 1: 標籤管理 ---
        self.cat_tab = QWidget()
        cat_layout = QVBoxLayout(self.cat_tab)
        cat_layout.setContentsMargins(20, 25, 20, 20)
        cat_layout.setSpacing(15)
        
        cat_layout.addWidget(QLabel("<b>專屬分類標籤</b><br><span style='color:gray; font-size:12px;'>雙擊標籤即可進入編輯</span>"))
        self.cat_list = QListWidget()
        self.cat_list.setObjectName("CategoryList")
        self.cat_list.setIconSize(QSize(14, 14))
        self.cat_list.itemDoubleClicked.connect(self.edit_category)
        self.refresh_cat_list()
        cat_layout.addWidget(self.cat_list)

        cat_btn_layout = QHBoxLayout()
        add_cat_btn = QPushButton("➕ 新增標籤")
        add_cat_btn.clicked.connect(self.add_category)
        del_cat_btn = QPushButton("🗑 刪除標籤")
        del_cat_btn.clicked.connect(self.delete_category)
        cat_btn_layout.addWidget(add_cat_btn)
        cat_btn_layout.addWidget(del_cat_btn)
        cat_layout.addLayout(cat_btn_layout)

        # --- 分頁 2: 過濾設定 ---
        self.blacklist_tab = QWidget()
        black_layout = QVBoxLayout(self.blacklist_tab)
        black_layout.setContentsMargins(20, 25, 20, 20)
        black_layout.setSpacing(15)
        black_layout.addWidget(QLabel("<b>不偵測的程序 (.exe)</b>"))
        
        self.black_exe_list = QListWidget()
        self.black_exe_list.setObjectName("Blacklist")
        self.black_exe_list.addItems(self.config.get("blacklist_exes", []))
        black_layout.addWidget(self.black_exe_list)
        
        black_btn_layout = QHBoxLayout()
        add_exe_btn = QPushButton("➕ 新增 EXE")
        add_exe_btn.clicked.connect(self.add_exe)
        del_exe_btn = QPushButton("🗑 移除選中")
        del_exe_btn.clicked.connect(self.delete_exe)
        black_btn_layout.addWidget(add_exe_btn)
        black_btn_layout.addWidget(del_exe_btn)
        black_layout.addLayout(black_btn_layout)
        
        # --- 分頁 3: 其他設定 ---
        self.other_tab = QWidget()
        other_layout = QVBoxLayout(self.other_tab)
        other_layout.setContentsMargins(20, 25, 20, 20)
        other_layout.setSpacing(15)
        
        other_layout.addWidget(QLabel("<b>危險操作與系統管理</b><br><span style='color:gray; font-size:12px;'>此區域的設定將對系統資料產生不可逆的影響</span>"))
        
        reset_btn = QPushButton("⚠️ 還原原廠設定")
        reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reset_btn.setObjectName("DangerButton") 
        reset_btn.clicked.connect(self.factory_reset)
        
        other_layout.addWidget(reset_btn)
        other_layout.addStretch()

        self.tabs.addTab(self.cat_tab, "標籤管理")
        self.tabs.addTab(self.blacklist_tab, "過濾設定")
        self.tabs.addTab(self.other_tab, "其他設定")
        layout.addWidget(self.tabs)

        self.line = QFrame()
        self.line.setObjectName("BottomSeparator")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Plain)
        layout.addWidget(self.line)

        bottom_area = QWidget()
        bottom_layout = QHBoxLayout(bottom_area)
        bottom_layout.setContentsMargins(20, 15, 20, 20)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("CancelButton")
        cancel_btn.clicked.connect(self.reject)
        
        save_btn = QPushButton("儲存所有設定")
        save_btn.setObjectName("ArchiveButton")
        save_btn.setFixedWidth(140)
        save_btn.clicked.connect(self.save_and_close)
        
        bottom_layout.addStretch()
        bottom_layout.addWidget(cancel_btn)
        bottom_layout.addWidget(save_btn)
        layout.addWidget(bottom_area)

    def refresh_cat_list(self):
        self.cat_list.clear()
        for c in self.config.get("categories", []):
            name = c['name']
            icon_char = c.get('icon', '🔹')
            theme_name = c.get('theme', 'Gray')
            theme_color = TAG_THEMES.get(theme_name, TAG_THEMES["Gray"])["fg"]
            
            item = QListWidgetItem(f"{icon_char}  {name}")
            item.setIcon(create_color_icon(theme_color))
            self.cat_list.addItem(item)

    def add_category(self):
        dlg = CategoryEditDialog(self)
        if dlg.exec():
            data = dlg.get_data()
            if data["name"]:
                self.config["categories"].append(data)
                self.refresh_cat_list()

    def edit_category(self, item):
        row = self.cat_list.row(item)
        cat_data = self.config["categories"][row]
        dlg = CategoryEditDialog(self, edit_data=cat_data)
        if dlg.exec():
            data = dlg.get_data()
            if data["name"]:
                self.config["categories"][row] = data
                self.refresh_cat_list()

    def delete_category(self):
        row = self.cat_list.currentRow()
        if row >= 0:
            del self.config["categories"][row]
            self.refresh_cat_list()

    def add_exe(self):
        exe, ok = QInputDialog.getText(self, "新增黑名單", "輸入進程名 (例: explorer.exe):")
        if ok and exe: self.black_exe_list.addItem(exe)

    def delete_exe(self):
        item = self.black_exe_list.currentItem()
        if item: self.black_exe_list.takeItem(self.black_exe_list.row(item))

    def save_and_close(self):
        self.config["blacklist_exes"] = [self.black_exe_list.item(i).text() for i in range(self.black_exe_list.count())]
        self.config_mgr.save_config(self.config)
        self.accept()

    def factory_reset(self):
        # --- 1. 警告視窗 (手寫) ---
        warn_dlg = QDialog(self)
        warn_dlg.setWindowTitle("確定要還原原廠設定嗎？")
        warn_dlg.setFixedSize(400, 180)
        
        warn_layout = QVBoxLayout(warn_dlg)
        warn_layout.setContentsMargins(30, 30, 30, 25)
        
        warn_content = QLabel("<b>還原原廠設定</b><br><br>這將會清除所有視窗與分頁的標籤記憶，以及自訂的系統分類和黑名單設定，此操作無法復原！")
        warn_content.setWordWrap(True)
        warn_content.setStyleSheet("color: #EBEBEA; font-size: 14px;")
        warn_layout.addWidget(warn_content)
        
        btn_area = QHBoxLayout()
        btn_area.addStretch()
        
        btn_cancel = QPushButton("取消")
        btn_cancel.setStyleSheet("QPushButton { color: #9B9A97 !important; background: transparent !important; border: none !important; padding: 8px 15px; } QPushButton:hover { background-color: rgba(255, 255, 255, 0.05) !important; color: #EBEBEA !important; border-radius: 6px; }")
        
        btn_restore = QPushButton("還原")
        btn_restore.setStyleSheet("QPushButton { color: #FF4D4D !important; background: transparent !important; border: none !important; padding: 8px 15px; font-weight: bold; } QPushButton:hover { background-color: rgba(255, 77, 77, 0.1) !important; border-radius: 6px; }")
        
        btn_cancel.clicked.connect(warn_dlg.reject)
        btn_restore.clicked.connect(warn_dlg.accept)
        btn_area.addWidget(btn_cancel)
        btn_area.addWidget(btn_restore)
        warn_layout.addLayout(btn_area)
        
        if warn_dlg.exec():
            # 執行還原
            memory_files = ["WorkSnap_Data/tag_memory.json", "WorkSnap_Data/checkbox_memory.json"]
            for mf in memory_files:
                path = Path(mf)
                if path.exists():
                    try: path.unlink()
                    except: pass
            
            self.config = self.config_mgr.default_config
            self.config_mgr.save_config(self.config)
            
            # --- 2. 成功視窗 (手寫，解決那個藍色半圓問題) ---
            done_dlg = QDialog(self)
            done_dlg.setWindowTitle("完成")
            done_dlg.setFixedSize(350, 150)
            
            done_layout = QVBoxLayout(done_dlg)
            done_layout.setContentsMargins(30, 30, 30, 25)
            
            done_content = QLabel("已還原原廠設定。<br>請重新掃描或重啟應用程式以套用變更。")
            done_content.setWordWrap(True)
            done_content.setStyleSheet("color: #EBEBEA; font-size: 14px;")
            done_layout.addWidget(done_content)
            
            ok_area = QHBoxLayout()
            ok_area.addStretch()
            btn_ok = QPushButton("確 定")
            # 這裡把按鈕加上一點邊框，比較好點擊
            btn_ok.setStyleSheet("QPushButton { color: #EBEBEA !important; background: transparent !important; border: 1px solid #3F3F3F !important; border-radius: 6px !important; padding: 6px 20px; font-weight: bold; } QPushButton:hover { background-color: rgba(255, 255, 255, 0.05) !important; }")
            btn_ok.clicked.connect(done_dlg.accept)
            ok_area.addWidget(btn_ok)
            done_layout.addLayout(ok_area)
            done_dlg.exec()
            
            self.accept()