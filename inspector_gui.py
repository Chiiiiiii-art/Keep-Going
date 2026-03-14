import sys
import json
import ctypes
from datetime import datetime, timedelta
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTreeWidget, QTreeWidgetItem, 
                             QLabel, QSlider, QFrame, QComboBox)
from PyQt6.QtCore import Qt, pyqtSignal, QVariantAnimation, QPropertyAnimation, QEasingCurve, QTimer
from PyQt6.QtGui import QPixmap, QPainter, QColor, QGuiApplication

# --- 核心修正 1：啟動時強制開啟 Windows DPI 感知 ---
# 這能解決在雙螢幕或 4K 螢幕上，座標計算出錯導致視窗縮到左上角看不見的問題
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2) # PROCESS_PER_MONITOR_DPI_AWARE
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

class TimelineViewer(QWidget):
    """自定義畫布：負責切換圖片時的淡入淡出特效"""
    def __init__(self):
        super().__init__()
        self.image_paths = []
        self.pixmap_cache = {}
        self.scaled_cache = {}
        self.current_path = None
        self.old_path = None
        
        self.alpha = 1.0
        self.anim = QVariantAnimation(self)
        self.anim.setDuration(200) 
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.valueChanged.connect(self.update_alpha)
        self.setMinimumSize(600, 400)
        
        self.scroll_timer = QTimer()
        self.scroll_timer.setSingleShot(True)
        self.scroll_timer.setInterval(120)

    def update_alpha(self, val):
        self.alpha = val
        self.update()

    def load_images(self, paths):
        self.image_paths = paths
        self.pixmap_cache.clear()
        self.scaled_cache.clear()
        for p in paths:
            self.pixmap_cache[p] = QPixmap(str(p))
        self.current_path = None
        self.old_path = None
        self.update()

    def get_scaled_pixmap(self, path):
        if path in self.scaled_cache: return self.scaled_cache[path]
        pm = self.pixmap_cache[path]
        scaled = pm.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.scaled_cache[path] = scaled
        return scaled

    def resizeEvent(self, event):
        self.scaled_cache.clear() 
        super().resizeEvent(event)

    def set_image_index(self, idx):
        if not self.image_paths or idx < 0 or idx >= len(self.image_paths): return
        new_path = self.image_paths[idx]
        if self.current_path == new_path: return
        self.old_path = self.current_path
        self.current_path = new_path
        if self.old_path:
            self.anim.stop()
            self.anim.start()
        else:
            self.alpha = 1.0
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        if not self.current_path:
            painter.setPen(QColor("#9B9A97"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "請開啟左側專案清單...")
            return
        def draw_centered(pm, opacity):
            if opacity <= 0.01: return
            x, y = (self.width()-pm.width())//2, (self.height()-pm.height())//2
            painter.setOpacity(opacity)
            painter.drawPixmap(x, y, pm)
        if self.old_path and self.alpha < 1.0:
            draw_centered(self.get_scaled_pixmap(self.old_path), 1.0 - self.alpha)
        draw_centered(self.get_scaled_pixmap(self.current_path), self.alpha)

class InspectorUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Keep-Going | 歷史進度檢閱")
        self.resize(1250, 850)
        
        # --- 核心修正 2：在視窗顯示前將其移至螢幕中央 ---
        self.center_window()
        
        self.current_paths = []
        self.metadata_db = {} 
        
        self.init_ui()
        self.load_metadata()
        self.load_data()

    def center_window(self):
        """抓取當前活動螢幕的可用區域，並精確居中視窗"""
        screen = QGuiApplication.primaryScreen()
        if screen:
            rect = screen.availableGeometry()
            # 計算居中位置
            x = rect.left() + (rect.width() - self.width()) // 2
            y = rect.top() + (rect.height() - self.height()) // 2
            self.move(x, y)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QHBoxLayout(central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # --- 側邊欄 ---
        self.sidebar_container = QFrame()
        self.sidebar_container.setObjectName("Sidebar")
        self.sidebar_container.setFixedWidth(300)
        self.sidebar_container.setStyleSheet("""
            QFrame#Sidebar { background-color: #1e1e1e; border-right: 1px solid #2c2c2c; }
            QLabel { color: #9B9A97; font-weight: bold; font-size: 11px; margin-bottom: 5px; }
            QTreeWidget { background: transparent; border: none; outline: none; }
            QTreeWidget::item { height: 42px; color: #EBEBEA; padding-left: 5px; border-radius: 4px; }
            QTreeWidget::item:hover { background-color: rgba(255, 255, 255, 0.05); }
            QTreeWidget::item:selected { background-color: rgba(255, 255, 255, 0.1); font-weight: bold; }
        """)
        
        sidebar_layout = QVBoxLayout(self.sidebar_container)
        sidebar_layout.setContentsMargins(20, 25, 20, 25)
        
        self.sidebar_content = QWidget()
        content_vbox = QVBoxLayout(self.sidebar_content)
        content_vbox.setContentsMargins(0, 0, 0, 0)
        content_vbox.setSpacing(10)
        
        content_vbox.addWidget(QLabel("⏳ 時間篩選"))
        self.time_filter = QComboBox()
        self.time_filter.addItems(["全部紀錄", "最近 7 天", "最近 14 天", "最近 30 天"])
        self.time_filter.currentIndexChanged.connect(self.load_data)
        content_vbox.addWidget(self.time_filter)
        content_vbox.addSpacing(20)

        content_vbox.addWidget(QLabel("📂 專案歷史"))
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.itemClicked.connect(self.on_project_selected)
        content_vbox.addWidget(self.tree)
        
        sidebar_layout.addWidget(self.sidebar_content)
        self.main_layout.addWidget(self.sidebar_container)

        # --- 右側主檢視區 ---
        self.view_panel = QWidget()
        view_layout = QVBoxLayout(self.view_panel)
        view_layout.setContentsMargins(40, 40, 40, 30) 
        view_layout.setSpacing(25)

        self.viewer = TimelineViewer()
        view_layout.addWidget(self.viewer, stretch=1)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setEnabled(False)
        self.slider.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.slider.setCursor(Qt.CursorShape.PointingHandCursor)
        self.slider.valueChanged.connect(self.on_slider_changed)
        self.slider.setStyleSheet("""
            QSlider::groove:horizontal { height: 6px; background: #333; border-radius: 3px; }
            QSlider::handle:horizontal { background: #EBEBEA; width: 16px; height: 16px; margin: -5px 0; border-radius: 8px; }
        """)
        view_layout.addWidget(self.slider)
        
        # 資訊卡片
        self.info_frame = QFrame()
        self.info_frame.setObjectName("InfoCard")
        self.info_frame.setStyleSheet("""
            QFrame#InfoCard { background-color: #202020; border-radius: 12px; border: 1px solid #2c2c2c; }
            QLabel { background: transparent; border: none; }
        """)
        self.info_frame.setMinimumHeight(120)
        
        info_layout = QVBoxLayout(self.info_frame)
        info_layout.setContentsMargins(25, 20, 25, 20)
        
        h_layout = QHBoxLayout()
        self.date_label = QLabel("🗓️ 尚未選擇專案")
        self.date_label.setStyleSheet("color: #EBEBEA; font-weight: bold; font-size: 16px;")
        
        self.duration_label = QLabel("⏱️ 0.0h")
        self.duration_label.setStyleSheet("color: #3498db; font-weight: bold; font-size: 15px;")
        
        self.count_label = QLabel("0 / 0")
        self.count_label.setStyleSheet("color: #9B9A97; font-size: 14px;")
        
        h_layout.addWidget(self.date_label)
        h_layout.addStretch()
        h_layout.addWidget(self.duration_label)
        h_layout.addSpacing(20)
        h_layout.addWidget(self.count_label)
        
        self.note_label = QLabel("📝 備註：無")
        self.note_label.setWordWrap(True)
        self.note_label.setStyleSheet("color: #9B9A97; margin-top: 8px; font-size: 14px; line-height: 1.4;")

        info_layout.addLayout(h_layout)
        info_layout.addWidget(self.note_label)
        view_layout.addWidget(self.info_frame)
        
        self.main_layout.addWidget(self.view_panel)

        # 全局滾輪綁定
        self.viewer.wheelEvent = self.handle_global_wheel
        self.slider.wheelEvent = self.handle_global_wheel

        # 側邊欄動畫設定
        self.sidebar_anim = QPropertyAnimation(self.sidebar_container, b"minimumWidth")
        self.sidebar_anim.setDuration(300)
        self.sidebar_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.sidebar_max_anim = QPropertyAnimation(self.sidebar_container, b"maximumWidth")
        self.sidebar_max_anim.setDuration(300)
        self.sidebar_max_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.sidebar_container.installEventFilter(self)
        self.is_sidebar_expanded = True

    def handle_global_wheel(self, event):
        """集中管轄滾輪事件，確保一次滾動只換一張圖"""
        if not self.current_paths or not self.slider.isEnabled(): return
        if self.viewer.scroll_timer.isActive(): return 
        delta = event.angleDelta().y()
        if abs(delta) < 15: return 
        step = -1 if delta > 0 else 1 
        self.slider.setValue(max(0, min(self.slider.value() + step, self.slider.maximum())))
        self.viewer.scroll_timer.start()
        event.accept()

    def eventFilter(self, obj, event):
        """處理側邊欄的懸停展開/縮回邏輯"""
        if obj == self.sidebar_container:
            if event.type() == event.Type.Enter:
                self.expand_sidebar()
            elif event.type() == event.Type.Leave:
                # 若下拉選單開啟中，暫不收合
                if not self.time_filter.view().isVisible():
                    QTimer.singleShot(300, self.check_sidebar_leave)
        return super().eventFilter(obj, event)

    def check_sidebar_leave(self):
        if not self.sidebar_container.underMouse() and not self.time_filter.view().isVisible():
            self.collapse_sidebar()

    def expand_sidebar(self):
        if not self.is_sidebar_expanded:
            self.sidebar_content.show()
            self.sidebar_anim.setStartValue(10)
            self.sidebar_anim.setEndValue(300)
            self.sidebar_max_anim.setStartValue(10)
            self.sidebar_max_anim.setEndValue(300)
            self.sidebar_anim.start()
            self.sidebar_max_anim.start()
            self.is_sidebar_expanded = True

    def collapse_sidebar(self):
        if self.is_sidebar_expanded:
            self.sidebar_content.hide()
            self.sidebar_anim.setStartValue(300)
            self.sidebar_anim.setEndValue(35) # 保留 35px 作為喚醒觸發感應帶
            self.sidebar_max_anim.setStartValue(300)
            self.sidebar_max_anim.setEndValue(35)
            self.sidebar_anim.start()
            self.sidebar_max_anim.start()
            self.is_sidebar_expanded = False

    def load_metadata(self):
        """從 Logs 目錄讀取 JSON，建立備註快取"""
        log_dir = Path("WorkSnap_Data/Logs")
        if not log_dir.exists(): return
        for log_file in log_dir.glob("*.json"):
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
                    for session in history:
                        for proj in session.get("projects", []):
                            img_path = proj.get("image_path", "")
                            if img_path:
                                self.metadata_db[Path(img_path).name] = {
                                    "note": proj.get("note", "(無備註)"),
                                    "duration": proj.get("duration", 0.0)
                                }
            except: pass

    def load_data(self):
        """掃描資料夾，根據時間過濾器渲染清單"""
        self.tree.clear()
        base_dir = Path("WorkSnap_Data")
        if not base_dir.exists(): return
        filter_idx = self.time_filter.currentIndex()
        days_map = {1: 7, 2: 14, 3: 30}
        cutoff = datetime.now() - timedelta(days=days_map.get(filter_idx, 9999)) if filter_idx > 0 else None

        tags = [d for d in base_dir.iterdir() if d.is_dir() and d.name != "Logs"]
        for tag_dir in tags:
            tag_node = None
            images = sorted(list(tag_dir.glob("*.png")))
            project_groups = {}
            for img in images:
                mtime = datetime.fromtimestamp(img.stat().st_mtime)
                if cutoff and mtime < cutoff: continue
                parts = img.stem.split('_', 2)
                title = parts[2] if len(parts) >= 3 else img.stem
                project_groups.setdefault(title, []).append(img)

            if project_groups:
                if not tag_node:
                    tag_node = QTreeWidgetItem(self.tree)
                    tag_node.setText(0, f"📁 {tag_dir.name}")
                    tag_node.setExpanded(True)
                for title, paths in project_groups.items():
                    proj_node = QTreeWidgetItem(tag_node)
                    proj_node.setText(0, f"📄 {title[:25]} ({len(paths)})")
                    proj_node.setData(0, Qt.ItemDataRole.UserRole, paths)

    def on_project_selected(self, item, column):
        paths = item.data(0, Qt.ItemDataRole.UserRole)
        if not paths: return
        self.current_paths = paths
        self.viewer.load_images(paths)
        self.slider.setEnabled(True)
        self.slider.setRange(0, len(paths) - 1)
        self.slider.setValue(0)
        self.on_slider_changed(0)

    def on_slider_changed(self, idx):
        self.viewer.set_image_index(idx)
        self.update_labels(idx)

    def update_labels(self, idx):
        if not self.current_paths: return
        path = self.current_paths[idx]
        parts = path.stem.split('_', 2)
        if len(parts) >= 2:
            self.date_label.setText(f"🗓️ {parts[0][:4]}-{parts[0][4:6]}-{parts[0][6:]} {parts[1][:2]}:{parts[1][2:4]}")
        self.count_label.setText(f"{idx + 1} / {len(self.current_paths)}")
        meta = self.metadata_db.get(path.name, {"note": "(未輸入備註)", "duration": 0.0})
        self.note_label.setText(f"📝 備註：{meta['note']}")
        self.duration_label.setText(f"⏱️ {meta['duration']}h")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # 使用 Fusion 風格
    app.setStyle("Fusion")
    
    # 這裡會嘗試載入外部 QSS，若無則套用預設顏色
    window = InspectorUI()
    window.show()
    sys.exit(app.exec())