import os
import datetime


LOG_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..",
    "jarvis_debug.log"
)
LOG_FILE = os.path.abspath(LOG_FILE)


def log(msg: str):
    line = f"[{datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass