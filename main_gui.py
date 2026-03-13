import sys
import os

# 1. 環境初始化：解決 COM 與 DPI 警告
os.environ["QT_LOGGING_RULES"] = "qt.qpa.window=false"
sys.coinit_flags = 2 

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTreeWidget, QTreeWidgetItem, QCheckBox, 
                             QLineEdit, QPushButton, QLabel, QProgressBar, 
                             QMessageBox, QTreeWidgetItemIterator)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from core_engine import KeepGoingEngine
from archive_controller import ArchiveController

class ArchiveWorker(QThread):
    """背景存檔執行緒，防止 UI 卡死"""
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

class KeepGoingUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Keep-Going | 下班進度紀錄")
        self.resize(1100, 750)
        self.engine = KeepGoingEngine()
        self.controller = ArchiveController()
        self.init_ui()
        # 初始掃描 (會受下方的 setChecked(True) 影響而執行過濾)
        self.refresh_list()

    def init_ui(self):
            """建立介面佈局並優化操作手感"""
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            main_layout = QVBoxLayout(central_widget)

            # --- 頂部控制列 ---
            top_bar = QHBoxLayout()
            self.status_label = QLabel("正在掃描工作狀態...")
            
            # 修正：預設啟動「聚焦模式」，開啟即隱藏雜訊
            self.filter_checkbox = QCheckBox("僅顯示工作相關 (已分類項目)")
            self.filter_checkbox.setChecked(True) 
            self.filter_checkbox.stateChanged.connect(self.refresh_list)
            
            top_bar.addWidget(self.status_label)
            top_bar.addStretch()
            top_bar.addWidget(self.filter_checkbox)
            main_layout.addLayout(top_bar)

            # --- 中間：樹狀清單 ---
            self.tree = QTreeWidget()
            self.tree.setColumnCount(2)
            self.tree.setHeaderLabels(["視窗項目", "進度備註 (Inline)"])
            self.tree.setColumnWidth(0, 600)
            
            # 修正：優化點擊範圍，當點擊整行標題時自動切換勾選框
            self.tree.itemClicked.connect(self.handle_item_clicked)
            
            main_layout.addWidget(self.tree)

            # --- 底部：功能區 ---
            self.progress_bar = QProgressBar()
            self.progress_bar.setVisible(False)
            main_layout.addWidget(self.progress_bar)

            btn_layout = QHBoxLayout()
            
            # 增加按鈕之間的間距
            btn_layout.setSpacing(10) 

            self.settings_btn = QPushButton("⚙ 系統設定")
            self.settings_btn.clicked.connect(self.open_settings)
            
            self.refresh_btn = QPushButton("🔄 重新掃描")
            self.refresh_btn.clicked.connect(self.refresh_list)
            
            self.archive_btn = QPushButton("確認存檔並下班！")
            self.archive_btn.setFixedHeight(45)
            self.archive_btn.setStyleSheet("""
                QPushButton {
                    background-color: #27ae60; 
                    color: white; 
                    font-weight: bold;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #2ecc71;
                }
            """)
            self.archive_btn.clicked.connect(self.start_archive)
            
            btn_layout.addWidget(self.settings_btn)
            btn_layout.addWidget(self.refresh_btn)
            btn_layout.addWidget(self.archive_btn)
            main_layout.addLayout(btn_layout)

    def handle_item_clicked(self, item, column):
            """當點擊第一欄時，自動切換勾選狀態，提升操作手感 [方案一]"""
            if column == 0:
                # 只有子節點(帶有資料的)才觸發切換
                data = item.data(0, Qt.ItemDataRole.UserRole)
                if data:
                    current_state = item.checkState(0)
                    new_state = Qt.CheckState.Unchecked if current_state == Qt.CheckState.Checked else Qt.CheckState.Checked
                    item.setCheckState(0, new_state)

    def refresh_list(self):
        """掃描視窗並群組化顯示"""
        self.tree.clear()
        raw_items = self.engine.get_full_status()
        
        # 過濾雜訊
        if self.filter_checkbox.isChecked():
            raw_items = [i for i in raw_items if i['category'] != "Uncategorized"]

        # 群組化 (根據 EXE 名稱或 Notion 關鍵字)
        groups = {}
        for item in raw_items:
            exe = item.get('exe', 'Unknown')
            # 針對 Notion 進行特殊群組化優化
            group_key = "Notion Pages" if "notion.so" in item.get('url', '') else exe
            if group_key not in groups: 
                groups[group_key] = []
            groups[group_key].append(item)

        # 渲染樹狀結構
        for group_name, items in groups.items():
            parent = QTreeWidgetItem(self.tree)
            parent.setText(0, f"{group_name} ({len(items)} 個項目)")
            parent.setExpanded(True)

            for data in items:
                child = QTreeWidgetItem(parent)
                child.setText(0, f"[{data['category']}] {data['title'][:70]}")
                
                # 預設勾選策略：未分類的不勾選
                is_checked = data['category'] != "Uncategorized"
                child.setCheckState(0, Qt.CheckState.Checked if is_checked else Qt.CheckState.Unchecked)
                
                # 使用 UserRole 儲存資料字典 [解決 TypeError]
                child.setData(0, Qt.ItemDataRole.UserRole, data)
                
                # 行內備註輸入框
                note_edit = QLineEdit()
                note_edit.setPlaceholderText("快速輸入備註...")
                note_edit.setFrame(False)
                self.tree.setItemWidget(child, 1, note_edit)

        self.status_label.setText(f"掃描完成。偵測到 {len(raw_items)} 個項目。")

    def start_archive(self):
        """收集勾選項目並開始背景存檔"""
        selected_data = []
        it = QTreeWidgetItemIterator(self.tree)
        
        while it.value():
            item = it.value()
            data = item.data(0, Qt.ItemDataRole.UserRole)
            # 只處理帶有資料的子節點且已被勾選的
            if data and item.checkState(0) == Qt.CheckState.Checked:
                note_edit = self.tree.itemWidget(item, 1)
                if note_edit:
                    data['note'] = note_edit.text()
                    selected_data.append(data)
            it += 1

        if not selected_data:
            QMessageBox.warning(self, "警告", "請至少勾選一個項目。")
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
        self.status_label.setText("存檔完成！辛苦了。")
        QMessageBox.information(self, "完成", "今天的努力已成功紀錄。")

    def open_settings(self):
        """開啟外部設定頁面"""
        from settings_dialog import SettingsDialog
        if SettingsDialog(self).exec():
            # 設定更新後通知 scanner 刷新規則
            self.engine.scanner.update_settings()
            self.refresh_list()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion") 
    window = KeepGoingUI()
    window.show()
    sys.exit(app.exec())