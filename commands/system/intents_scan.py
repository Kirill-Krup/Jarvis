import subprocess
import os
import threading


def _run_scan(scan_args: list[str], label: str, ctx):
    mpcmdrun = r"C:\Program Files\Windows Defender\MpCmdRun.exe"

    if not os.path.exists(mpcmdrun):
        mpcmdrun = None

    def _scan():
        try:
            if mpcmdrun:
                cmd = [mpcmdrun] + scan_args
            else:
                scan_type = scan_args[1] if len(scan_args) > 1 else "QuickScan"
                cmd = ["powershell", "-Command",
                       f"Start-MpScan -ScanType {scan_type}"]

            print(f"[SCAN] Запуск: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
            print(f"[SCAN] Завершено. Код: {result.returncode}")
            print(f"[SCAN] {result.stdout}")
        except subprocess.TimeoutExpired:
            print("[SCAN] Сканирование прервано по таймауту (1 час)")
        except Exception as e:
            print(f"[SCAN] Ошибка: {e}")

    threading.Thread(target=_scan, daemon=True).start()


def handle_scan_quick(cmd, ctx):
    _run_scan(
        ["-Scan", "-ScanType", "1"],
        "Быстрое сканирование",
        ctx
    )
    return ctx.reply(
        "Запускаю быструю проверку на вирусы. "
        "Результат появится в Центре безопасности Windows"
    )


def handle_scan_full(cmd, ctx):
    _run_scan(
        ["-Scan", "-ScanType", "2"],  # 2 = FullScan
        "Полное сканирование",
        ctx
    )
    return ctx.reply(
        "Запускаю полную проверку на вирусы. "
        "Это займёт продолжительное время, не выключайте компьютер"
    )


def handle_scan_disk(cmd, ctx):
    text = cmd.text_lower

    drive_letter = _extract_drive_letter(text)

    if not drive_letter:
        return ctx.reply("Укажите букву диска, например: просканируй диск C")

    drive_path = f"{drive_letter}:\\"

    if not os.path.exists(drive_path):
        return ctx.reply(f"Диск {drive_letter} не найден")

    _run_scan(
        ["-Scan", "-ScanType", "3", "-File", drive_path],  # 3 = CustomScan
        f"Сканирование диска {drive_letter}",
        ctx
    )
    return ctx.reply(f"Сканирую диск {drive_letter} на вирусы")


def handle_scan_folder(cmd, ctx):
    text = cmd.text_lower

    FOLDER_MAP = {
        "загрузки":      os.path.expanduser("~/Downloads"),
        "загрузок":      os.path.expanduser("~/Downloads"),
        "документы":     os.path.expanduser("~/Documents"),
        "рабочий стол":  os.path.expanduser("~/Desktop"),
        "desktop":       os.path.expanduser("~/Desktop"),
        "temp":          os.environ.get("TEMP", "C:\\Temp"),
        "временные":     os.environ.get("TEMP", "C:\\Temp"),
    }

    folder_path = None
    folder_name = None

    for key, path in FOLDER_MAP.items():
        if key in text:
            folder_path = path
            folder_name = key
            break

    if not folder_path:
        return ctx.reply("Не понял какую папку проверить")

    if not os.path.exists(folder_path):
        return ctx.reply(f"Папка {folder_name} не найдена")

    _run_scan(
        ["-Scan", "-ScanType", "3", "-File", folder_path],
        f"Сканирование папки {folder_name}",
        ctx
    )
    return ctx.reply(f"Сканирую папку {folder_name} на вирусы")


def handle_scan_cancel(cmd, ctx):
    mpcmdrun = r"C:\Program Files\Windows Defender\MpCmdRun.exe"
    try:
        if os.path.exists(mpcmdrun):
            subprocess.Popen([mpcmdrun, "-RemoveDefinitions", "-All"],
                             creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            subprocess.run(
                ["powershell", "-Command", "Stop-MpScan"],
                capture_output=True
            )
        return ctx.reply("Сканирование остановлено")
    except Exception as e:
        print(f"[SCAN] Ошибка отмены: {e}")
        return ctx.reply("Не удалось остановить сканирование")


def _extract_drive_letter(text: str) -> str | None:
    import re
    match = re.search(r'диск\s+([a-zа-яё])', text, re.IGNORECASE)
    if match:
        letter = match.group(1).upper()
        RU_TO_EN = {
            'А': 'A', 'В': 'B', 'С': 'C', 'Д': 'D',
            'Е': 'E', 'Ф': 'F', 'Г': 'G', 'Н': 'H',
        }
        return RU_TO_EN.get(letter, letter)

    WORD_MAP = {
        "цэ": "C", "це": "C",
        "дэ": "D", "де": "D",
        "е":  "E", "эй": "E",
        "еф": "F", "эф": "F",
    }
    for word, letter in WORD_MAP.items():
        if f"диск {word}" in text:
            return letter

    return None