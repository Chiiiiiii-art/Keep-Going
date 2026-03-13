# scanner.py 完整強化版
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
        self.rules = config["rules"]
        self.blacklist_exes = config.get("blacklist_exes", [])
        self.blacklist_titles = config.get("blacklist_titles", [])

    def get_process_name(self, hwnd):
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            proc = psutil.Process(pid)
            return proc.name()
        except Exception:
            return None

    def is_real_window(self, hwnd):
        if not win32gui.IsWindowVisible(hwnd): return False
        title = win32gui.GetWindowText(hwnd)
        if not title: return False
        ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        if ex_style & win32con.WS_EX_TOOLWINDOW: return False
        return True

    def scan_active_windows(self):
        active_windows = []
        self.update_settings()

        def callback(hwnd, extra):
            if not self.is_real_window(hwnd): return
            
            title = win32gui.GetWindowText(hwnd)
            exe_name = self.get_process_name(hwnd)

            # 1. 優先判定：如果是 Keep-Going 程式本身，絕對排除
            # 這裡改用更嚴謹的判定：標題符合且 EXE 是 Python 或打包後的名稱
            if title == "Keep-Going | 下班進度紀錄":
                return

            # 2. 標題黑名單過濾 (排除系統雜項)
            if any(bt in title for bt in self.blacklist_titles):
                return

            # 3. 進程黑名單過濾
            if exe_name and exe_name.lower() in [e.lower() for e in self.blacklist_exes]:
                return

            # 4. 自動分類邏輯
            category = "Uncategorized"
            for cat, exes in self.rules.items():
                if exe_name and any(exe.lower() == exe_name.lower() for exe in exes):
                    category = cat
                    break
            
            # --- 關鍵修正：針對 VS Code 可能被誤殺的保險 ---
            if exe_name and exe_name.lower() == "code.exe":
                category = "Dev"

            rect = win32gui.GetWindowRect(hwnd)
            w, h = rect[2] - rect[0], rect[3] - rect[1]

            active_windows.append({
                "title": title,
                "exe": exe_name or "Unknown",
                "category": category,
                "hwnd": hwnd,
                "rect": (rect[0], rect[1], w, h)
            })

        win32gui.EnumWindows(callback, None)
        return active_windows