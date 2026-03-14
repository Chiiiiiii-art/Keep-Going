# settings_manager.py
import json
from pathlib import Path

# 內建 Notion 風格標籤主題庫
TAG_THEMES = {
    "Red": {"bg": "#4D2D2D", "fg": "#FFA3A3", "border": "none"},
    "Blue": {"bg": "#2D3D4D", "fg": "#A3D1FF", "border": "none"},
    "Green": {"bg": "#2D4D3D", "fg": "#A3FFD1", "border": "none"},
    "Yellow": {"bg": "#4D452D", "fg": "#FFF0A3", "border": "none"},
    "Purple": {"bg": "#3D2D4D", "fg": "#D1A3FF", "border": "none"},
    "Orange": {"bg": "#4D362D", "fg": "#FFC2A3", "border": "none"},
    "Gray": {"bg": "#373737", "fg": "#9B9A97", "border": "none"},
    "Uncategorized": {"bg": "transparent", "fg": "#555555", "border": "1px dashed #333333"}
}

class ConfigManager:
    def __init__(self, config_path="settings.json"):
        self.config_path = Path(config_path)
        # 預設配置：將分類清空
        self.default_config = {
            "categories": [],
            "blacklist_exes": [
                "explorer.exe", "SystemSettings.exe", "NVIDIA Overlay.exe", 
                "TextInputHost.exe", "ApplicationFrameHost.exe", "ShellExperienceHost.exe",
                "Taskmgr.exe"
            ],
            "blacklist_titles": ["Program Manager", "Keep-Going", "設定", "Windows 輸入體驗"]
        }
        self.config = self.load_config()

    def load_config(self):
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "categories" not in data:
                        data["categories"] = self.default_config["categories"]
                    return data
            except Exception:
                return self.default_config
        else:
            self.save_config(self.default_config)
            return self.default_config

    def save_config(self, config):
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=4)

    def get_category_map(self):
        cat_map = {}
        for c in self.config.get("categories", []):
            theme_key = c.get("theme", "Gray")
            cat_map[c["name"]] = {
                "icon": c.get("icon", "📁"),
                "style": TAG_THEMES.get(theme_key, TAG_THEMES["Gray"])
            }
        return cat_map