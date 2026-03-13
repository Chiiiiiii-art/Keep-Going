import sys
import os

os.environ["QT_MACOS_DISABLE_SCREEN_FILTER"] = "1" 
os.environ["QT_LOGGING_RULES"] = "qt.qpa.window=false"

sys.coinit_flags = 2 

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QListWidget, QListWidgetItem, QCheckBox, 
                             QLineEdit, QPushButton, QLabel, QTextEdit, QComboBox,
                             QProgressBar, QMessageBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from core_engine import KeepGoingEngine
from archive_controller import ArchiveController

class ArchiveWorker(QThread):
    """專門處理存檔流程的背景執行緒"""
    progress = pyqtSignal(int, str)  # 傳回：百分比, 目前處理項目名稱
    finished = pyqtSignal(str)       # 傳回：存檔紀錄路徑

    def __init__(self, controller, selected_data):
        super().__init__()
        self.controller = controller
        self.selected_data = selected_data

    def run(self):
        # 在執行緒中執行耗時的置頂與截圖循環
        archive_results = []
        total = len(self.selected_data)

        for i, item in enumerate(self.selected_data):
            self.progress.emit(int((i / total) * 100), item['title'])
            
            # 這裡我們複用 controller 的單筆邏輯，但為了演示直接呼叫 flow
            # 實務上建議將 controller 拆出單筆處理方法
            # 這裡簡化演示：
            self.controller.run_archive_flow([item])
            
        self.finished.emit("存檔已完成")

class WindowItemWidget(QWidget):
    def __init__(self, item_data):
        super().__init__()
        self.data = item_data
        layout = QHBoxLayout()
        layout.setContentsMargins(5, 2, 5, 2)
        
        self.checkbox = QCheckBox()
        is_work = item_data['category'] != "Uncategorized"
        self.checkbox.setChecked(is_work) 
        
        label_text = f"[{item_data['category']}] {item_data['title'][:55]}"
        self.label = QLabel(label_text)
        
        layout.addWidget(self.checkbox)
        layout.addWidget(self.label)
        layout.addStretch()
        self.setLayout(layout)

class KeepGoingUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Keep-Going | 下班進度紀錄")
        self.resize(1000, 700)
        
        self.engine = KeepGoingEngine()
        self.controller = ArchiveController()
        self.items_widgets = []

        self.init_ui()
        self.refresh_list()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # 頂部狀態列
        self.status_label = QLabel("準備就緒。請勾選要紀錄的項目：")
        main_layout.addWidget(self.status_label)

        # 中間內容區
        content_layout = QHBoxLayout()
        
        # 左側：清單
        self.list_widget = QListWidget()
        self.list_widget.itemClicked.connect(self.on_item_clicked)
        content_layout.addWidget(self.list_widget, stretch=2)
        
        # 右側：編輯區
        right_panel = QVBoxLayout()
        right_panel.addWidget(QLabel("進度備註："))
        self.note_edit = QTextEdit()
        self.note_edit.setPlaceholderText("這張圖/這個功能完成了什麼...")
        self.note_edit.textChanged.connect(self.save_current_note)
        right_panel.addWidget(self.note_edit)
        
        right_panel.addWidget(QLabel("手動分類："))
        self.cat_combo = QComboBox()
        self.cat_combo.addItems(["Art", "Dev", "Writing", "Uncategorized"])
        self.cat_combo.currentIndexChanged.connect(self.save_current_category)
        right_panel.addWidget(self.cat_combo)
        right_panel.addStretch()
        content_layout.addLayout(right_panel, stretch=1)

        main_layout.addLayout(content_layout)

        # 底部：進度條與按鈕
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)

        btn_layout = QHBoxLayout()
        self.refresh_btn = QPushButton("重新掃描視窗")
        self.refresh_btn.clicked.connect(self.refresh_list)
        
        self.archive_btn = QPushButton("確認存檔並下班！")
        self.archive_btn.setFixedHeight(45)
        self.archive_btn.setStyleSheet("background-color: #27ae60; color: white; font-size: 14px; font-weight: bold;")
        self.archive_btn.clicked.connect(self.start_archive)

        self.settings_btn = QPushButton("⚙ 系統設定")
        self.settings_btn.clicked.connect(self.open_settings)
        btn_layout.insertWidget(0, self.settings_btn) # 放在最左邊

        # 實作 open_settings 方法
        def open_settings(self):
            from settings_dialog import SettingsDialog
            dialog = SettingsDialog(self)
            if dialog.exec():
                # 設定儲存後，自動刷新掃描清單
                QMessageBox.information(self, "成功", "設定已更新，正在重新掃描...")
                self.refresh_list()
        
        btn_layout.addWidget(self.refresh_btn)
        btn_layout.addWidget(self.archive_btn)
        main_layout.addLayout(btn_layout)

    def refresh_list(self):
        self.list_widget.clear()
        self.items_widgets = []
        raw_items = self.engine.get_full_status()
        
        for item in raw_items:
            item['note'] = item.get('note', "")
            list_item = QListWidgetItem(self.list_widget)
            widget = WindowItemWidget(item)
            list_item.setSizeHint(widget.sizeHint())
            self.list_widget.addItem(list_item)
            self.list_widget.setItemWidget(list_item, widget)
            self.items_widgets.append(widget)

    def on_item_clicked(self, list_item):
        widget = self.list_widget.itemWidget(list_item)
        self.current_selected_widget = widget
        self.note_edit.setText(widget.data['note'])
        self.cat_combo.setCurrentText(widget.data['category'])

    def save_current_note(self):
        if hasattr(self, 'current_selected_widget'):
            self.current_selected_widget.data['note'] = self.note_edit.toPlainText()

    def save_current_category(self):
        if hasattr(self, 'current_selected_widget'):
            new_cat = self.cat_combo.currentText()
            self.current_selected_widget.data['category'] = new_cat
            self.current_selected_widget.label.setText(f"[{new_cat}] {self.current_selected_widget.data['title'][:55]}")
    def open_settings(self):
            """開啟設定對話框並處理設定更新後的邏輯"""
            try:
                from settings_dialog import SettingsDialog
                dialog = SettingsDialog(self)
                
                # exec() 會開啟模態視窗，程式會在此暫停直到視窗關閉
                if dialog.exec():
                    # 如果使用者點擊了「儲存設定」 (dialog.accept())
                    self.status_label.setText("設定已更新，正在重新整理清單...")
                    
                    # 通知 scanner 更新它的內部規則快取
                    self.engine.scanner.update_settings()
                    
                    # 重新執行掃描，讓新的黑名單或分類規則生效
                    self.refresh_list()
                    
                    QMessageBox.information(self, "設定更新", "規則已成功套用！")
            except Exception as e:
                QMessageBox.critical(self, "錯誤", f"無法開啟設定頁面: {e}")
                
    def start_archive(self):
        selected_data = [w.data for w in self.items_widgets if w.checkbox.isChecked()]
        if not selected_data:
            QMessageBox.warning(self, "警告", "請至少勾選一個項目。")
            return

        # 禁用 UI
        self.archive_btn.setEnabled(False)
        self.refresh_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        # 啟動背景執行緒
        self.worker = ArchiveWorker(self.controller, selected_data)
        self.worker.progress.connect(self.update_ui_progress)
        self.worker.finished.connect(self.on_archive_finished)
        self.worker.start()

    def update_ui_progress(self, val, title):
        self.progress_bar.setValue(val)
        self.status_label.setText(f"正在存檔: {title}...")

    def on_archive_finished(self, msg):
        self.archive_btn.setEnabled(True)
        self.refresh_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText("存檔完成！辛苦了。")
        QMessageBox.information(self, "完成", "所有進度已成功紀錄。")

if __name__ == "__main__":
    # 建立 Application 實例1
    app = QApplication(sys.argv)
    
    app.setStyle("Fusion") 

    window = KeepGoingUI()
    window.show()
    
    try:
        sys.exit(app.exec())
    except SystemExit:
        pass