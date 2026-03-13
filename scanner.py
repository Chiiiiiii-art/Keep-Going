import psutil
import win32process
import win32gui
import win32con
from settings_manager import ConfigManager # 確保你有建立這個檔案

class WindowScanner:
    def __init__(self):
        # 建立設定管理器並讀取
        self.config_mgr = ConfigManager()
        self.update_settings()

    def update_settings(self):
        """同步最新的設定內容"""
        config = self.config_mgr.load_config()
        self.rules = config["rules"]
        self.blacklist_exes = config["blacklist_exes"]
        self.blacklist_titles = config["blacklist_titles"]

    def get_process_name(self, hwnd):
        """核心輔助函式：透過視窗控制代碼獲取進程名稱 (.exe)"""
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            proc = psutil.Process(pid)
            return proc.name()
        except (psutil.NoSuchProcess, Exception):
            return "Unknown"

    def scan_active_windows(self):
        """掃描並自動過濾"""
        active_windows = []
        self.update_settings()

        def callback(hwnd, extra):
            # 1. 基礎過濾：只看可見視窗
            if not win32gui.IsWindowVisible(hwnd):
                return
            
            # 2. 標題過濾：排除黑名單中的文字
            title = win32gui.GetWindowText(hwnd)
            if not title or any(bt in title for bt in self.blacklist_titles):
                return

            # 3. 進程過濾：排除系統組件
            exe_name = self.get_process_name(hwnd)
            if exe_name.lower() in [e.lower() for e in self.blacklist_exes]:
                return

            # 4. 尺寸過濾：排除背景小視窗
            rect = win32gui.GetWindowRect(hwnd)
            w, h = rect[2] - rect[0], rect[3] - rect[1]
            if w <= 100 or h <= 100:
                return

            # 5. 自動分類：根據規則比對
            category = "Uncategorized"
            for cat, exes in self.rules.items():
                if any(exe.lower() == exe_name.lower() for exe in exes):
                    category = cat
                    break

            active_windows.append({
                "title": title,
                "exe": exe_name,
                "category": category,
                "hwnd": hwnd,
                "rect": (rect[0], rect[1], w, h)
            })

        win32gui.EnumWindows(callback, None)
        return active_windows