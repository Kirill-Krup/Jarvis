import os
from thefuzz import process, fuzz
from config.settings import get_search_paths

class FileSearch:
    def find_app(self, app_name: str, alt_name: str = "") -> str | None:
        all_exes = {}
        exclude_dirs = {'windows', 'cache', 'temp', 'node_modules'}

        for search_path in get_search_paths():
            if not os.path.exists(search_path): continue

            for root, dirs, files in os.walk(search_path):
                dirs[:] = [d for d in dirs if d.lower() not in exclude_dirs]
                for file in files:
                    if file.endswith(".exe"):
                        name = file[:-4].lower()
                        all_exes[name] = os.path.join(root, file)

        if not all_exes: return None

        match1, score1 = process.extractOne(app_name, all_exes.keys(), scorer=fuzz.partial_token_sort_ratio)
        match2, score2 = process.extractOne(alt_name, all_exes.keys(), scorer=fuzz.partial_token_sort_ratio)

        print(f"DEBUG: Сравнение {app_name} ({score1}%) и {alt_name} ({score2}%)")

        if max(score1, score2) > 60:
            return all_exes[match1 if score1 >= score2 else match2]

        return None