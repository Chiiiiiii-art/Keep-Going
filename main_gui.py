# main_gui.py

import sys
import os
import json
import ctypes
import traceback
from urllib.parse import urlparse
from pathlib import Path

# 修正：消除 Windows DPI 權限警告 (放在 QApplication 之前)
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
os.environ["QT_AUTOSCREENSCALEFACTOR"] = "1"

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTreeWidget, QTreeWidgetItem, QCheckBox, 
                             QLineEdit, QPushButton, QLabel, QProgressBar, 
                             QMessageBox, QTreeWidgetItemIterator, QFrame, QMenu, QWidgetAction)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QAction, QColor, QPixmap, QIcon, QPainter, QGuiApplication
from core_engine import KeepGoingEngine
from archive_controller import ArchiveController

# --- 工具函式 ---
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

# --- 功能：時數選擇器 ---
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

# --- 主視窗 ---
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
        footer.setSpacing(25)
        
        self.settings_btn = QPushButton("⚙️ 系統設定"); self.settings_btn.setObjectName("SettingsButton")
        self.refresh_btn = QPushButton("🔄 重新掃描"); self.refresh_btn.setObjectName("RefreshButton")
        self.archive_btn = QPushButton("確認存檔並下班！"); self.archive_btn.setObjectName("ArchiveButton")
        
        self.settings_btn.clicked.connect(self.open_settings); self.refresh_btn.clicked.connect(self.refresh_list); self.archive_btn.clicked.connect(self.start_archive)
        
        footer.addWidget(self.settings_btn); footer.addWidget(self.refresh_btn); footer.addStretch(); footer.addWidget(self.archive_btn)
        main_layout.addLayout(footer)

    def on_item_clicked(self, item, column):
        if item.childCount() > 0: item.setExpanded(not item.isExpanded())

    def get_domain(self, url):
        try: return urlparse(url).netloc.replace("www.", "").split(".")[-2].capitalize()
        except: return "Browser"

    def refresh_list(self):
        self.tree.clear()
        raw_items = self.engine.get_full_status()
        apps = {}
        for item in raw_items:
            id_key = item.get('url') or item['title']
            item['category'] = self.tag_memory.get(id_key, item.get('category'))
            if self.filter_checkbox.isChecked() and item['category'] is None: continue
            exe = item.get('exe', 'Unknown')
            if exe not in apps: apps[exe] = {'normal': [], 'domains': {}}
            is_browser = item.get('type') == 'browser_tab' or exe.lower() in ['chrome.exe', 'edge.exe', 'brave.exe', 'firefox.exe', 'comet.exe']
            if is_browser and 'url' in item and item['url']:
                dom = self.get_domain(item['url'])
                apps[exe]['domains'].setdefault(dom, []).append(item)
            else: apps[exe]['normal'].append(item)

        for exe, data in apps.items():
            exe_node = QTreeWidgetItem(self.tree); exe_node.setText(0, f"💻 {exe}")
            exe_has_tagged = False
            for d in data['normal']:
                self._add_tree_item(exe_node, d)
                if d.get('category') is not None: exe_has_tagged = True
            for dom, d_items in data['domains'].items():
                dom_node = QTreeWidgetItem(exe_node); dom_node.setText(0, f"🌐 {dom}")
                dom_has_tagged = False
                for d in d_items:
                    self._add_tree_item(dom_node, d)
                    if d.get('category') is not None: dom_has_tagged = True; exe_has_tagged = True
                dom_node.setExpanded(dom_has_tagged)
            exe_node.setExpanded(exe_has_tagged)
        self.status_label.setText(f"目前顯示 {self.tree.topLevelItemCount()} 個應用程式群組")

    def _add_tree_item(self, parent, data):
        child = QTreeWidgetItem(parent)
        child.setText(0, data['title'][:75])
        child.setData(0, Qt.ItemDataRole.UserRole, data)
        container = QWidget(); layout = QHBoxLayout(container); layout.setContentsMargins(5, 0, 5, 0); layout.setSpacing(15)
        
        # 傳入 child 參數，確保分類變更時能同步 TreeItem 資料
        self.create_tag_picker(data, container, child)
        
        dur_widget = DurationWidget(); dur_widget.set_active(data.get('category') is not None); layout.addWidget(dur_widget)
        note = HoverLineEdit(data.get('note', '')); note.setPlaceholderText("在此輸入進度備註..."); note.setObjectName("NoteEdit"); layout.addWidget(note)
        self.tree.setItemWidget(child, 1, container)

    def create_tag_picker(self, data, container, item):
        cat_map = self.engine.scanner.config_mgr.get_category_map()
        tag_name = data.get('category')
        if tag_name and tag_name in cat_map:
            info = cat_map[tag_name]; style = info["style"]
            btn_text = f"{info['icon']} {tag_name}".strip()
            btn_style = f"background-color: {style['bg']}; color: white; border: {style['border']}; border-radius: 4px; font-weight: bold; font-size: 11px; padding: 6px 10px;"
        else:
            btn_text = "(未分類)"; btn_style = "background-color: transparent; color: #555555; border: 1px dashed #333333; border-radius: 4px; font-weight: bold; font-size: 11px; padding: 6px 10px;"
        
        btn = QPushButton(btn_text); btn.setObjectName("TagButton"); btn.setFixedWidth(120); btn.setStyleSheet(btn_style)
        menu = QMenu(self)
        for name, inf in cat_map.items():
            action = QAction(name, self); action.setIcon(create_emoji_icon(inf['icon']))
            # 同步將 item 傳入 change_category
            action.triggered.connect(lambda chk, c=name, d=data, cnr=container, it=item: self.change_category(d, c, cnr, it))
            menu.addAction(action)
        menu.addSeparator()
        clear_widget = ClearTagWidget()
        clear_widget.clicked.connect(lambda it=item: (self.change_category(data, None, container, it), menu.close()))
        clear_action = QWidgetAction(self); clear_action.setDefaultWidget(clear_widget); menu.addAction(clear_action)
        btn.setMenu(menu); container.layout().insertWidget(0, btn)

    def change_category(self, data, new_cat, container, item):
        # 1. 更新記憶體資料
        data['category'] = new_cat
        # 2. 關鍵修正：將更新後的資料寫入 TreeItem 的 UserRole，解決存檔抓不到標籤的問題
        item.setData(0, Qt.ItemDataRole.UserRole, data)
        
        id_key = data.get('url') or data['title']
        if new_cat is None: 
            self.tag_memory.pop(id_key, None)
            try:
                with open(self.memory_file, 'w', encoding='utf-8') as f: json.dump(self.tag_memory, f, ensure_ascii=False)
            except: pass
        else: self.save_memory(id_key, new_cat)
            
        if self.filter_checkbox.isChecked() and new_cat is None:
            self.refresh_list()
        else:
            for i in reversed(range(container.layout().count())):
                w = container.layout().itemAt(i).widget()
                if isinstance(w, QPushButton) and w.objectName() == "TagButton": w.setParent(None)
                elif isinstance(w, DurationWidget): w.set_active(new_cat is not None)
            self.create_tag_picker(data, container, item)

    def start_archive(self):
        try:
            selected = []
            it = QTreeWidgetItemIterator(self.tree)
            while it.value():
                item = it.value(); data = item.data(0, Qt.ItemDataRole.UserRole)
                if data and data.get('category') is not None:
                    # 關鍵：從 UI 元件抓取使用者輸入的最新 備註 與 時數
                    container = self.tree.itemWidget(item, 1)
                    if container:
                        for i in range(container.layout().count()):
                            w = container.layout().itemAt(i).widget()
                            if not w: continue
                            if w.objectName() == "NoteEdit": data['note'] = w.text()
                            elif w.objectName() == "DurationLabel": data['duration'] = getattr(w, 'hours', 0.0)
                    selected.append(data)
                it += 1
            
            if not selected:
                print("⚠️ 後臺提醒：目前清單中沒有任何已分類項目可供存檔。")
                msg = QMessageBox(self); msg.setIcon(QMessageBox.Icon.Warning); msg.setWindowTitle("提示")
                msg.setText("目前沒有已分類的項目可供存檔。"); msg.setInformativeText("請先點擊項目旁邊的標籤按鈕設定分類。")
                msg.setStyleSheet("QLabel { min-width: 280px; min-height: 40px; }") # 修復三角形顯示問題
                msg.exec(); return

            print(f"🚀 開始存檔流程，共處理 {len(selected)} 筆項目...")
            self.controller.run_archive_flow(selected)
            QMessageBox.information(self, "完成", "存檔已成功！")
        except Exception as e:
            print(f"❌ 存檔錯誤：\n{traceback.format_exc()}")
            QMessageBox.critical(self, "錯誤", f"存檔失敗: {str(e)}")

    def open_settings(self):
        try:
            from settings_dialog import SettingsDialog
            if SettingsDialog(self).exec(): self.engine.scanner.update_settings(); self.refresh_list()
        except Exception as e: print(f"❌ 無法開啟設定：{e}")

if __name__ == "__main__":
    app = QApplication(sys.argv); app.setStyle("Fusion")
    base_path = Path(__file__).resolve().parent; qss_path = base_path / "style.qss"
    if qss_path.exists(): app.setStyleSheet(qss_path.read_text(encoding="utf-8"))
    w = KeepGoingUI(); w.show()
    sys.exit(app.exec())