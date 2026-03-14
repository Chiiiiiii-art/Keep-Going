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
            if not self.is_real_window(hwnd): 
                return
            
            title = win32gui.GetWindowText(hwnd)
            # 取得執行檔名稱
            exe_name = self.get_process_name(hwnd)

            # --- 修正核心：權限不足處理 ---
            # 如果拿不到 exe_name，代表該視窗權限比你的 App 高（通常是管理員開啟的 VS Code）
            if not exe_name:
                # 檢查標題，如果標題包含 "Visual Studio Code"，我們就手動標記它
                if "Visual Studio Code" in title:
                    exe_display = "Code.exe (Admin)"
                else:
                    exe_display = "Administrator Process"
            else:
                exe_display = exe_name

            # 1. 排除 App 自身的特定標題
            if title in ["Keep-Going | 下班進度紀錄", "Keep-Going 控制中心"]:
                return

            # 2. 標題黑名單過濾 (精確匹配)
            if any(bt == title for bt in self.blacklist_titles):
                return

            # 3. 執行檔黑名單過濾
            if exe_name and exe_name.lower() in [e.lower() for e in self.blacklist_exes]:
                return

            try:
                rect = win32gui.GetWindowRect(hwnd)
                w, h = rect[2] - rect[0], rect[3] - rect[1]
            except:
                return

            active_windows.append({
                "title": title, 
                "exe": exe_display, # 使用我們處理過的名稱
                "category": None, 
                "hwnd": hwnd, 
                "rect": (rect[0], rect[1], w, h)
            })

        win32gui.EnumWindows(callback, None)
        return active_windows