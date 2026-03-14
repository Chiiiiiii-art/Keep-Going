import sys
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, 
                             QWidget, QLabel, QLineEdit, QPushButton, QListWidget, 
                             QInputDialog, QComboBox, QFrame, QListWidgetItem)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor, QPixmap, QIcon, QPainter
from settings_manager import ConfigManager, TAG_THEMES

def create_color_icon(hex_color, size=14):
    """根據十六進位顏色產生一個圓角方塊圖標"""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(hex_color))
    painter.setPen(Qt.PenStyle.NoPen)
    # 繪製帶有 4px 圓角的方塊
    painter.drawRoundedRect(0, 0, size, size, 4, 4)
    painter.end()
    return QIcon(pixmap)

class CategoryEditDialog(QDialog):
    """新增/編輯標籤的對話框 - Notion 風格精簡版"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("新增分類標籤")
        self.setFixedWidth(350)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)
        
        # 標題與輸入
        layout.addWidget(QLabel("分類名稱"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("輸入專案或領域名稱...")
        layout.addWidget(self.name_input)
        
        layout.addWidget(QLabel("Emoji 圖示"))
        self.icon_input = QLineEdit()
        self.icon_input.setPlaceholderText("貼上一個 Emoji (如 🎨, 💻)...")
        layout.addWidget(self.icon_input)
        
        layout.addWidget(QLabel("標籤色調"))
        self.theme_combo = QComboBox()
        # 加入顏色圖標
        for theme_name, theme_data in TAG_THEMES.items():
            if theme_name == "Uncategorized": continue
            icon = create_color_icon(theme_data["fg"])
            self.theme_combo.addItem(icon, theme_name)
        layout.addWidget(self.theme_combo)
        
        layout.addSpacing(15)
        
        btns = QHBoxLayout()
        btns.setSpacing(10)

        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("SettingsButton")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)

        ok_btn = QPushButton("確認建立")
        ok_btn.setObjectName("ArchiveButton") 
        ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        ok_btn.clicked.connect(self.accept)
        
        btns.addStretch()
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
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(20)

        # --- 頂部標題 ---
        header_title = QLabel("系統規則設定")
        header_title.setObjectName("TitleLabel")
        header_title.setStyleSheet("font-size: 20px;")
        layout.addWidget(header_title)

        # --- 分頁系統樣式化 ---
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border-top: 1px solid rgba(255, 255, 255, 0.05); background: transparent; }
            QTabBar::tab { background: transparent; padding: 10px 20px; color: #9B9A97; }
            QTabBar::tab:selected { color: #EBEBEA; border-bottom: 2px solid #EBEBEA; }
        """)

        # 分頁 1: 標籤管理
        self.cat_tab = QWidget()
        cat_layout = QVBoxLayout(self.cat_tab)
        cat_layout.setContentsMargins(0, 15, 0, 0)
        
        cat_layout.addWidget(QLabel("<b>專屬分類標籤</b>"))
        cat_desc = QLabel("在此定義你想要追蹤的專案或領域")
        cat_desc.setObjectName("SubTitleLabel")
        cat_layout.addWidget(cat_desc)
        
        self.cat_list = QListWidget()
        self.cat_list.setIconSize(QSize(14, 14))
        self.refresh_cat_list()
        cat_layout.addWidget(self.cat_list)

        cat_btn_layout = QHBoxLayout()
        add_cat_btn = QPushButton("➕ 新增標籤")
        add_cat_btn.setObjectName("SettingsButton")
        add_cat_btn.clicked.connect(self.add_category)
        
        del_cat_btn = QPushButton("🗑 刪除選中")
        del_cat_btn.setObjectName("SettingsButton")
        del_cat_btn.clicked.connect(self.delete_category)
        
        cat_btn_layout.addWidget(add_cat_btn)
        cat_btn_layout.addWidget(del_cat_btn)
        cat_btn_layout.addStretch()
        cat_layout.addLayout(cat_btn_layout)

        # 分頁 2: 程序過濾
        self.blacklist_tab = QWidget()
        black_layout = QVBoxLayout(self.blacklist_tab)
        black_layout.setContentsMargins(0, 15, 0, 0)
        
        black_layout.addWidget(QLabel("<b>程序黑名單</b>"))
        black_desc = QLabel("被加入的程序名稱將不會出現在掃描清單中")
        black_desc.setObjectName("SubTitleLabel")
        black_layout.addWidget(black_desc)
        
        self.black_exe_list = QListWidget()
        self.black_exe_list.addItems(self.config.get("blacklist_exes", []))
        black_layout.addWidget(self.black_exe_list)
        
        black_btn_layout = QHBoxLayout()
        add_exe_btn = QPushButton("➕ 新增程序")
        add_exe_btn.setObjectName("SettingsButton")
        add_exe_btn.clicked.connect(self.add_exe)
        
        del_exe_btn = QPushButton("🗑 刪除選中")
        del_exe_btn.setObjectName("SettingsButton")
        del_exe_btn.clicked.connect(self.delete_exe)
        
        black_btn_layout.addWidget(add_exe_btn)
        black_btn_layout.addWidget(del_exe_btn)
        black_btn_layout.addStretch()
        black_layout.addLayout(black_btn_layout)
        
        self.tabs.addTab(self.cat_tab, "標籤管理")
        self.tabs.addTab(self.blacklist_tab, "過濾設定")
        layout.addWidget(self.tabs)

        # --- 底部功能按鈕 ---
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: rgba(255, 255, 255, 0.05); min-height: 1px;")
        layout.addWidget(line)

        buttons = QHBoxLayout()
        buttons.setSpacing(12)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("SettingsButton")
        cancel_btn.clicked.connect(self.reject)
        
        save_btn = QPushButton("儲存設定")
        save_btn.setObjectName("ArchiveButton")
        save_btn.clicked.connect(self.save_and_close)
        
        buttons.addStretch()
        buttons.addWidget(cancel_btn)
        buttons.addWidget(save_btn)
        layout.addLayout(buttons)

    def refresh_cat_list(self):
        """將色彩方塊結合標籤，確保視覺一致性"""
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

    def delete_category(self):
        row = self.cat_list.currentRow()
        if row >= 0:
            del self.config["categories"][row]
            self.refresh_cat_list()

    def add_exe(self):
        exe, ok = QInputDialog.getText(self, "新增程序", "請輸入程序名稱 (例如: obsidian.exe):")
        if ok and exe:
            self.black_exe_list.addItem(exe)

    def delete_exe(self):
        item = self.black_exe_list.currentItem()
        if item:
            self.black_exe_list.takeItem(self.black_exe_list.row(item))

    def save_and_close(self):
        self.config["blacklist_exes"] = [self.black_exe_list.item(i).text() for i in range(self.black_exe_list.count())]
        self.config_mgr.save_config(self.config)
        self.accept()