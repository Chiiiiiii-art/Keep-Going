import requests

class BrowserResolver:
    def __init__(self, port=9222):
        self.endpoint = f"http://127.0.0.1:{port}/json"

    def get_all_tabs(self):
        """
        透過 Chrome DevTools Protocol 獲取所有分頁
        """
        try:
            # 獲取分頁清單
            response = requests.get(self.endpoint, timeout=2)
            tabs = response.json()
            
            resolved_tabs = []
            for tab in tabs:
                # 我們只關心真正的網頁 (type='page')
                if tab.get('type') == 'page':
                    url = tab.get('url', '')
                    title = tab.get('title', '')
                    
                    # 預設規則映射：偵測 Notion
                    category = "Uncategorized"
                    if "notion.so" in url:
                        category = "Writing"
                    
                    resolved_tabs.append({
                        "category": category,
                        "title": title,
                        "url": url,
                        "id": tab.get('id') # 用於後續 bringToFront 指令
                    })
            return resolved_tabs
        except requests.exceptions.ConnectionError:
            return None # 瀏覽器未開啟偵錯模式

if __name__ == "__main__":
    resolver = BrowserResolver()
    tabs = resolver.get_all_tabs()
    
    if tabs is None:
        print("❌ 無法連接到瀏覽器。請確保瀏覽器已開啟偵錯模式 (port 9222)。")
    else:
        print(f"偵測到 {len(tabs)} 個瀏覽器分頁：")
        for t in tabs:
            print(f"[{t['category']}] {t['title'][:40]}... \n    URL: {t['url']}")