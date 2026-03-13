import json
from pathlib import Path

class ConfigManager:
    def __init__(self, config_path="settings.json"):
        self.config_path = Path(config_path)
        self.default_config = {
            "rules": {
                "Art": ["Photoshop.exe", "ClipStudioPaint.exe", "Krita.exe"],
                "Dev": ["Code.exe", "devenv.exe", "WindowsTerminal.exe"],
                "Writing": ["Notion.exe", "Obsidian.exe"]
            },
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
                    return json.load(f)
            except Exception:
                return self.default_config
        else:
            self.save_config(self.default_config)
            return self.default_config

    def save_config(self, config):
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=4)