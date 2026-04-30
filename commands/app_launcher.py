import subprocess
import json
import os
from commands.file_search import FileSearch
from transliterate import translit

class AppLauncher:
    def __init__(self, file_search):
        self.memory_path = "config/memory.json"
        self.file_search = file_search
        self.memory = self._load_memory()

        if not self.memory.get("apps"):
            self.first_run_scan()

    def _load_memory(self):
        if os.path.exists(self.memory_path):
            with open(self.memory_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"apps": {}}

    def _save_memory(self):
        os.makedirs(os.path.dirname(self.memory_path), exist_ok=True)
        with open(self.memory_path, "w", encoding="utf-8") as f:
            json.dump(self.memory, f, ensure_ascii=False, indent=4)

    def launch(self, app_name: str, honorific: str) -> str:
        app_name_raw = app_name.lower().strip()

        if app_name_raw in self.memory.get("apps", {}):
            path = self.memory["apps"][app_name_raw]
            if os.path.exists(path):
                os.startfile(path)
                return f"Запускаю {app_name_raw}, {honorific}"

        app_name_en = translit(app_name_raw, 'ru', reversed=True)
        print(f"🔍 Ищу '{app_name_raw}' (или '{app_name_en}') на диске...")

        path = self.file_search.find_app(app_name_raw, alt_name=app_name_en)

        if path and os.path.exists(path):
            self.memory.setdefault("apps", {})[app_name_raw] = path
            self._save_memory()
            os.startfile(path)
            return f"Нашёл и запускаю {app_name_raw}, {honorific}"

        return f"Не удалось найти {app_name_raw}, {honorific}"

    def first_run_scan(self):
        print("🚀 Первый запуск: сканирую базовые приложения...")
        essential_apps = ["telegram", "discord", "steam", "chrome", "operagx", "spotify"]

        for app in essential_apps:
            path = self.file_search.find_app(app)
            if path:
                print(f"[SCAN] {app} -> {path}")
                self.memory["apps"][app] = path
            else:
                print(f"[SCAN] {app} не найден")

        self._save_memory()
        print("✅ Базовые пути сохранены в память.")

    def close(self, app_name: str, honorific: str) -> str:
        app_name = app_name.lower().strip()

        system_processes = {
            "проводник": "explorer.exe",
            "explorer": "explorer.exe",
            "консоль": "cmd.exe",
            "терминал": "cmd.exe",
            "командная строка": "cmd.exe",
            "калькулятор": "CalculatorApp.exe",
            "браузер": "chrome.exe",
            "chrome": "chrome.exe",
            "telegram": "Telegram.exe",
            "телеграм": "Telegram.exe",
            "discord": "Discord.exe",
            "дискорд": "Discord.exe",
            "steam": "steam.exe",
            "стим": "steam.exe",
        }

        target_exe = system_processes.get(app_name)

        if not target_exe:
            if app_name in self.memory["apps"]:
                target_exe = os.path.basename(self.memory["apps"][app_name])
            else:
                path = self.file_search.find_app(app_name)
                if path:
                    target_exe = os.path.basename(path)

        if target_exe:
            exe_name = os.path.basename(target_exe).lower()

            if exe_name == "explorer.exe":
                os.system('taskkill /FI "IMAGENAME eq explorer.exe" /FI "WINDOWTITLE ne Taskbar"')
                return f"Окна проводника закрыты, {honorific}"

            exit_code = os.system(f'taskkill /F /IM "{exe_name}" /T')
            if exit_code == 0:
                return f"Приложение {app_name} закрыто, {honorific}"
            else:
                return f"Не удалось закрыть {app_name}, {honorific}"

