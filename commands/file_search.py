import os
import json
from pathlib import Path
from thefuzz import process, fuzz
from transliterate import translit
from config.settings import get_search_paths


APP_INDEX_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..",
    "app_index.json"
)


class FileSearch:

    def __init__(self):
        self.exclude_dirs = {
            "windows", "cache", "temp", "tmp",
            "node_modules", "$recycle.bin",
            "system volume information", "__pycache__"
        }
        self.app_extensions = {".exe", ".lnk"}
        self._index = None

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

    def _safe_walk(self, search_path: str):
        try:
            for root, dirs, files in os.walk(search_path, topdown=True):
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
                    print(f"[FileSearch] Загружен индекс приложений: {len(self._index)} записей")
                    return self._index
            except Exception:
                print("[FileSearch] Не удалось прочитать app_index.json, пересканируем")

        self._index = {}
        return self._index

    def _save_index(self):
        if self._index is None:
            return
        try:
            with open(APP_INDEX_FILE, "w", encoding="utf-8") as f:
                json.dump(self._index, f, ensure_ascii=False, indent=2)
            print(f"[FileSearch] Индекс приложений сохранён: {len(self._index)} записей")
        except Exception as e:
            print(f"[FileSearch] Ошибка сохранения app_index.json: {e}")

    def build_full_index(self):
        index = {}
        for search_path in get_search_paths():
            if not os.path.exists(search_path):
                continue
            print(f"[FileSearch] Полный скан: {search_path}")

            for root, _, files in self._safe_walk(search_path):
                for file in files:
                    ext = Path(file).suffix.lower()
                    if ext not in self.app_extensions:
                        continue

                    stem = Path(file).stem
                    norm_name = self._normalize(stem)
                    full_path = os.path.join(root, file)

                    if norm_name not in index:
                        index[norm_name] = full_path

        self._index = index
        self._save_index()


    def _get_candidates(self) -> list[dict]:
        idx = self._load_index()
        candidates = []

        for name, path in idx.items():
            if os.path.exists(path):
                candidates.append({"name": name, "path": path, "ext": Path(path).suffix.lower()})

        if not candidates:
            candidates = self._collect_app_candidates()
            self._index = {c["name"]: c["path"] for c in candidates}
            self._save_index()

        return candidates

    def _collect_app_candidates(self) -> list[dict]:
        candidates = []
        for search_path in get_search_paths():
            if not os.path.exists(search_path):
                continue
            print(f"[FileSearch] Сканирую приложения: {search_path}")
            for root, _, files in self._safe_walk(search_path):
                for file in files:
                    ext = Path(file).suffix.lower()
                    if ext not in self.app_extensions:
                        continue
                    stem = Path(file).stem
                    candidates.append({
                        "name": self._normalize(stem),
                        "path": os.path.join(root, file),
                        "ext": ext,
                    })
        print(f"[FileSearch] Кандидатов приложений: {len(candidates)}")
        return candidates


    def find_app(self, app_name: str, alt_name: str = "") -> str | None:
        app_name_norm = self._normalize(app_name)
        alt_name_norm = self._normalize(alt_name) if alt_name else ""

        candidates = self._get_candidates()
        if not candidates:
            return None

        names = [item["name"] for item in candidates]

        best_main = process.extractOne(app_name_norm, names, scorer=fuzz.token_sort_ratio)
        best_alt = process.extractOne(alt_name_norm, names, scorer=fuzz.token_sort_ratio) if alt_name_norm else None

        best_name, best_score = best_main or ("", 0)
        if best_alt and best_alt[1] > best_score:
            best_name, best_score = best_alt

        print(f"[FileSearch] find_app: main='{app_name_norm}', alt='{alt_name_norm}' → '{best_name}' ({best_score}%)")

        if best_score < 70:
            return None

        matched = [item for item in candidates if item["name"] == best_name]
        if not matched:
            return None

        def priority(item: dict) -> int:
            p = item["path"].lower()
            score = 0
            if item["ext"] == ".exe":
                score += 50
            if "program files" in p:
                score += 30
            if "desktop" in p:
                score += 10
            if "appdata" in p:
                score += 5
            return score

        matched.sort(key=priority, reverse=True)
        result = matched[0]["path"]
        print(f"[FileSearch] → Путь приложения: {result}")

        idx = self._load_index()
        idx[self._normalize(best_name)] = result
        self._save_index()

        return result


    def find_folder(self, folder_name: str) -> str | None:
        name_orig = self._normalize(folder_name)
        name_lat = self._to_translit(folder_name)

        print(f"[FileSearch] find_folder: '{name_orig}' / '{name_lat}'")

        folder_candidates = []

        for search_path in get_search_paths():
            if not os.path.exists(search_path):
                continue
            print(f"[FileSearch] Сканирую папки: {search_path}")

            for root, dirs, _ in self._safe_walk(search_path):
                for directory in dirs:
                    dir_norm = self._normalize(directory)
                    dir_lat = self._to_translit(directory)
                    folder_candidates.append({
                        "name_orig": dir_norm,
                        "name_lat": dir_lat,
                        "path": os.path.join(root, directory),
                    })

        print(f"[FileSearch] Кандидатов папок: {len(folder_candidates)}")

        if not folder_candidates:
            return None

        orig_names = [item["name_orig"] for item in folder_candidates]
        best_orig = process.extractOne(name_orig, orig_names, scorer=fuzz.token_sort_ratio)

        lat_names = [item["name_lat"] for item in folder_candidates]
        best_lat = process.extractOne(name_lat, lat_names, scorer=fuzz.token_sort_ratio)

        print(f"[FileSearch] Вариант orig: '{best_orig}', lat: '{best_lat}'")

        best_name = None
        best_score = 0
        use_orig = True

        if best_orig:
            best_name, best_score = best_orig
        if best_lat and best_lat[1] > best_score:
            best_name, best_score = best_lat
            use_orig = False

        print(f"[FileSearch] Лучший fuzzy: '{best_name}' ({best_score}%)")

        if best_score < 75:
            print(f"[FileSearch] Слишком низкий score, не нашёл")
            return None

        if use_orig:
            matched = [item for item in folder_candidates if item["name_orig"] == best_name]
        else:
            matched = [item for item in folder_candidates if item["name_lat"] == best_name]

        if not matched:
            return None

        matched.sort(key=lambda x: len(x["path"]))
        result = matched[0]["path"]
        print(f"[FileSearch] → Путь папки: {result}")
        return result