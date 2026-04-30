import sys
import traceback

from app.jarvis_app import JarvisApp
from core.logging_utils import log


if __name__ == "__main__":
    try:
        JarvisApp().start()
    except SystemExit as e:
        log(f"SystemExit: code={e.code}")
    except BaseException:
        log(f"Критическая ошибка:\n{traceback.format_exc()}")
        sys.exit(1)