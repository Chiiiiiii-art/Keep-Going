import os
import json
from datetime import datetime
from pathlib import Path

class DataManager:
    """負責管理 Keep-Going 的檔案結構與 JSON 紀錄存取"""
    
    def __init__(self, base_dir="WorkSnap_Data"):
        self.base_dir = Path(base_dir)
        self.categories = ["Art", "Dev", "Writing"]
        self.logs_dir = self.base_dir / "Logs"
        self._init_directories()

    def _init_directories(self):
        """初始化資料夾結構"""
        for category in self.categories:
            (self.base_dir / category).mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def generate_image_path(self, tag, keyword=""):
        """產生符合規範的圖片儲存路徑 (YYYYMMDD_HHMMSS_關鍵字.png)"""
        if tag not in self.categories:
            raise ValueError(f"未知的標籤: {tag}")
        
        now = datetime.now()
        timestamp_str = now.strftime("%Y%m%d_%H%M%S")
        safe_keyword = "".join([c for c in keyword if c.isalnum() or c in (' ', '_')]).rstrip()
        safe_keyword = f"_{safe_keyword}" if safe_keyword else ""
        
        filename = f"{timestamp_str}{safe_keyword}.png"
        return self.base_dir / tag / filename

    def save_archive_record(self, projects_data):
        """
        儲存下班存檔紀錄至對應月份的 JSON 檔案
        projects_data: list of dict (符合 5. 資料架構的 projects 陣列)
        """
        now = datetime.now()
        log_filename = f"history_{now.strftime('%Y_%m')}.json"
        log_path = self.logs_dir / log_filename

        record = {
            "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
            "projects": projects_data
        }

        # 讀取現有紀錄或建立新陣列
        history = []
        if log_path.exists():
            try:
                with open(log_path, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            except json.JSONDecodeError:
                pass # 檔案損毀則從空陣列開始

        history.append(record)

        # 寫入更新後的紀錄
        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=4)
            
        return log_path

if __name__ == "__main__":
    # 簡單的使用範例
    dm = DataManager()
    dummy_projects = [
        {
            "tag": "Dev",
            "window_title": "main.py - WorkSnap",
            "image_path": str(dm.generate_image_path("Dev", "VSCode")),
            "note": "完成視窗自動分類功能測試"
        }
    ]
    saved_file = dm.save_archive_record(dummy_projects)
    print(f"紀錄已成功儲存至: {saved_file}")