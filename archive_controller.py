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
        """
        執行下班存檔流程
        selected_items_with_notes: list of dict, 包含項目資訊與使用者輸入的 note
        """
        archive_results = []
        
        for item in selected_items_with_notes:
            tag = item.get('category', 'Uncategorized')
            title = item.get('title', 'Untitled')
            note = item.get('note', '')
            
            # 1. 產生儲存路徑
            # 取得簡短關鍵字作為檔名一部分
            keyword = title[:15].replace(" ", "_").strip() 
            # 去除 Windows 檔名不允許的字元
            for char in r'<>:"/\|?*':
                keyword = keyword.replace(char, "")
            save_path = self.dm.generate_image_path(tag, keyword)
            
            success = False
            # 2. 執行置頂動作
            if item.get('type') == 'browser_tab':
                # 瀏覽器分頁切換
                if self.cap.focus_browser_tab(item['id']):
                    # 瀏覽器視窗本身也需要置頂才能截圖
                    # 這裡假設 Comet 視窗已經由 core_engine 處理或手動尋找
                    import pygetwindow as gw
                    browsers = [w for w in gw.getWindowsWithTitle('Comet') if w.visible]
                    if browsers:
                        self.cap.focus_window(browsers[0]._hWnd)
                        success = True
            else:
                # 一般視窗置頂
                if self.cap.focus_window(item['hwnd']):
                    success = True

            # 3. 截圖
            if success:
                # 如果是分頁，截取整個瀏覽器視窗；如果是視窗，截取該視窗座標
                rect = item.get('rect') 
                if not rect: # 瀏覽器分頁可能沒帶 rect，找主視窗
                    import pygetwindow as gw
                    browsers = [w for w in gw.getWindowsWithTitle('Comet') if w.visible]
                    rect = (browsers[0].left, browsers[0].top, browsers[0].width, browsers[0].height)
                
                self.cap.capture(rect, str(save_path))
                
                # 4. 準備寫入 JSON 的資料結構
                record = {
                    "tag": tag,
                    "window_title": title,
                    "image_path": str(save_path.relative_to(self.dm.base_dir)), # 存相對路徑
                    "note": note
                }
                if item.get('url'):
                    record["url"] = item['url']
                
                archive_results.append(record)
                print(f"✅ 已完成: {title}")
            else:
                print(f"❌ 失敗: 無法聚焦 {title}")

        # 5. 寫入月份紀錄檔
        if archive_results:
            log_path = self.dm.save_archive_record(archive_results)
            print(f"\n🎉 存檔完成！紀錄已更新至: {log_path}")

if __name__ == "__main__":
    controller = ArchiveController()
    
    # 模擬 UI 傳來的「使用者勾選項目」
    # 這裡我們自動抓取目前的狀態，並模擬幫前兩個項目加備註
    current_status = controller.engine.get_full_status()
    test_selection = []
    
    if current_status:
        # 測試：只存前兩個
        for i in range(min(2, len(current_status))):
            item = current_status[i]
            item['note'] = f"這是關於 {item['title'][:10]} 的自動測試備註"
            test_selection.append(item)
        
        print(f"開始執行批次存檔，預計處理 {len(test_selection)} 個項目...")
        controller.run_archive_flow(test_selection)