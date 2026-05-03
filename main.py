import os
import sys
import ctypes

from app.jarvis_app import JarvisApp


def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def relaunch_as_admin():
    script = os.path.abspath(sys.argv[0])
    params = " ".join(f'"{a}"' for a in sys.argv[1:])
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, f'"{script}" {params}', None, 1
    )
    sys.exit(0)


if __name__ == "__main__":
    if not is_admin():
        relaunch_as_admin()

    app = JarvisApp()
    app.start()