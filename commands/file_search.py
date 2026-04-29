import os
from config.settings import get_search_paths


class FileSearch:

    def find_app(self, app_name: str) -> str | None:
        for search_path in get_search_paths():
            result = self._search_in_folder(search_path, app_name)
            if result:
                return result
        return None

    def _search_in_folder(self, folder: str, app_name: str) -> str | None:
        if not os.path.exists(folder):
            return None

        for root, dirs, files in os.walk(folder):
            for file in files:
                if (file.endswith(".exe")
                        and app_name.lower() in file.lower()):
                    return os.path.join(root, file)
        return None