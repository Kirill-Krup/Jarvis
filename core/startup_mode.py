import sys


def should_start_hidden() -> bool:
    return "--autostart" in sys.argv