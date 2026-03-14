import os
import json
from datetime import datetime
from pathlib import Path
from settings_manager import ConfigManager

class DataManager:
    def __init__(self, base_dir="WorkSnap_Data"):
        self.base_dir = Path(base_dir)
        # 動態載入使用者自訂的分類
        config_mgr = ConfigManager()
        config = config_mgr.load_config()
        self.categories = [c["name"] for c in config.get("categories", [])]
        if "Uncategorized" not in self.categories:
            self.categories.append("Uncategorized")
            
        self.logs_dir = self.base_dir / "Logs"
        self._init_directories()

    def _init_directories(self):
        for category in self.categories:
            (self.base_dir / category).mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def generate_image_path(self, tag, keyword=""):
        # 允許建立新資料夾（針對後來新增的自訂標籤）
        target_dir = self.base_dir / tag
        target_dir.mkdir(parents=True, exist_ok=True)
        
        now = datetime.now()
        timestamp_str = now.strftime("%Y%m%d_%H%M%S")
        safe_keyword = "".join([c for c in keyword if c.isalnum() or c in (' ', '_')]).rstrip()
        safe_keyword = f"_{safe_keyword}" if safe_keyword else ""
        
        filename = f"{timestamp_str}{safe_keyword}.png"
        return target_dir / filename

    def save_archive_record(self, projects_data):
        now = datetime.now()
        log_filename = f"history_{now.strftime('%Y_%m')}.json"
        log_path = self.logs_dir / log_filename

        record = {"timestamp": now.strftime("%Y-%m-%d %H:%M:%S"), "projects": projects_data}
        history = []
        if log_path.exists():
            try:
                with open(log_path, 'r', encoding='utf-8') as f: history = json.load(f)
            except json.JSONDecodeError: pass 

        history.append(record)
        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=4)
        return log_path