import os
import json

WAKE_WORD = "джарвис"

BASE_SEARCH_PATHS = [
    "C:/Program Files",
    "C:/Program Files (x86)",
    f"C:/Users/{os.environ.get('USERNAME', 'User')}/Desktop",
    f"C:/Users/{os.environ.get('USERNAME', 'User')}/AppData/Roaming",
    f"C:/Users/{os.environ.get('USERNAME', 'User')}/AppData/Local",
]

def get_search_paths() -> list:
    paths = BASE_SEARCH_PATHS.copy()
    config_path = "config/user_config.json"
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        paths += config.get("extra_drives", [])
    return paths