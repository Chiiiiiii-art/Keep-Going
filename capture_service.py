# capture_service.py
import time
import requests
import ctypes
from PIL import Image
import win32gui
import win32con
import win32ui
from pywinauto import Application

# 核心修正：強制全域 DPI 感知，確保座標與物理像素 1:1
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    ctypes.windll.user32.SetProcessDPIAware()

class CaptureService:
    def __init__(self, cdp_port=9222):
        self.cdp_base_url = f"http://127.0.0.1:{cdp_port}/json"

    def focus_window(self, hwnd):
        """將視窗喚醒至最上層"""
        try:
            if not win32gui.IsWindow(hwnd): return False
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            
            win32gui.SetForegroundWindow(hwnd)
            app = Application().connect(handle=hwnd)
            app.top_window().set_focus()
            
            time.sleep(1) 
            return True
        except Exception:
            return False

    def capture(self, hwnd, rect, save_path):
        """
        修正：透過 hwnd 使用 PrintWindow 穿透黑屏並解決縮放問題
        """
        left, top, w, h = rect
        
        # 核心修正 2：優先使用 PrintWindow (解決 PS/GitHub 黑屏與截圖範圍太小的問題)
        if hwnd and win32gui.IsWindow(hwnd):
            try:
                # 重新抓取最精確的視窗物理大小
                r = win32gui.GetWindowRect(hwnd)
                w, h = r[2] - r[0], r[3] - r[1]
                
                w_dc = win32gui.GetWindowDC(hwnd)
                dc_obj = win32ui.CreateDCFromHandle(w_dc)
                c_dc = dc_obj.CreateCompatibleDC()
                bmp = win32ui.CreateBitmap()
                bmp.CreateCompatibleBitmap(dc_obj, w, h)
                c_dc.SelectObject(bmp)
                
                # Flag 2 (PW_RENDERFULLCONTENT) 能強制硬體加速視窗渲染內容
                result = ctypes.windll.user32.PrintWindow(hwnd, c_dc.GetSafeHdc(), 2)
                
                if result == 1:
                    bmp_info = bmp.GetInfo()
                    bmp_str = bmp.GetBitmapBits(True)
                    img = Image.frombuffer('RGB', (bmp_info['bmWidth'], bmp_info['bmHeight']), 
                                         bmp_str, 'raw', 'BGRX', 0, 1)
                    img.save(save_path)
                    
                    # 釋放資源
                    win32gui.DeleteObject(bmp.GetHandle())
                    c_dc.DeleteDC(); dc_obj.DeleteDC()
                    win32gui.ReleaseDC(hwnd, w_dc)
                    print(f"📸 穿透模式截圖成功: {save_path}")
                    return
            except Exception as e:
                print(f"穿透模式失敗: {e}")

        # 後備方案：傳統截圖 (僅在 PrintWindow 失敗時觸發)
        from PIL import ImageGrab
        bbox = (left, top, left + w, top + h)
        screenshot = ImageGrab.grab(bbox=bbox, all_screens=True)
        screenshot.save(save_path)