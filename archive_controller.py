# archive_controller.py
import time
from data_manager import DataManager
from core_engine import KeepGoingEngine
from capture_service import CaptureService

class ArchiveController:
    def __init__(self):
        self.dm = DataManager()
        self.engine = KeepGoingEngine()
        self.cap = CaptureService()

    def run_archive_flow(self, selected_items_with_notes):
        archive_results = []
        for item in selected_items_with_notes:
            tag = item.get('category') or 'Uncategorized'
            title = item.get('title') or 'Untitled'
            note = item.get('note') or ''
            duration = item.get('duration') or 0.0
            
            # 檔名處理
            keyword = "".join([c for c in title[:15] if c.isalnum() or c in (' ', '_')]).strip()
            save_path = self.dm.generate_image_path(tag, keyword)
            
            success = False
            target_hwnd = item.get('hwnd')
            
            # 置頂視窗
            if item.get('type') == 'browser_tab':
                if self.cap.focus_browser_tab(item['id']):
                    import pygetwindow as gw
                    browsers = [w for w in gw.getWindowsWithTitle('Comet') if w.visible]
                    if browsers:
                        target_hwnd = browsers[0]._hWnd
                        self.cap.focus_window(target_hwnd); success = True
            else:
                if target_hwnd and self.cap.focus_window(target_hwnd):
                    success = True

            # 截圖與紀錄 (修正點：傳入 hwnd)
            if success:
                rect = item.get('rect') 
                if not rect:
                    import pygetwindow as gw
                    browsers = [w for w in gw.getWindowsWithTitle('Comet') if w.visible]
                    rect = (browsers[0].left, browsers[0].top, browsers[0].width, browsers[0].height)
                
                # 同步呼叫新的 capture 函式
                self.cap.capture(target_hwnd, rect, str(save_path))
                
                # 統一紀錄資料
                record = {
                    "tag": tag,
                    "window_title": title,
                    "image_path": str(save_path.relative_to(self.dm.base_dir)),
                    "note": note,
                    "duration": duration
                }
                if item.get('url'): record["url"] = item['url']
                archive_results.append(record)
                print(f"✅ 已完成: {title}")

        if archive_results:
            log_path = self.dm.save_archive_record(archive_results)
            print(f"\n🎉 存檔完成！紀錄已更新至: {log_path}")