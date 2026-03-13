import requests

class BrowserResolver:
    def __init__(self, port=9222):
        self.endpoint = f"http://127.0.0.1:{port}/json"

    def get_all_tabs(self):
        try:
            response = requests.get(self.endpoint, timeout=2)
            tabs = response.json()
            
            resolved_tabs = []
            for tab in tabs:
                if tab.get('type') == 'page':
                    # 修正：移除 Notion 的寫死判斷，全交給使用者記憶
                    resolved_tabs.append({
                        "category": "Uncategorized", 
                        "title": tab.get('title', ''),
                        "url": tab.get('url', ''),
                        "id": tab.get('id')
                    })
            return resolved_tabs
        except requests.exceptions.ConnectionError:
            return None