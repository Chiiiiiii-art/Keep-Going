import pygetwindow as gw
import psutil
import win32process
import win32gui

class WindowScanner:
    def __init__(self):
        # 預設規則映射
        self.rules = {
            "Art": ["Photoshop.exe", "ClipStudioPaint.exe", "Krita.exe"],
            "Dev": ["Code.exe", "devenv.exe", "WindowsTerminal.exe"],
            "Writing": ["Notion.exe"]
        }
        
        # 系統級黑名單：這些進程永遠不該出現在清單中
        self.blacklist_exes = [
            "explorer.exe", "SystemSettings.exe", "NVIDIA Overlay.exe", 
            "TextInputHost.exe", "ApplicationFrameHost.exe", "ShellExperienceHost.exe",
            "StartMenuExperienceHost.exe", "Taskmgr.exe", "SearchHost.exe"
        ]
        
        # 標題黑名單
        self.blacklist_titles = ["Program Manager", "Settings", "設定", "Windows 輸入體驗"]

    def get_process_name(self, hwnd):
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            proc = psutil.Process(pid)
            return proc.name()
        except (psutil.NoSuchProcess, Exception):
            return "Unknown"

    def scan_active_windows(self):
        """掃描並過濾無意義的系統視窗"""
        active_windows = []
        windows = gw.getAllWindows()
        
        for win in windows:
            # 基礎過濾：有標題、可見、非縮小化
            if not (win.title and not win.isMinimized and win.visible):
                continue
                
            # 進一步檢查視窗大小，排除掉長寬過小的隱形視窗 (例如 1x1 或 0x0)
            if win.width <= 10 or win.height <= 10:
                continue

            exe_name = self.get_process_name(win._hWnd)
            
            # 執行黑名單過濾
            if exe_name in self.blacklist_exes:
                continue
            if any(bt in win.title for bt in self.blacklist_titles):
                continue
                
            # 自動分類邏輯
            category = "Uncategorized"
            for cat, exes in self.rules.items():
                if exe_name in exes:
                    category = cat
                    break
            
            active_windows.append({
                "title": win.title,
                "exe": exe_name,
                "category": category,
                "hwnd": win._hWnd,
                "rect": (win.left, win.top, win.width, win.height)
            })
        
        return active_windows