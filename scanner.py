import psutil
import win32process
import win32gui
import win32con
from settings_manager import ConfigManager

class WindowScanner:
    def __init__(self):
        self.config_mgr = ConfigManager()
        self.update_settings()

    def update_settings(self):
        config = self.config_mgr.load_config()
        self.blacklist_exes = config.get("blacklist_exes", [])
        self.blacklist_titles = config.get("blacklist_titles", [])

    def get_process_name(self, hwnd):
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            return psutil.Process(pid).name()
        except Exception: return None

    def is_real_window(self, hwnd):
        if not win32gui.IsWindowVisible(hwnd): return False
        title = win32gui.GetWindowText(hwnd)
        if not title: return False
        if win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) & win32con.WS_EX_TOOLWINDOW: return False
        return True

    def scan_active_windows(self):
        active_windows = []
        self.update_settings()

        def callback(hwnd, extra):
            if not self.is_real_window(hwnd): return
            title = win32gui.GetWindowText(hwnd)
            exe_name = self.get_process_name(hwnd)

            if title == "Keep-Going | 下班進度紀錄": return
            if any(bt in title for bt in self.blacklist_titles): return
            if exe_name and exe_name.lower() in [e.lower() for e in self.blacklist_exes]: return

            # 核心修正：全部預設為 Uncategorized，依賴使用者自訂分配與記憶
            rect = win32gui.GetWindowRect(hwnd)
            w, h = rect[2] - rect[0], rect[3] - rect[1]

            active_windows.append({
                "title": title, "exe": exe_name or "Unknown", "category": "Uncategorized",
                "hwnd": hwnd, "rect": (rect[0], rect[1], w, h)
            })

        win32gui.EnumWindows(callback, None)
        return active_windows