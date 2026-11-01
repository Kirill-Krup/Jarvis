"""Открытие ссылок в браузере по умолчанию."""
import os
import webbrowser


def open_url(url: str):
    try:
        os.startfile(url)
    except OSError:
        webbrowser.open(url)
