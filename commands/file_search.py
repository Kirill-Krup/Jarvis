import os
import json
from pathlib import Path
from thefuzz import process, fuzz
from transliterate import translit


APP_INDEX_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..",
    "app_index.json"
)

APP_ALIASES = {
    "дота": ["dota", "dota 2", "dota2"],
    "доту": ["dota", "dota 2", "dota2"],
    "доте": ["dota", "dota 2", "dota2"],
    "кс": ["cs2", "csgo", "counter strike", "counter-strike"],
    "ксго": ["cs2", "csgo", "counter strike", "counter-strike"],
    "контра": ["cs2", "csgo", "counter strike", "counter-strike"],
    "контру": ["cs2", "csgo", "counter strike", "counter-strike"],
    "телега": ["telegram"],
    "телегу": ["telegram"],
    "телеграм": ["telegram"],
    "стим": ["steam"],
    "дискорд": ["discord"],
    "диск": ["discord"],
    "хром": ["chrome", "google chrome"],
    "гугл": ["chrome", "google chrome"],
    "яндекс": ["yandex", "browser"],
    "спотифай": ["spotify"],
    "калькулятор": ["calculator", "calc", "calculatorapp"],
    "блокнот": ["notepad"],
    "проводник": ["explorer"],
    "терминал": ["wt", "cmd", "powershell"],
    "консоль": ["cmd", "powershell", "wt"],
    "ворд": ["word", "winword"],
    "эксель": ["excel"],
}


