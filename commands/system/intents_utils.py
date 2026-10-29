import os
import subprocess
import datetime


def handle_time(cmd, ctx):
    now = datetime.datetime.now().strftime("%H:%M")
    return ctx.reply(f"Сейчас {now}")


def handle_date(cmd, ctx):
    today = datetime.datetime.now().strftime("%d.%m.%Y")
    return ctx.reply(f"Сегодня {today}")


def handle_calc(cmd, ctx):
    subprocess.Popen("calc")
    return ctx.reply("Открываю калькулятор")


def handle_screenshot(cmd, ctx):
    screenshot_dir = os.path.join(os.path.expanduser("~"), "Pictures", "Screenshots")
    os.makedirs(screenshot_dir, exist_ok=True)
    filename = os.path.join(
        screenshot_dir,
        f"screenshot_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    )
    ps = (
        "powershell -command \""
        "Add-Type -AssemblyName System.Windows.Forms; "
        "Add-Type -AssemblyName System.Drawing; "
        "$bmp = New-Object System.Drawing.Bitmap([System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Width,"
        "[System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Height); "
        "$graphics = [System.Drawing.Graphics]::FromImage($bmp); "
        "$graphics.CopyFromScreen(0,0,0,0,$bmp.Size); "
        f"$bmp.Save('{filename}');\""
    )
    os.system(ps)
    return ctx.reply("Скриншот сохранён")


def handle_downloads(cmd, ctx):
    path = os.path.join(os.path.expanduser("~"), "Downloads")
    if os.path.exists(path):
        os.startfile(path)
        return ctx.reply("Открываю загрузки")
    return ctx.reply("Папка загрузок не найдена")


def handle_documents(cmd, ctx):
    path = os.path.join(os.path.expanduser("~"), "Documents")
    if os.path.exists(path):
        os.startfile(path)
        return ctx.reply("Открываю документы")
    return ctx.reply("Папка документов не найдена")


def handle_desktop(cmd, ctx):
    path = os.path.join(os.path.expanduser("~"), "Desktop")
    if os.path.exists(path):
        os.startfile(path)
        return ctx.reply("Открываю рабочий стол")
    return ctx.reply("Рабочий стол не найден")


def handle_disk_d(cmd, ctx):
    if os.path.exists("D:\\"):
        os.startfile("D:\\")
        return ctx.reply("Открываю диск D")
    return ctx.reply("Диск D не найден")


def handle_disk_e(cmd, ctx):
    if os.path.exists("E:\\"):
        os.startfile("E:\\")
        return ctx.reply("Открываю диск E")
    return ctx.reply("Диск E не найден")