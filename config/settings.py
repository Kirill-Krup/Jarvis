import os
import json
import getpass

WAKE_WORD = "джарвис"

_USERNAME = getpass.getuser()

BASE_SEARCH_PATHS = [
    "C:/Program Files",
    "C:/Program Files (x86)",
    f"C:/Users/{_USERNAME}/Desktop",
    f"C:/Users/{_USERNAME}/AppData/Roaming",
    f"C:/Users/{_USERNAME}/AppData/Local",
]

def get_search_paths() -> list:
    paths = BASE_SEARCH_PATHS.copy()
    config_path = "config/user_config.json"
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        extra = config.get("extra_drives", [])
        print(f"[settings] extra_drives из конфига: {extra}")
        paths += extra
    print(f"[settings] search_paths: {paths}")
    return paths