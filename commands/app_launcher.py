import subprocess
import json
import os

from commands.file_search import FileSearch


class AppLauncher:

    def __init__(self):
        self.file_search = FileSearch()
        self.memory_path = "config/memory.json"
        self.memory = self._load_memory()
        print("AppLauncher готов ✓")

    def launch(self, app_name: str, honorific: str) -> str:
        if app_name in self.memory["apps"]:
            path = self.memory["apps"][app_name]
            subprocess.Popen(path)
            return f"Запускаю {app_name}, {honorific}"

        print(f"Ищу {app_name} на диске...")
        path = self.file_search.find_app(app_name)

        if path:
            self.memory["apps"][app_name] = path
            self._save_memory()
            subprocess.Popen(path)
            return f"Нашёл и запускаю {app_name}, {honorific}"

        return f"Не могу найти {app_name}, {honorific}"

    def _load_memory(self) -> dict:
        if os.path.exists(self.memory_path):
            with open(self.memory_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"apps": {}}

    def _save_memory(self):
        with open(self.memory_path, "w", encoding="utf-8") as f:
            json.dump(self.memory, f, ensure_ascii=False, indent=2)