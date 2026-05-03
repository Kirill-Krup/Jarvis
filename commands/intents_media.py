import os
import subprocess
import time


def _is_youtube_in_browser() -> bool:
    result = subprocess.run(
        ['powershell', '-Command',
         '(Get-Process | Where-Object {$_.MainWindowTitle -match "YouTube"} '
         '| Select-Object -First 1).MainWindowTitle'],
        capture_output=True, text=True
    )
    return bool(result.stdout.strip())


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


def handle_media_pause(cmd, ctx):
    if _is_youtube_in_browser() and _focus_browser():
        import pyautogui
        pyautogui.press('k')
        return ctx.reply("Пауза")

    os.system(
        'powershell -command '
        '"(New-Object -ComObject WScript.Shell).SendKeys([char]179)"'
    )
    return ctx.reply("Пауза")


def handle_media_play(cmd, ctx):
    if _is_youtube_in_browser() and _focus_browser():
        import pyautogui
        pyautogui.press('k')
        return ctx.reply("Продолжаю воспроизведение")

    os.system(
        'powershell -command '
        '"(New-Object -ComObject WScript.Shell).SendKeys([char]179)"'
    )
    return ctx.reply("Продолжаю воспроизведение")


def handle_media_next(cmd, ctx):
    os.system(
        'powershell -command '
        '"(New-Object -ComObject WScript.Shell).SendKeys([char]176)"'
    )
    return ctx.reply("Следующий трек")


def handle_media_prev(cmd, ctx):
    os.system(
        'powershell -command '
        '"(New-Object -ComObject WScript.Shell).SendKeys([char]177)"'
    )
    return ctx.reply("Предыдущий трек")