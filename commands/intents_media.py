import os


def handle_media_pause(cmd, ctx):
    os.system(
        "powershell -command "
        "\"(New-Object -ComObject WScript.Shell).SendKeys([char]179)\""
    )
    return ctx.reply("Пауза")


def handle_media_play(cmd, ctx):
    os.system(
        "powershell -command "
        "\"(New-Object -ComObject WScript.Shell).SendKeys([char]179)\""
    )
    return ctx.reply("Продолжаю воспроизведение")


def handle_media_next(cmd, ctx):
    os.system(
        "powershell -command "
        "\"(New-Object -ComObject WScript.Shell).SendKeys([char]176)\""
    )
    return ctx.reply("Следующий трек")


def handle_media_prev(cmd, ctx):
    os.system(
        "powershell -command "
        "\"(New-Object -ComObject WScript.Shell).SendKeys([char]177)\""
    )
    return ctx.reply("Предыдущий трек")