import sys
import os
import json
import ctypes
from urllib.parse import urlparse
from pathlib import Path

# --- 核心修正：強制開啟 Windows DPI 感知 ---
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2) 
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTreeWidget, QTreeWidgetItem, QCheckBox, 
                             QLineEdit, QPushButton, QLabel, QProgressBar, 
                             QMessageBox, QTreeWidgetItemIterator, QFrame, QMenu, QWidgetAction)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QAction, QColor, QPixmap, QIcon, QPainter, QGuiApplication
from core_engine import KeepGoingEngine
from archive_controller import ArchiveController

def create_emoji_icon(emoji_char, size=20):
    if not emoji_char: return QIcon()
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    font = painter.font()
    font.setPointSize(size - 6)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, emoji_char)
    painter.end()
    return QIcon(pixmap)

# --- 功能：懸停自動聚焦的輸入框 ---
class HoverLineEdit(QLineEdit):
    def enterEvent(self, event):
        self.setFocus()
        super().enterEvent(event)

# --- 功能：時數選擇器 (修正：支援禁用狀態回饋) ---
class DurationWidget(QLabel):
    def __init__(self, parent=None):
        super().__init__("0.0h", parent)
        self.hours = 0.0
        self.setFixedWidth(60)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setObjectName("DurationLabel")
        self.setMouseTracking(True)
        self.active = True
        self.set_style(False)

    def set_active(self, active):
        self.active = active
        self.set_style(False)
        self.setCursor(Qt.CursorShape.SizeVerCursor if active else Qt.CursorShape.ArrowCursor)

    def set_style(self, is_hover):
        if not self.active:
            # 禁用狀態：半透明、無邊框感
            self.setStyleSheet("background-color: rgba(255,255,255,0.02); color: #444; border: 1px solid #222; border-radius: 4px; font-size: 11px; font-weight: bold; padding: 4px 0px;")
            return
            
        color = "#EBEBEA" if is_hover else "#9B9A97"
        border = "1px solid #666666" if is_hover else "1px solid #333333"
        bg = "#2C2C2C" if is_hover else "#262626"
        self.setStyleSheet(f"background-color: {bg}; color: {color}; border: {border}; border-radius: 4px; font-size: 11px; font-weight: bold; padding: 4px 0px;")

    def enterEvent(self, event): self.set_style(True)
    def leaveEvent(self, event): self.set_style(False)
    
    def wheelEvent(self, event):
        if not self.active: return
        delta = event.angleDelta().y()
        if delta > 0: self.hours += 0.5
        elif delta < 0 and self.hours >= 0.5: self.hours -= 0.5
        self.setText(f"{self.hours:.1f}h")
        event.accept()

class ClearTagWidget(QLabel):
    clicked = pyqtSignal()
    def __init__(self, parent=None):
        super().__init__("清除標籤", parent)
        self.setMouseTracking(True)
        self.set_style(False)
        self.setContentsMargins(12, 8, 12, 8)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_style(self, is_hover):
        color = "#FF4D4D" if is_hover else "white"
        self.setStyleSheet(f"color: {color}; font-weight: bold; background: transparent; font-size: 13px; border: none;")

    def enterEvent(self, event): self.set_style(True)
    def leaveEvent(self, event): self.set_style(False)
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton: self.clicked.emit()

class KeepGoingUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Keep-Going | 下班進度紀錄")
        self.resize(1100, 750)
        self.center_window()
        self.engine = KeepGoingEngine()
        self.controller = ArchiveController()
        self.load_memory()
        self.init_ui()
        self.refresh_list()

    def center_window(self):
        screen = QGuiApplication.primaryScreen()
        if screen:
            rect = screen.availableGeometry()
            self.move(rect.left() + (rect.width() - self.width()) // 2,
                      rect.top() + (rect.height() - self.height()) // 2)

    def load_memory(self):
        self.memory_file = Path("WorkSnap_Data/tag_memory.json")
        self.tag_memory = {}
        if self.memory_file.exists():
            try:
                with open(self.memory_file, 'r', encoding='utf-8') as f: self.tag_memory = json.load(f)
            except: pass

    def save_memory(self, identifier, tag):
        self.tag_memory[identifier] = tag
        try:
            self.memory_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.memory_file, 'w', encoding='utf-8') as f: json.dump(self.tag_memory, f, ensure_ascii=False)
        except: pass

    def init_ui(self):
        central_widget = QWidget(); self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget); main_layout.setContentsMargins(30, 30, 30, 20); main_layout.setSpacing(15)

        top_bar = QHBoxLayout()
        self.status_label = QLabel("正在掃描工作狀態..."); self.status_label.setObjectName("SubTitleLabel")
        self.filter_checkbox = QCheckBox("僅顯示已分類項目"); self.filter_checkbox.setChecked(True)
        self.filter_checkbox.stateChanged.connect(self.refresh_list)
        top_bar.addWidget(self.status_label); top_bar.addStretch(); top_bar.addWidget(self.filter_checkbox)
        main_layout.addLayout(top_bar)

        self.tree = QTreeWidget(); self.tree.setColumnCount(2); self.tree.setHeaderHidden(True)
        self.tree.setColumnWidth(0, 550); self.tree.setFrameShape(QFrame.Shape.NoFrame); self.tree.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.tree.itemClicked.connect(self.on_item_clicked)
        main_layout.addWidget(self.tree)

        footer = QHBoxLayout()
        footer.setSpacing(25) # 增加左下按鈕間距
        
        self.settings_btn = QPushButton("⚙️ 系統設定"); self.settings_btn.setObjectName("SettingsButton")
        self.refresh_btn = QPushButton("🔄 重新掃描"); self.refresh_btn.setObjectName("RefreshButton")
        self.archive_btn = QPushButton("確認存檔並下班！"); self.archive_btn.setObjectName("ArchiveButton")
        
        self.settings_btn.clicked.connect(self.open_settings); self.refresh_btn.clicked.connect(self.refresh_list); self.archive_btn.clicked.connect(self.start_archive)
        
        footer.addWidget(self.settings_btn); footer.addWidget(self.refresh_btn); footer.addStretch(); footer.addWidget(self.archive_btn)
        main_layout.addLayout(footer)

    def on_item_clicked(self, item, column):
        if item.childCount() > 0: item.setExpanded(not item.isExpanded())

    def refresh_list(self):
        self.tree.clear()
        raw_items = self.engine.get_full_status()
        cat_map = self.engine.scanner.config_mgr.get_category_map()
        
        apps = {}
        for item in raw_items:
            id_key = item.get('url') or item['title']
            if id_key in self.tag_memory: item['category'] = self.tag_memory[id_key]
            else: item['category'] = item.get('category', 'Uncategorized')
                
            if item['category'] not in cat_map: item['category'] = 'Uncategorized'
            if self.filter_checkbox.isChecked() and item['category'] == "Uncategorized": continue
                
            exe = item.get('exe', 'Unknown')
            if exe not in apps: apps[exe] = {'normal': [], 'domains': {}}
            is_browser = item.get('type') == 'browser_tab' or exe.lower() in ['chrome.exe', 'edge.exe', 'brave.exe', 'firefox.exe', 'comet.exe']
            
            if is_browser and 'url' in item and item['url']:
                dom = self.get_domain(item.get('url'))
                apps[exe]['domains'].setdefault(dom, []).append(item)
            else:
                apps[exe]['normal'].append(item)

        for exe, data in apps.items():
            exe_node = QTreeWidgetItem(self.tree); exe_node.setText(0, f"💻 {exe}"); exe_node.setForeground(0, QColor("#9B9A97"))
            exe_has_tagged = False
            for d in data['normal']:
                self._add_tree_item(exe_node, d)
                if d.get('category') != 'Uncategorized': exe_has_tagged = True
            for dom, d_items in data['domains'].items():
                dom_node = QTreeWidgetItem(exe_node); dom_node.setText(0, f"🌐 {dom}"); dom_node.setForeground(0, QColor("#9B9A97"))
                dom_has_tagged = False
                for d in d_items:
                    self._add_tree_item(dom_node, d)
                    if d.get('category') != 'Uncategorized': dom_has_tagged = True; exe_has_tagged = True
                dom_node.setExpanded(dom_has_tagged)
            exe_node.setExpanded(exe_has_tagged)
        self.status_label.setText(f"目前顯示 {self.tree.topLevelItemCount()} 個應用程式群組")

    def get_domain(self, url):
        try: return urlparse(url).netloc.replace("www.", "").split(".")[-2].capitalize()
        except: return "Browser"

    def _add_tree_item(self, parent, data):
        child = QTreeWidgetItem(parent)
        child.setText(0, data['title'][:75]); child.setData(0, Qt.ItemDataRole.UserRole, data)
        container = QWidget(); layout = QHBoxLayout(container); layout.setContentsMargins(5, 0, 5, 0); layout.setSpacing(15)
        
        self.create_tag_picker(data, container)
        
        # --- 修正：旋鈕不消失，僅改變啟用狀態 ---
        dur_widget = DurationWidget()
        dur_widget.set_active(data.get('category', 'Uncategorized') != "Uncategorized")
        layout.addWidget(dur_widget)
        
        note = HoverLineEdit(data.get('note', ''))
        note.setPlaceholderText("在此輸入進度備註..."); note.setObjectName("NoteEdit")
        layout.addWidget(note)
        self.tree.setItemWidget(child, 1, container)

    def create_tag_picker(self, data, container):
        cat_map = self.engine.scanner.config_mgr.get_category_map()
        tag_name = data.get('category', 'Uncategorized')
        if tag_name not in cat_map: tag_name = "Uncategorized"
        info = cat_map[tag_name]; style = info["style"]
        
        btn = QPushButton(f"{info['icon']} {tag_name if tag_name != 'Uncategorized' else '(無標籤)'}".strip())
        btn.setObjectName("TagButton"); btn.setFixedWidth(120); btn.setCursor(Qt.CursorShape.PointingHandCursor)
        # --- 修正：增加垂直 padding (上下內距) 讓標籤更寬敞 ---
        btn.setStyleSheet(f"background-color: {style['bg']}; color: white; border: {style['border']}; border-radius: 4px; font-weight: bold; font-size: 11px; padding: 6px 10px;")

        menu = QMenu(self); menu.setCursor(Qt.CursorShape.PointingHandCursor)
        for name, inf in cat_map.items():
            if name == "Uncategorized": continue
            action = QAction(name, self); action.setIcon(create_emoji_icon(inf['icon']))
            action.triggered.connect(lambda chk, c=name, d=data, cnr=container: self.change_category(d, c, cnr))
            menu.addAction(action)
        menu.addSeparator()
        clear_action = QWidgetAction(self); clear_widget = ClearTagWidget()
        clear_widget.clicked.connect(lambda: (self.change_category(data, "Uncategorized", container), menu.close()))
        clear_action.setDefaultWidget(clear_widget); menu.addAction(clear_action)
        btn.setMenu(menu); container.layout().insertWidget(0, btn)

    def change_category(self, data, new_cat, container):
        data['category'] = new_cat
        id_key = data.get('url') or data['title']
        if new_cat == "Uncategorized": 
            self.tag_memory.pop(id_key, None)
            with open(self.memory_file, 'w', encoding='utf-8') as f: json.dump(self.tag_memory, f, ensure_ascii=False)
        else: self.save_memory(id_key, new_cat)
            
        if self.filter_checkbox.isChecked() and new_cat == "Uncategorized":
            self.refresh_list()
        else:
            # --- 修正：不刪除 DurationWidget，而是切換其狀態 ---
            for i in reversed(range(container.layout().count())):
                w = container.layout().itemAt(i).widget()
                if isinstance(w, QPushButton) and w.objectName() == "TagButton": w.setParent(None)
                elif isinstance(w, DurationWidget): w.set_active(new_cat != "Uncategorized")
            self.create_tag_picker(data, container)

    def start_archive(self):
        selected = []
        it = QTreeWidgetItemIterator(self.tree)
        while it.value():
            item = it.value(); data = item.data(0, Qt.ItemDataRole.UserRole)
            if data and data.get('category') != "Uncategorized":
                cnr = self.tree.itemWidget(item, 1)
                if cnr:
                    for i in range(cnr.layout().count()):
                        w = cnr.layout().itemAt(i).widget()
                        if isinstance(w, QLineEdit): data['note'] = w.text()
                        elif isinstance(w, DurationWidget): data['duration'] = w.hours
                selected.append(data)
            it += 1
        if not selected: return QMessageBox.warning(self, "提示", "目前沒有已分類的項目可供存檔。")
        self.controller.run_archive_flow(selected)
        QMessageBox.information(self, "完成", "存檔已成功！")

    def open_settings(self):
        from settings_dialog import SettingsDialog
        if SettingsDialog(self).exec(): self.engine.scanner.update_settings(); self.refresh_list()

if __name__ == "__main__":
    app = QApplication(sys.argv); app.setStyle("Fusion")
    qss = Path("style.qss")
    if qss.exists(): app.setStyleSheet(qss.read_text(encoding="utf-8"))
    w = KeepGoingUI(); w.show(); sys.exit(app.exec())