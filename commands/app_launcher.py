import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
import json
import os
import subprocess
from pathlib import Path
from transliterate import translit

from config.basic_apps import BASIC_APPS
from core.speakers.speaker import Speaker


class AppLauncher:
    def __init__(self, file_search, speaker=None):
        self.speaker = speaker or Speaker()
        self.memory_path = "config/memory.json"
        self.file_search = file_search
        self.memory = self._load_memory()

        # Если в памяти нет приложений или их меньше 5, запускаем базовое сканирование
        if not self.memory.get("apps") or len(self.memory.get("apps", {})) < 5:
            self.first_run_scan()

    def _load_memory(self):
        if os.path.exists(self.memory_path):
            try:
                with open(self.memory_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"apps": {}}

    def _save_memory(self):
        os.makedirs(os.path.dirname(self.memory_path), exist_ok=True)
        with open(self.memory_path, "w", encoding="utf-8") as f:
            json.dump(self.memory, f, ensure_ascii=False, indent=4)

    def _resolve_from_memory(self, query: str) -> str | None:
        """Поиск пути в памяти с учётом падежей, транслита и синонимов."""
        apps = self.memory.get("apps", {})
        q = query.lower().strip()

        # 1. Прямое совпадение
        if q in apps and os.path.exists(apps[q]):
            return apps[q]

        # 2. Усечение окончания винительного падежа ("телегу" -> "телега")
        if q.endswith("у") and len(q) > 2:
            base_a = q[:-1] + "а"
            if base_a in apps and os.path.exists(apps[base_a]):
                return apps[base_a]
            base_none = q[:-1]
            if base_none in apps and os.path.exists(apps[base_none]):
                return apps[base_none]

        # 3. Транслит
        try:
            q_en = translit(q, "ru", reversed=True)
            if q_en in apps and os.path.exists(apps[q_en]):
                return apps[q_en]
        except Exception:
            pass

        return None

    @staticmethod
    def _open_file(path: str):
        norm = os.path.normpath(path)
        try:
            if "explorer.exe" in norm.lower():
                cmd = ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", "Start-Process explorer.exe -ArgumentList 'shell:MyComputerFolder'"]
            elif "chrome.exe" in norm.lower() or "msedge.exe" in norm.lower() or "browser.exe" in norm.lower():
                cmd = ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", f"Start-Process '{norm}' -ArgumentList 'https://google.com'"]
            else:
                cmd = ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", f"Start-Process '{norm}'"]
            subprocess.Popen(cmd, creationflags=subprocess.CREATE_NO_WINDOW)
        except Exception:
            try:
                os.startfile(norm)
            except Exception:
                os.system(f'start "" "{norm}"')

    def launch(self, app_name: str, honorific: str) -> str:
        app_name_raw = app_name.lower().strip()

        # Быстрый поиск в памяти (0 мс)
        path = self._resolve_from_memory(app_name_raw)
        if path and os.path.exists(path):
            print(f"[AppLauncher] Мгновенный запуск из памяти: '{app_name_raw}' -> {path}")
            self._open_file(path)
            return f"Запускаю {app_name_raw}, {honorific}"

        # Если в памяти нет — ищем на диске
        try:
            app_name_en = translit(app_name_raw, 'ru', reversed=True)
        except Exception:
            app_name_en = ""

        print(f"[SEARCH] Ищу '{app_name_raw}' (или '{app_name_en}') на диске...")
        path = self.file_search.find_app(app_name_raw, alt_name=app_name_en)

        if path and os.path.exists(path):
            self.memory.setdefault("apps", {})[app_name_raw] = path
            if app_name_raw.endswith("у") and len(app_name_raw) > 2:
                self.memory["apps"][app_name_raw[:-1] + "а"] = path
                self.memory["apps"][app_name_raw[:-1]] = path
            self._save_memory()
            self._open_file(path)
            return f"Запускаю {app_name_raw}, {honorific}"

        return f"Не удалось найти {app_name_raw}, {honorific}"

    def first_run_scan(self, force: bool = False):
        """Сканирует базовые приложения и сохраняет все их пути и синонимы в memory.json."""
        print("[SCAN] Сканирование списка базовых приложений...")
        apps_dict = self.memory.setdefault("apps", {})
        found_count = 0

        for item in BASIC_APPS:
            app_id = item["id"]
            title = item.get("title", app_id)
            aliases = item.get("aliases", [app_id])
            fallback_paths = item.get("fallback_paths", [])
            search_names = item.get("search_names", [app_id])

            target_path = None

            # 1. Сначала проверяем прямые системные пути (для блокнота, калькулятора, проводника)
            for fb in fallback_paths:
                if os.path.exists(fb):
                    target_path = fb
                    break

            # 2. Если не найден — ищем через FileSearch (ярлыки Start Menu / Desktop / Steam)
            if not target_path:
                for s_name in search_names:
                    p = self.file_search.find_app(s_name)
                    if p and os.path.exists(p):
                        target_path = p
                        break

            # 3. Сохраняем путь для ВСЕХ синонимов этого приложения
            if target_path:
                found_count += 1
                for alias in aliases:
                    apps_dict[alias.lower().strip()] = target_path
                print(f"[SCAN] {title} -> {target_path} (алиасы: {', '.join(aliases[:4])})")
            else:
                print(f"[SCAN] {title} не найден на компьютере")

        self._save_memory()
        print(f"[OK] Сканирование завершено: сохранено {found_count} базовых программ (всего ключей в памяти: {len(apps_dict)}).")

    def close(self, app_name: str, honorific: str) -> str:
        app_name = app_name.lower().strip()

        # Карта процессов базовых приложений
        system_processes = {
            "проводник": "explorer.exe",
            "explorer": "explorer.exe",
            "консоль": "cmd.exe",
            "терминал": "cmd.exe",
            "командная строка": "cmd.exe",
            "калькулятор": "CalculatorApp.exe",
            "calc": "CalculatorApp.exe",
            "блокнот": "notepad.exe",
            "notepad": "notepad.exe",
            "браузер": "chrome.exe",
            "chrome": "chrome.exe",
            "хром": "chrome.exe",
            "telegram": "Telegram.exe",
            "телеграм": "Telegram.exe",
            "телега": "Telegram.exe",
            "телегу": "Telegram.exe",
            "discord": "Discord.exe",
            "дискорд": "Discord.exe",
            "диску": "Discord.exe",
            "steam": "steam.exe",
            "стим": "steam.exe",
            "код": "Code.exe",
            "vscode": "Code.exe",
            "вс код": "Code.exe",
            "дота": "dota2.exe",
            "доту": "dota2.exe",
            "дота 2": "dota2.exe",
            "кс": "cs2.exe",
            "кску": "cs2.exe",
            "кс 2": "cs2.exe",
            "торрент": "qbittorrent.exe",
            "qbittorrent": "qbittorrent.exe",
            "обс": "obs64.exe",
            "obs": "obs64.exe",
        }

        # Также дополняем из BASIC_APPS
        for item in BASIC_APPS:
            proc = item.get("process_name")
            if proc:
                for al in item.get("aliases", []):
                    if al not in system_processes:
                        system_processes[al.lower().strip()] = proc

        target_exe = system_processes.get(app_name)

        if not target_exe:
            path = self._resolve_from_memory(app_name)
            if not path:
                path = self.file_search.find_app(app_name)

            if path:
                base = os.path.basename(path).lower()
                if base.endswith(".lnk"):
                    stem = Path(base).stem.lower()
                    target_exe = system_processes.get(stem, stem + ".exe")
                elif base.endswith(".url"):
                    # Steam url shortcut
                    target_exe = system_processes.get(app_name)
                else:
                    target_exe = base

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

        return f"Не удалось определить процесс для {app_name}, {honorific}"
