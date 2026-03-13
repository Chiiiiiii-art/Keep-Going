import time
import requests
from PIL import ImageGrab
from pywinauto import Application
import win32gui
import win32con

class CaptureService:
    def __init__(self, cdp_port=9222):
        self.cdp_base_url = f"http://127.0.0.1:{cdp_port}/json"

    def focus_window(self, hwnd):
        """將一般視窗喚醒至最上層"""
        try:
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            
            shell = Application().connect(handle=hwnd)
            shell.top_window().set_focus()
            
            # 修正點：針對 PS 等大型 App 增加等待時間
            # 從原本的 0.3s 增加到 0.8s，確保 GPU 完成重繪
            time.sleep(5) 
            return True
        except Exception:
            return False

    def focus_browser_tab(self, tab_id):
        """透過 CDP 指令發送 Page.bringToFront"""
        try:
            # 呼叫 CDP 啟動該分頁
            requests.get(f"{self.cdp_base_url}/activate/{tab_id}")
            time.sleep(0.4) # 規格書建議 300ms，我們稍微多給一點確保渲染
            return True
        except Exception as e:
            print(f"無法切換分頁: {e}")
            return False

    def capture(self, rect, save_path):
        """根據座標裁剪並儲存截圖"""
        # rect 格式: (left, top, width, height)
        # ImageGrab.grab 格式: (left, top, right, bottom)
        bbox = (rect[0], rect[1], rect[0] + rect[2], rect[1] + rect[3])
        
        # 截取螢幕
        screenshot = ImageGrab.grab(bbox=bbox, all_screens=True)
        screenshot.save(save_path)
        print(f"📸 截圖已儲存: {save_path}")

if __name__ == "__main__":
    # 測試程式碼：試著截取目前運行的 VS Code
    import pygetwindow as gw
    from data_manager import DataManager
    
    cap = CaptureService()
    dm = DataManager()
    
    # 找尋 VS Code 視窗
    code_wins = [w for w in gw.getWindowsWithTitle('Visual Studio Code') if w.visible]
    if code_wins:
        win = code_wins[0]
        print(f"正在測試截圖: {win.title}")
        
        if cap.focus_window(win._hWnd):
            save_path = dm.generate_image_path("Dev", "VSCode_Test")
            cap.capture((win.left, win.top, win.width, win.height), save_path)