import webbrowser
import subprocess
import time
import pyautogui

def _focus_browser():
    result = subprocess.run(
        ['powershell', '-Command',
         '(Get-Process | Where-Object {$_.MainWindowTitle -match "YouTube|Chrome|Firefox|Edge"} '
         '| Select-Object -First 1).MainWindowTitle'],
        capture_output=True, text=True
    )
    title = result.stdout.strip()
    if title:
        subprocess.run(
            ['powershell', '-Command',
             f'(New-Object -ComObject WScript.Shell).AppActivate("{title}")'],
            capture_output=True
        )
        time.sleep(0.3)
        return True
    return False


def handle_youtube_pause(cmd, ctx):
    if _focus_browser():
        pyautogui.press('k')
        return ctx.reply("Переключаю воспроизведение")
    return ctx.reply("Браузер с YouTube не найден")


def handle_youtube_fullscreen(cmd, ctx):
    if _focus_browser():
        pyautogui.press('f')
        return ctx.reply("Переключаю полноэкранный режим")
    return ctx.reply("Браузер с YouTube не найден")


def handle_youtube_mute(cmd, ctx):
    if _focus_browser():
        pyautogui.press('m')
        return ctx.reply("Переключаю звук")
    return ctx.reply("Браузер с YouTube не найден")


def handle_youtube_forward(cmd, ctx):
    if _focus_browser():
        pyautogui.press('l')
        return ctx.reply("Перематываю вперёд")
    return ctx.reply("Браузер с YouTube не найден")


def handle_youtube_backward(cmd, ctx):
    if _focus_browser():
        pyautogui.press('j')
        return ctx.reply("Перематываю назад")
    return ctx.reply("Браузер с YouTube не найден")


def handle_youtube_volume_up(cmd, ctx):
    if _focus_browser():
        pyautogui.press('up')
        return ctx.reply("Громче")
    return ctx.reply("Браузер с YouTube не найден")


def handle_youtube_volume_down(cmd, ctx):
    if _focus_browser():
        pyautogui.press('down')
        return ctx.reply("Тише")
    return ctx.reply("Браузер с YouTube не найден")


def handle_open_channel(cmd, ctx):
    text = cmd.text_lower
    channel = (
        text.replace("открой канал", "")
            .replace("перейди на канал", "")
            .replace("канал", "")
            .strip()
    )

    url = f"https://www.youtube.com/results?search_query={channel.replace(' ', '+')}+канал"
    webbrowser.open(url)
    return ctx.reply(f"Ищу канал {channel} на YouTube")


def handle_youtube_search(cmd, ctx):
    text = cmd.text_lower
    query = (
        text.replace("найди на ютубе", "")
            .replace("найди видео", "")
            .replace("поищи на ютубе", "")
            .replace("ютуб найди", "")
            .strip()
    )

    if not query:
        return ctx.reply("Что искать на YouTube?")

    url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
    webbrowser.open(url)
    return ctx.reply(f"Ищу на YouTube: {query}")