class FileSearch:

    def __init__(self):
        self.exclude_dirs = {
            "windows", "cache", "temp", "tmp",
            "node_modules", "$recycle.bin",
            "system volume information", "__pycache__"
        }
        self.app_extensions = {".exe", ".lnk", ".url"}
        self._index = None
        self._cached_candidates = None

    def _normalize(self, text: str) -> str:
        return (
            text.lower()
            .replace("_", " ").replace("-", " ").replace(".", " ")
            .strip()
        )

    def _to_translit(self, text: str) -> str:
        try:
            return translit(text, 'ru', reversed=True).lower().strip()
        except Exception:
            return text

    def _safe_walk(self, search_path: str, max_depth: int = 4):
        try:
            base_depth = search_path.count(os.sep)
            for root, dirs, files in os.walk(search_path, topdown=True):
                cur_depth = root.count(os.sep) - base_depth
                if cur_depth >= max_depth:
                    dirs.clear()
                    continue
                dirs[:] = [d for d in dirs if d.lower() not in self.exclude_dirs]
                yield root, dirs, files
        except (PermissionError, OSError):
            return

    def _load_index(self) -> dict:
        if self._index is not None:
            return self._index

        if os.path.exists(APP_INDEX_FILE):
            try:
                with open(APP_INDEX_FILE, "r", encoding="utf-8") as f:
                    self._index = json.load(f)
                    return self._index
            except Exception:
                pass

        self._index = {}
        return self._index

    def _save_index(self):
        if self._index is None:
            return
        try:
            with open(APP_INDEX_FILE, "w", encoding="utf-8") as f:
                json.dump(self._index, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[FileSearch] Ошибка сохранения app_index.json: {e}")

    def _get_candidates(self) -> list[dict]:
        if self._cached_candidates:
            return self._cached_candidates
        self._cached_candidates = self._collect_app_candidates()
        return self._cached_candidates

    def _collect_app_candidates(self) -> list[dict]:
        candidates = []
        seen_paths = set()

        # Tier 1: Быстрые пути (ярлыки Start Menu, Рабочий стол, папки с играми)
        user = os.environ.get("USERNAME", "")
        tier1_paths = [
            os.path.expandvars("%ProgramData%/Microsoft/Windows/Start Menu/Programs"),
            os.path.expandvars("%APPDATA%/Microsoft/Windows/Start Menu/Programs"),
            os.path.expandvars("%USERPROFILE%/Desktop"),
            "C:/Users/Public/Desktop",
            "E:/Games",
            "D:/Games",
            "C:/Games",
            "D:/Steam",
            "D:/Steam/steamapps/common",
            "C:/Program Files (x86)/Steam/steamapps/common",
            "E:/SteamLibrary",
            "E:/SteamLibrary/steamapps/common",
            "D:/SteamLibrary",
            "D:/SteamLibrary/steamapps/common",
            f"C:/Users/{user}/AppData/Local/Programs",
        ]

        tier2_paths = [
            "C:/Program Files",
            "C:/Program Files (x86)",
        ]

        # Обход Tier 1
        for p in tier1_paths:
            if not os.path.exists(p):
                continue
            for root, _, files in self._safe_walk(p, max_depth=4):
                for file in files:
                    ext = Path(file).suffix.lower()
                    if ext not in self.app_extensions:
                        continue
                    stem = Path(file).stem
                    s_lower = stem.lower()
                    if any(bad in s_lower for bad in ["uninstall", "unins000", "crashpad", "update_helper"]):
                        continue
                    full_path = os.path.join(root, file)
                    if full_path in seen_paths:
                        continue
                    seen_paths.add(full_path)
                    candidates.append({
                        "name": self._normalize(stem),
                        "raw_name": s_lower,
                        "path": full_path,
                        "ext": ext,
                        "tier": 1
                    })

        # Обход Tier 2 (только верхние уровни Program Files)
        for p in tier2_paths:
            if not os.path.exists(p):
                continue
            for root, _, files in self._safe_walk(p, max_depth=2):
                for file in files:
                    ext = Path(file).suffix.lower()
                    if ext not in self.app_extensions:
                        continue
                    stem = Path(file).stem
                    s_lower = stem.lower()
                    if any(bad in s_lower for bad in ["uninstall", "unins000", "crashpad", "update_helper"]):
                        continue
                    full_path = os.path.join(root, file)
                    if full_path in seen_paths:
                        continue
                    seen_paths.add(full_path)
                    candidates.append({
                        "name": self._normalize(stem),
                        "raw_name": s_lower,
                        "path": full_path,
                        "ext": ext,
                        "tier": 2
                    })

        return candidates

    def find_app(self, app_name: str, alt_name: str = "") -> str | None:
        raw_query = app_name.lower().strip()
        queries = [self._normalize(raw_query)]

        # Проверяем алиасы (например: "доту" -> ["dota", "dota 2", "dota2"])
        if raw_query in APP_ALIASES:
            queries.extend(APP_ALIASES[raw_query])

        # Снятие падежных окончаний винительного падежа ("доту" -> "дота", "телегу" -> "телега")
        if raw_query.endswith("у") and len(raw_query) > 2:
            base_a = raw_query[:-1] + "а"
            base_none = raw_query[:-1]
            queries.append(base_a)
            queries.append(base_none)
            if base_a in APP_ALIASES:
                queries.extend(APP_ALIASES[base_a])

        # Добавляем транслитерацию
        tr = self._to_translit(raw_query)
        if tr not in queries:
            queries.append(tr)
        if alt_name:
            norm_alt = self._normalize(alt_name)
            if norm_alt not in queries:
                queries.append(norm_alt)

        candidates = self._get_candidates()
        if not candidates:
            return None

        best_candidate = None
        best_score = 0

        for cand in candidates:
            c_name = cand["name"]
            score = 0

            for q in queries:
                q_norm = self._normalize(q)
                if not q_norm:
                    continue

                # Точное совпадение
                if c_name == q_norm or cand["raw_name"] == q_norm:
                    score = max(score, 100)
                # Вхождение целого слова или фразы
                elif f" {q_norm} " in f" {c_name} ":
                    score = max(score, 95)
                elif c_name.startswith(q_norm) or q_norm in c_name:
                    score = max(score, 88)
                else:
                    score = max(score, fuzz.token_sort_ratio(q_norm, c_name))
                    # «minecraft launcher» не должно совпадать с любым «Launcher»:
                    # набор слов сравниваем, только если все слова запроса есть в названии
                    if set(q_norm.split()) <= set(c_name.split()):
                        score = max(score, fuzz.token_set_ratio(q_norm, c_name))

            # Бонус за ярлыки (.lnk, .url), так как они указывают на основное приложение
            if cand["ext"] in (".lnk", ".url"):
                score += 5
            if cand.get("tier") == 1:
                score += 5

            if score > best_score:
                best_score = score
                best_candidate = cand

        # короткие запросы дают много случайных совпадений: для них порог выше
        min_score = 80 if len(raw_query) >= 6 else 90
        if best_candidate and best_score >= min_score:
            print(f"[FileSearch] find_app: query='{raw_query}' -> '{best_candidate['name']}' ({best_score}%)")
            print(f"[FileSearch] -> Путь приложения: {best_candidate['path']}")

            idx = self._load_index()
            idx[raw_query] = best_candidate["path"]
            self._save_index()
            return best_candidate["path"]

        print(f"[FileSearch] find_app: query='{raw_query}' не найден (лучший: {best_score}%)")
        return None

    def find_folder(self, folder_name: str) -> str | None:
        name_orig = self._normalize(folder_name)
        name_lat = self._to_translit(folder_name)

        user = os.environ.get("USERNAME", "")
        folder_paths = [
            os.path.expandvars("%USERPROFILE%/Desktop"),
            os.path.expandvars("%USERPROFILE%/Downloads"),
            os.path.expandvars("%USERPROFILE%/Documents"),
            f"C:/Users/{user}",
            "E:/",
            "D:/",
            "C:/",
        ]

        folder_candidates = []
        for search_path in folder_paths:
            if not os.path.exists(search_path):
                continue
            for root, dirs, _ in self._safe_walk(search_path, max_depth=2):
                for directory in dirs:
                    dir_norm = self._normalize(directory)
                    dir_lat = self._to_translit(directory)
                    folder_candidates.append({
                        "name_orig": dir_norm,
                        "name_lat": dir_lat,
                        "path": os.path.join(root, directory),
                    })

        if not folder_candidates:
            return None

        orig_names = [item["name_orig"] for item in folder_candidates]
        best_orig = process.extractOne(name_orig, orig_names, scorer=fuzz.token_sort_ratio)

        lat_names = [item["name_lat"] for item in folder_candidates]
        best_lat = process.extractOne(name_lat, lat_names, scorer=fuzz.token_sort_ratio)

        best_name = None
        best_score = 0
        use_orig = True

        if best_orig:
            best_name, best_score = best_orig
        if best_lat and best_lat[1] > best_score:
            best_name, best_score = best_lat
            use_orig = False

        if best_score < 65:
            return None

        if use_orig:
            matched = [item for item in folder_candidates if item["name_orig"] == best_name]
        else:
            matched = [item for item in folder_candidates if item["name_lat"] == best_name]

        if not matched:
            return None

        matched.sort(key=lambda x: len(x["path"]))
        result = matched[0]["path"]
        print(f"[FileSearch] -> Путь папки: {result}")
        return result
