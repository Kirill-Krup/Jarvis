import os
import subprocess


def handle_sleep(cmd, ctx):
    return "SLEEP_MODE"


def handle_shutdown(cmd, ctx):
    text = cmd.text_lower
    if "завершить работу" in text:
        return "CONFIRM_SHUTDOWN_PC"
    return "SHUTDOWN"


def handle_restart_pc(cmd, ctx):
    os.system("shutdown /r /t 0")
    return ctx.reply("Перезагружаю компьютер")


def handle_lock_pc(cmd, ctx):
    os.system("rundll32.exe user32.dll,LockWorkStation")
    return ctx.reply("Блокирую компьютер")


def handle_task_manager(cmd, ctx):
    subprocess.Popen(["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", "Start-Process taskmgr.exe"], creationflags=subprocess.CREATE_NO_WINDOW)
    return ctx.reply("Открываю диспетчер задач")


def handle_explorer(cmd, ctx):
    subprocess.Popen(["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", "Start-Process explorer.exe -ArgumentList 'shell:MyComputerFolder'"], creationflags=subprocess.CREATE_NO_WINDOW)
    return ctx.reply("Открываю проводник")


def handle_windows_settings(cmd, ctx):
    subprocess.Popen(["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", "Start-Process ms-settings:"], creationflags=subprocess.CREATE_NO_WINDOW)
    return ctx.reply("Открываю настройки Windows")


def handle_control_panel(cmd, ctx):
    subprocess.Popen(["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", "Start-Process control.exe"], creationflags=subprocess.CREATE_NO_WINDOW)
    return ctx.reply("Открываю панель управления")
