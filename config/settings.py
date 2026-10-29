import os
import json
import getpass
import string

WAKE_WORD = "джарвис"

_USERNAME = getpass.getuser()

BASE_SEARCH_PATHS = [
    # Меню Пуск и Рабочие столы (содержат 95% ярлыков всех приложений и игр)
    "C:/ProgramData/Microsoft/Windows/Start Menu/Programs",
    f"C:/Users/{_USERNAME}/AppData/Roaming/Microsoft/Windows/Start Menu/Programs",
    f"C:/Users/{_USERNAME}/Desktop",
    "C:/Users/Public/Desktop",
    "C:/Program Files",
    "C:/Program Files (x86)",
    f"C:/Users/{_USERNAME}/AppData/Local/Programs",
]


def get_search_paths() -> list:
    paths = []
    # Добавляем стандартные пути
    for p in BASE_SEARCH_PATHS:
        if os.path.exists(p) and p not in paths:
            paths.append(p)

    # Автоматически обнаруживаем диски и популярные папки с играми и программами
    for letter in string.ascii_uppercase:
        drive = f"{letter}:/"
        if os.path.exists(drive):
            # Проверяем типовые папки для игр и лаунчеров
            for sub in ("Games", "Steam", "Steam/steamapps/common", "SteamLibrary", "SteamLibrary/steamapps/common", "Program Files", "Program Files (x86)"):
                candidate = f"{letter}:/{sub}"
                if os.path.exists(candidate) and candidate not in paths:
                    paths.append(candidate)

    # Добавляем пути из конфига
    config_path = "config/user_config.json"
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            extra = config.get("extra_drives", [])
            for ed in extra:
                if os.path.exists(ed) and ed not in paths:
                    paths.append(ed)
        except Exception:
            pass

    return paths
