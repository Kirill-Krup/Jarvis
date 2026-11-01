"""Запуск и закрытие программ по названию (русскому, английскому или «на слух»)."""
import json
import os
import subprocess
from pathlib import Path

from transliterate import translit

from config.basic_apps import BASIC_APPS
from nlu import lexicon

MEMORY_PATH = "config/memory.json"
BROWSER_EXES = ("chrome.exe", "msedge.exe", "browser.exe")
CASE_ENDINGS = ("у", "ю", "а", "ы", "е")   # телегу, идею, доте…
FUZZY_MIN_SCORE = 82


class AppLauncher:
    def __init__(self, file_search, speaker=None):
        self.speaker = speaker
        self.file_search = file_search
        self.memory = self._load_memory()
        self._basic_by_id = {item["id"]: item for item in BASIC_APPS}
        self._builtin_names = lexicon.builtin_names()

        apps = self.memory.get("apps", {})
        if len(apps) < 5:
            self.first_run_scan()

    # ------------------------------------------------------------- память

    def _load_memory(self) -> dict:
        if os.path.exists(MEMORY_PATH):
            try:
                with open(MEMORY_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"apps": {}}

    def _save_memory(self):
        os.makedirs(os.path.dirname(MEMORY_PATH), exist_ok=True)
        with open(MEMORY_PATH, "w", encoding="utf-8") as f:
            json.dump(self.memory, f, ensure_ascii=False, indent=4)

    @property
    def apps(self) -> dict:
        return self.memory.setdefault("apps", {})

    def known_names(self) -> set[str]:
        """Все названия, которые Джарвис умеет открывать (для исправления речи)."""
        names = {k for k in self.apps if not k.startswith("folder:")}
        return names | set(self._builtin_names)

    # ------------------------------------------------------------- поиск

    def _existing(self, key: str) -> str | None:
        path = self.apps.get(key)
        return path if path and os.path.exists(path) else None

    def _from_memory(self, query: str) -> str | None:
        """Точное совпадение с учётом падежей («телегу» -> «телега»)."""
        if path := self._existing(query):
            return path
        if len(query) > 2 and query.endswith(CASE_ENDINGS):
            for variant in (query[:-1] + "а", query[:-1], query[:-1] + "я"):
                if path := self._existing(variant):
                    return path
        try:
            return self._existing(translit(query, "ru", reversed=True))
        except Exception:
            return None

    def _scan_basic(self, app_id: str) -> str | None:
        """Ищет одну программу из BASIC_APPS и запоминает её под всеми именами."""
        item = self._basic_by_id.get(app_id)
        if not item:
            return None
        path = next((p for p in item.get("fallback_paths", []) if os.path.exists(p)), None)
        if not path:
            for name in item.get("search_names", [app_id]):
                found = self.file_search.find_app(name)
                if found and os.path.exists(found):
                    path = found
                    break
        if path:
            for alias in item.get("aliases", [app_id]):
                self.apps[alias.lower().strip()] = path
            self._save_memory()
        return path

    def resolve(self, query: str) -> str | None:
        """Путь к программе по названию. Понимает падежи, транслит, английские
        названия, записанные по-русски, и мелкие ошибки распознавания."""
        query = query.lower().strip()
        if path := self._from_memory(query):
            return path

        # известные программы: «интеллиджей идея» -> IntelliJ IDEA
        found = lexicon.best_match(query, self._builtin_names, FUZZY_MIN_SCORE)
        if found:
            app_id = self._builtin_names[found[0]]
            print(f"[AppLauncher] «{query}» похоже на «{found[0]}» ({found[1]}%)")
            path = self._from_memory(found[0]) or self._scan_basic(app_id)
            if path:
                self._remember(query, path)
            return path  # программа известна: если её нет на ПК, чужую не запускаем

        # уже найденные ранее программы (в том числе произвольные)
        found = lexicon.best_match(
            query, [k for k in self.apps if not k.startswith("folder:")], 88)
        if found and (path := self._existing(found[0])):
            return path

        # поиск по диску: русское, транслит и английское звучание
        try:
            alt = translit(query, "ru", reversed=True)
        except Exception:
            alt = ""
        path = self.file_search.find_app(query, alt_name=alt)
        if path and os.path.exists(path):
            self._remember(query, path)
            return path
        return None

    def _remember(self, query: str, path: str):
        self.apps[query] = path
        self._save_memory()

    # ------------------------------------------------------------ запуск

    @staticmethod
    def _open_file(path: str):
        norm = os.path.normpath(path)
        lower = norm.lower()
        try:
            if lower.endswith("explorer.exe"):
                subprocess.Popen(["explorer.exe", "shell:MyComputerFolder"])
            elif lower.endswith(BROWSER_EXES):
                subprocess.Popen([norm, "https://google.com"])
            else:
                os.startfile(norm)
        except OSError:
            subprocess.Popen(f'start "" "{norm}"', shell=True)

    def launch(self, app_name: str, honorific: str = "") -> str:
        name = app_name.lower().strip()
        path = self.resolve(name)
        if path:
            print(f"[AppLauncher] Запуск: '{name}' -> {path}")
            self._open_file(path)
            return f"Запускаю {name}, {honorific}" if honorific else f"Запускаю {name}"
        return f"Не удалось найти {name}, {honorific}" if honorific else f"Не удалось найти {name}"

    def first_run_scan(self):
        """Первичное сканирование базовых программ (быстро: Start Menu и типовые пути)."""
        print("[SCAN] Сканирование базовых приложений...")
        found = sum(1 for item in BASIC_APPS if self._scan_basic(item["id"]))
        print(f"[OK] Найдено программ: {found} из {len(BASIC_APPS)}")

    # ----------------------------------------------------------- закрытие

    def _process_name(self, app_name: str) -> str | None:
        """Имя процесса для taskkill."""
        for item in BASIC_APPS:
            aliases = [a.lower() for a in item.get("aliases", [])]
            if app_name in aliases and item.get("process_name"):
                return item["process_name"]

        found = lexicon.best_match(app_name, self._builtin_names, FUZZY_MIN_SCORE)
        if found:
            item = self._basic_by_id[self._builtin_names[found[0]]]
            if item.get("process_name"):
                return item["process_name"]

        path = self._from_memory(app_name) or self.file_search.find_app(app_name)
        if path:
            base = os.path.basename(path).lower()
            return base if not base.endswith((".lnk", ".url")) else Path(base).stem + ".exe"
        return None

    def close(self, app_name: str, honorific: str = "") -> str:
        app_name = app_name.lower().strip()
        suffix = f", {honorific}" if honorific else ""
        exe = self._process_name(app_name)
        if not exe:
            return f"Не удалось определить процесс для {app_name}{suffix}"

        exe = os.path.basename(exe)
        if exe.lower() == "explorer.exe":
            os.system('taskkill /FI "IMAGENAME eq explorer.exe" /FI "WINDOWTITLE ne Taskbar"')
            return f"Окна проводника закрыты{suffix}"

        code = subprocess.call(["taskkill", "/F", "/IM", exe, "/T"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if code == 0:
            return f"Приложение {app_name} закрыто{suffix}"
        return f"Не удалось закрыть {app_name}{suffix}"
