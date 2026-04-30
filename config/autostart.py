import os
import sys
import winreg


APP_NAME = "JarvisVoiceAssistant"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _build_command() -> str:
    if getattr(sys, "frozen", False):
        exe_path = sys.executable
        return f'"{exe_path}" --autostart'

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    main_py = os.path.join(project_root, "main.py")
    return f'"{sys.executable}" "{main_py}" --autostart'


def enable_autostart():
    command = _build_command()
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, command)


def disable_autostart():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, APP_NAME)
    except FileNotFoundError:
        pass
    except OSError:
        pass


def is_autostart_enabled() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, APP_NAME)
            return bool(value)
    except FileNotFoundError:
        return False
    except OSError:
        return False