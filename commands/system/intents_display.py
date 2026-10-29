import subprocess


def handle_display_extend(cmd, ctx):
    subprocess.Popen(["DisplaySwitch.exe", "/extend"])
    ctx.speaker.speak_extend_display()
    return ""


def handle_display_duplicate(cmd, ctx):
    subprocess.Popen(["DisplaySwitch.exe", "/clone"])
    ctx.speaker.speak_duplicate_display()
    return ""


def handle_display_primary(cmd, ctx):
    subprocess.Popen(["DisplaySwitch.exe", "/internal"])
    ctx.speaker.speak_first_display_active()
    return ""


def handle_display_second(cmd, ctx):
    subprocess.Popen(["DisplaySwitch.exe", "/external"])
    ctx.speaker.speak_second_display_active()
    return ""


def _parse_brightness(text: str) -> int | None:
    import re
    numbers = re.findall(r'\d+', text)
    if numbers:
        val = int(numbers[0])
        return max(0, min(100, val))  # clamp 0..100
    return None


def _set_brightness_all(level: int):
    script = (
        f"(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods)"
        f".WmiSetBrightness(1,{level})"
    )
    subprocess.run(
        ["powershell", "-Command", script],
        capture_output=True
    )


def _get_monitors() -> list[str]:
    result = subprocess.run(
        ["powershell", "-Command",
         "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorID | "
         "ForEach-Object { "
         "    ($_.UserFriendlyName | ForEach-Object {[char]$_}) -join '' "
         "})"],
        capture_output=True, text=True
    )
    monitors = [m.strip() for m in result.stdout.strip().splitlines() if m.strip()]
    return monitors


def handle_brightness_set(cmd, ctx):
    level = _parse_brightness(cmd.text_lower)
    if level is None:
        return ctx.reply("Укажите уровень яркости от 0 до 100")

    _set_brightness_all(level)
    return ctx.reply(f"Устанавливаю яркость {level} процентов")


def handle_brightness_up(cmd, ctx):
    current = _get_current_brightness()
    new_level = min(100, current + 20)
    _set_brightness_all(new_level)
    return ctx.reply(f"Яркость {new_level} процентов")


def handle_brightness_down(cmd, ctx):
    current = _get_current_brightness()
    new_level = max(0, current - 20)
    _set_brightness_all(new_level)
    return ctx.reply(f"Яркость {new_level} процентов")


def _get_current_brightness() -> int:
    result = subprocess.run(
        ["powershell", "-Command",
         "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightness).CurrentBrightness"],
        capture_output=True, text=True
    )
    try:
        return int(result.stdout.strip().splitlines()[0])
    except Exception:
        return 50  # fallback


def handle_brightness_monitor(cmd, ctx):
    text = cmd.text_lower
    level = _parse_brightness(text)
    if level is None:
        return ctx.reply("Укажите уровень яркости от 0 до 100")

    monitor_idx = 0
    if "второго" in text or "второй" in text or "второму" in text:
        monitor_idx = 1
    elif "третьего" in text or "третий" in text:
        monitor_idx = 2

    try:
        from monitorcontrol import get_monitors
        monitors = list(get_monitors())
        if monitor_idx >= len(monitors):
            return ctx.reply(f"Монитор {monitor_idx + 1} не найден")

        with monitors[monitor_idx] as m:
            m.set_luminance(level)

        names = ["первого", "второго", "третьего"]
        name = names[monitor_idx] if monitor_idx < len(names) else str(monitor_idx + 1)
        return ctx.reply(f"Яркость {name} монитора {level} процентов")

    except ImportError:
        _set_brightness_all(level)
        return ctx.reply(f"Устанавливаю яркость {level} процентов")
    except Exception as e:
        return ctx.reply(f"Не удалось изменить яркость монитора")


def handle_display_info(cmd, ctx):
    monitors = _get_monitors()
    if not monitors:
        return ctx.reply("Не удалось получить информацию о мониторах")
    count = len(monitors)
    names = ", ".join(monitors) if monitors else "неизвестно"
    return ctx.reply(f"Подключено мониторов: {count}. {names}")