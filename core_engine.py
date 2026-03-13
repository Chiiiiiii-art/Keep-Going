from scanner import WindowScanner
from browser_resolver import BrowserResolver

class KeepGoingEngine:
    def __init__(self):
        self.scanner = WindowScanner()
        self.resolver = BrowserResolver()

    def get_full_status(self):
        """整合一般視窗與瀏覽器分頁"""
        all_items = []
        
        # 1. 抓取一般視窗
        windows = self.scanner.scan_active_windows()
        
        # 找出瀏覽器視窗 (Comet)
        browser_windows = [w for w in windows if w['exe'].lower() == "comet.exe"]
        other_windows = [w for w in windows if w['exe'].lower() != "comet.exe"]
        
        # 2. 抓取 CDP 分頁
        tabs = self.resolver.get_all_tabs()
        
        if tabs:
            # 如果 CDP 有抓到，我們就用分頁資訊取代原本的 Comet 總視窗
            all_items.extend(other_windows)
            for tab in tabs:
                all_items.append({
                    "type": "browser_tab",
                    "category": tab['category'],
                    "title": tab['title'],
                    "url": tab['url'],
                    "id": tab['id']
                })
        else:
            # 如果 CDP 沒開，就顯示一般視窗並提示
            print("⚠️ 提醒：瀏覽器偵錯模式未開啟，無法獲取詳細分頁。")
            all_items.extend(windows)
            
        return all_items

if __name__ == "__main__":
    engine = KeepGoingEngine()
    final_list = engine.get_full_status()
    
    print("\n--- 當前待記錄清單 ---")
    for item in final_list:
        source = item.get('type', 'window')
        print(f"[{item['category']}] ({source}) {item['title'][:50]}")