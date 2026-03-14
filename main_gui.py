import sys
import os
import json
import ctypes # 新增：用於解決 DPI 造成的黑屏
from urllib.parse import urlparse
from pathlib import Path

# --- 核心修正：強制開啟 Windows DPI 感知，解決高解析度螢幕 PS 截圖黑屏/偏移問題 ---
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2) # PROCESS_PER_MONITOR_DPI_AWARE
except Exception:
    ctypes.windll.user32.SetProcessDPIAware()

# 環境初始化
sys.coinit_flags = 2 
os.environ["QT_LOGGING_RULES"] = "qt.qpa.window=false"

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTreeWidget, QTreeWidgetItem, QCheckBox, 
                             QLineEdit, QPushButton, QLabel, QProgressBar, 
                             QMessageBox, QTreeWidgetItemIterator, QFrame, QMenu)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QAction
from core_engine import KeepGoingEngine
from archive_controller import ArchiveController

class HoverLineEdit(QLineEdit):
    """自定義輸入框：滑鼠懸停時自動獲得焦點"""
    def enterEvent(self, event):
        self.setFocus()
        super().enterEvent(event)

class ArchiveWorker(QThread):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(str)

    def __init__(self, controller, selected_data):
        super().__init__()
        self.controller = controller
        self.selected_data = selected_data

    def run(self):
        for i, item in enumerate(self.selected_data):
            self.progress.emit(int((i / len(self.selected_data)) * 100), item['title'])
            self.controller.run_archive_flow([item])
        self.finished.emit("完成")
class DurationWidget(QLabel):
    """自定義工時選擇組件：支援滑鼠滾輪以 0.5h 為單位增減"""
    def __init__(self, parent=None):
        super().__init__("0.0h", parent)
        self.hours = 0.0
        self.setFixedWidth(60)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setObjectName("DurationLabel")
        self.setCursor(Qt.CursorShape.SizeVerCursor) # 提示使用者可以上下捲動

    def wheelEvent(self, event):
        # 取得滾輪方向 (delta > 0 為向上捲動)
        delta = event.angleDelta().y()
        if delta > 0:
            self.hours += 0.5
        elif delta < 0 and self.hours >= 0.5:
            self.hours -= 0.5
        
        self.setText(f"{self.hours:.1f}h")
        event.accept()

class KeepGoingUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Keep-Going | 下班進度紀錄")
        self.resize(1100, 750)
        
        self.engine = KeepGoingEngine()
        self.controller = ArchiveController()
        
        self.load_memory()
        self.init_ui()
        self.refresh_list()

    def load_memory(self):
        self.memory_file = Path("WorkSnap_Data/tag_memory.json")
        self.tag_memory = {}
        if self.memory_file.exists():
            try:
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    self.tag_memory = json.load(f)
            except: pass

    def save_memory(self, identifier, tag):
        self.tag_memory[identifier] = tag
        try:
            self.memory_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(self.tag_memory, f, ensure_ascii=False)
        except: pass

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(30, 30, 30, 20)
        main_layout.setSpacing(15)

        # 頂部控制列
        top_bar = QHBoxLayout()
        self.status_label = QLabel("正在掃描工作狀態...")
        self.status_label.setObjectName("SubTitleLabel")
        
        self.filter_checkbox = QCheckBox("僅顯示已分類項目")
        self.filter_checkbox.setChecked(True) 
        self.filter_checkbox.stateChanged.connect(self.refresh_list)
        
        top_bar.addWidget(self.status_label)
        top_bar.addStretch()
        top_bar.addWidget(self.filter_checkbox)
        main_layout.addLayout(top_bar)

        # 樹狀清單
        self.tree = QTreeWidget()
        self.tree.setColumnCount(2)
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(20)
        self.tree.setColumnWidth(0, 580)
        self.tree.setFrameShape(QFrame.Shape.NoFrame)
        self.tree.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.tree.setSelectionMode(QTreeWidget.SelectionMode.NoSelection)
        self.tree.setRootIsDecorated(True) 
        
        self.tree.itemClicked.connect(self.handle_item_clicked)
        main_layout.addWidget(self.tree)

        # 底部
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)

        footer_layout = QHBoxLayout()
        
        # 綁定專屬 ID 以利 QSS 樣式設定
        self.settings_btn = QPushButton("⚙️ 系統設定")
        self.settings_btn.setObjectName("SettingsButton")
        self.settings_btn.setFixedWidth(120)
        self.settings_btn.clicked.connect(self.open_settings)
        
        self.refresh_btn = QPushButton("🔄 重新掃描")
        self.refresh_btn.setObjectName("RefreshButton")
        self.refresh_btn.setFixedWidth(120)
        self.refresh_btn.clicked.connect(self.refresh_list)
        
        self.archive_btn = QPushButton("確認存檔並下班！")
        self.archive_btn.setObjectName("ArchiveButton")
        self.archive_btn.clicked.connect(self.start_archive)
        
        footer_layout.addWidget(self.settings_btn)
        footer_layout.addWidget(self.refresh_btn)
        footer_layout.addStretch()
        footer_layout.addWidget(self.archive_btn)
        main_layout.addLayout(footer_layout)

    def get_domain_name(self, url):
        try:
            netloc = urlparse(url).netloc.replace("www.", "")
            parts = netloc.split(".")
            return parts[-2].capitalize() if len(parts) >= 2 else netloc.capitalize()
        except: return "Unknown"

    def refresh_list(self):
        self.tree.clear()
        raw_items = self.engine.get_full_status()
        
        apps, browser_tabs = {}, {}
        for item in raw_items:
            identifier = item.get('url') or item['title']
            if identifier in self.tag_memory:
                item['category'] = self.tag_memory[identifier]

            if self.filter_checkbox.isChecked() and item['category'] == "Uncategorized":
                continue

            exe = item.get('exe', 'Unknown')
            if item.get('type') == 'browser_tab' or exe.lower() == 'comet.exe':
                domain = self.get_domain_name(item.get('url', ''))
                browser_tabs.setdefault(domain, []).append(item)
            else:
                apps.setdefault(exe, []).append(item)

        # --- 渲染 App 與修正展開邏輯 ---
        for exe_name, items in apps.items():
            parent = QTreeWidgetItem(self.tree)
            parent.setText(0, f"💻 {exe_name}")
            # 判斷是否包含已分類項目
            has_tagged = any(d.get('category', 'Uncategorized') != 'Uncategorized' for d in items)
            parent.setExpanded(has_tagged)
            parent.setForeground(0, Qt.GlobalColor.gray)
            for data in items: self._add_tree_item(parent, data)

        # --- 渲染瀏覽器分頁與修正展開邏輯 ---
        if browser_tabs:
            b_parent = QTreeWidgetItem(self.tree)
            b_parent.setText(0, "🌐 Comet.exe (分頁)")
            has_any_tagged_browser = False

            for domain, items in browser_tabs.items():
                has_tagged = any(d.get('category', 'Uncategorized') != 'Uncategorized' for d in items)
                if has_tagged:
                    has_any_tagged_browser = True

                d_node = QTreeWidgetItem(b_parent)
                d_node.setText(0, f"📁 {domain}")
                d_node.setExpanded(has_tagged)
                for data in items: self._add_tree_item(d_node, data)
                
            b_parent.setExpanded(has_any_tagged_browser)

        self.status_label.setText(f"目前顯示 {self.tree.topLevelItemCount()} 個群組")

    def _add_tree_item(self, parent_node, data):
        child = QTreeWidgetItem(parent_node)
        child.setText(0, data['title'][:75])
        child.setData(0, Qt.ItemDataRole.UserRole, data)
        
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(5, 0, 5, 0)
        layout.setSpacing(15)

        # 1. 標籤按鈕
        tag_btn = self.create_tag_picker(data, container)
        
        # 2. 新增：工時選擇器 (0.5h 單位)
        duration_picker = DurationWidget()
        layout.addWidget(duration_picker)
        
        # 3. 備註框
        note_edit = HoverLineEdit()
        note_edit.setPlaceholderText("在此輸入進度備註...")
        note_edit.setFrame(False)
        note_edit.setStyleSheet("background: transparent; color: #9B9A97; font-size: 13px;")
        layout.addWidget(note_edit)
        
        self.tree.setItemWidget(child, 1, container)

    def create_tag_picker(self, data, container):
        tag_name = data.get('category', 'Uncategorized')
        display_name = "(無標籤)" if tag_name == "Uncategorized" else tag_name
        icon_map = {"Art": "🎨 ", "Dev": "💻 ", "Writing": "📝 ", "Uncategorized": ""}
        
        btn = QPushButton(f"{icon_map.get(tag_name, '')}{display_name}")
        btn.setObjectName("TagButton")
        btn.setFixedWidth(110)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        
        colors = {
            "Art": "background-color: #4D2D2D; color: #FFA3A3;",
            "Dev": "background-color: #2D3D4D; color: #A3D1FF;",
            "Writing": "background-color: #2D4D3D; color: #A3FFD1;",
            "Uncategorized": "background-color: transparent; color: #555; border: 1px dashed #333;"
        }
        btn.setStyleSheet(f"QPushButton {{ {colors.get(tag_name)} border-radius: 4px; padding: 2px 5px; font-size: 11px; font-weight: bold; border: none; }}")

        menu = QMenu(self)
        for cat in ["Art", "Dev", "Writing", "Uncategorized"]:
            action = QAction(f"{icon_map.get(cat, '')}{cat if cat != 'Uncategorized' else '清除標籤'}", self)
            action.triggered.connect(lambda chk, c=cat, d=data, cnr=container: self.change_category(d, c, cnr))
            menu.addAction(action)
        btn.setMenu(menu)
        
        container.layout().insertWidget(0, btn)
        return btn

    def change_category(self, data, new_cat, container):
        data['category'] = new_cat
        identifier = data.get('url') or data['title']
        
        if new_cat == "Uncategorized":
            self.tag_memory.pop(identifier, None) 
        else:
            self.save_memory(identifier, new_cat)
            
        for i in reversed(range(container.layout().count())):
            w = container.layout().itemAt(i).widget()
            if isinstance(w, QPushButton) and w.objectName() == "TagButton":
                w.setParent(None)
        self.create_tag_picker(data, container)

    def handle_item_clicked(self, item, column):
        if item.childCount() > 0:
            item.setExpanded(not item.isExpanded())
        self.tree.clearSelection()

    def start_archive(self):
        selected_data = []
        it = QTreeWidgetItemIterator(self.tree)
        while it.value():
            item = it.value()
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if data and data.get('category') != "Uncategorized":
                container = self.tree.itemWidget(item, 1)
                if container:
                    for i in range(container.layout().count()):
                        w = container.layout().itemAt(i).widget()
                        if isinstance(w, QLineEdit):
                            data['note'] = w.text()
                        # 新增：收集工時資訊
                        elif isinstance(w, DurationWidget):
                            data['duration'] = w.hours
                selected_data.append(data)
            it += 1

        if not selected_data:
            QMessageBox.warning(self, "提示", "目前沒有已分類的項目可供存檔。")
            return

        self.archive_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.worker = ArchiveWorker(self.controller, selected_data)
        self.worker.progress.connect(lambda val, title: self.progress_bar.setValue(val))
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def on_finished(self):
        self.archive_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        QMessageBox.information(self, "完成", "今天的努力已成功紀錄！")

    def open_settings(self):
        from settings_dialog import SettingsDialog
        if SettingsDialog(self).exec():
            self.engine.scanner.update_settings()
            self.refresh_list()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    qss_path = Path("style.qss")
    if qss_path.exists(): app.setStyleSheet(qss_path.read_text(encoding="utf-8"))
    window = KeepGoingUI()
    window.show()
    sys.exit(app.exec())