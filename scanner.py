import pygetwindow as gw
import psutil
import win32process # 需要安裝 pywin32
import win32gui

class WindowScanner:
    def __init__(self):
        # 預設規則映射
        self.rules = {
            "Art": ["Photoshop.exe", "ClipStudioPaint.exe", "Krita.exe"],
            "Dev": ["Code.exe", "devenv.exe", "WindowsTerminal.exe"],
            "Writing": ["Notion.exe"] # Notion 桌面版
        }

    def get_process_name(self, hwnd):
        """透過視窗控制代碼獲取進程名稱"""
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            proc = psutil.Process(pid)
            return proc.name()
        except (psutil.NoSuchProcess, Exception):
            return "Unknown"

    def scan_active_windows(self):
        """掃描目前所有非縮小化的視窗"""
        active_windows = []
        # 獲取所有開啟的視窗
        windows = gw.getAllWindows()
        
        for win in windows:
            # 過濾條件：有標題、非縮小化、且視窗必須在可見範圍內
            if win.title and not win.isMinimized and win.visible:
                # 獲取進程名稱以供分類
                exe_name = self.get_process_name(win._hWnd)
                
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

if __name__ == "__main__":
    scanner = WindowScanner()
    results = scanner.scan_active_windows()
    print(f"偵測到 {len(results)} 個活躍視窗：\n")
    for w in results:
        print(f"[{w['category']}] {w['exe']} - {w['title'][:50]}...")