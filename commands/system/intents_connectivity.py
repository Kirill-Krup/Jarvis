"""Управление Bluetooth, WiFi и другими системными переключателями."""
import subprocess
import os


def _run_ps(command: str) -> bool:
    """Выполняет PowerShell-команду скрытно."""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", command],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return result.returncode == 0
    except Exception as e:
        print(f"[Connectivity] Ошибка PowerShell: {e}")
        return False


def handle_bluetooth_on(cmd, ctx):
    """Включает Bluetooth."""
    # Через PowerShell: включаем радио Bluetooth
    ps_cmd = (
        "Add-Type -AssemblyName System.Runtime.WindowsRuntime; "
        "[Windows.Devices.Radios.Radio,Windows.System.Devices,ContentType=WindowsRuntime] | Out-Null; "
        "$radios = [Windows.Devices.Radios.Radio]::GetRadiosAsync().GetAwaiter().GetResult(); "
        "$bt = $radios | Where-Object { $_.Kind -eq 'Bluetooth' }; "
        "if ($bt) { $bt.SetStateAsync('On').GetAwaiter().GetResult() | Out-Null }"
    )
    if _run_ps(ps_cmd):
        return ctx.reply("Блютуз включён")

    # Fallback: через ms-settings
    subprocess.Popen(
        ["powershell", "-NoProfile", "-WindowStyle", "Hidden",
         "-Command", "Start-Process ms-settings:bluetooth"],
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    return ctx.reply("Открываю настройки Bluetooth")


def handle_bluetooth_off(cmd, ctx):
    """Выключает Bluetooth."""
    ps_cmd = (
        "Add-Type -AssemblyName System.Runtime.WindowsRuntime; "
        "[Windows.Devices.Radios.Radio,Windows.System.Devices,ContentType=WindowsRuntime] | Out-Null; "
        "$radios = [Windows.Devices.Radios.Radio]::GetRadiosAsync().GetAwaiter().GetResult(); "
        "$bt = $radios | Where-Object { $_.Kind -eq 'Bluetooth' }; "
        "if ($bt) { $bt.SetStateAsync('Off').GetAwaiter().GetResult() | Out-Null }"
    )
    if _run_ps(ps_cmd):
        return ctx.reply("Блютуз выключен")

    subprocess.Popen(
        ["powershell", "-NoProfile", "-WindowStyle", "Hidden",
         "-Command", "Start-Process ms-settings:bluetooth"],
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    return ctx.reply("Открываю настройки Bluetooth")


def handle_wifi_on(cmd, ctx):
    """Включает WiFi."""
    success = _run_ps("netsh interface set interface name='Wi-Fi' admin=enable")
    if success:
        return ctx.reply("Вай фай включён")

    subprocess.Popen(
        ["powershell", "-NoProfile", "-WindowStyle", "Hidden",
         "-Command", "Start-Process ms-settings:network-wifi"],
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    return ctx.reply("Открываю настройки WiFi")


def handle_wifi_off(cmd, ctx):
    """Выключает WiFi."""
    success = _run_ps("netsh interface set interface name='Wi-Fi' admin=disable")
    if success:
        return ctx.reply("Вай фай выключен")

    subprocess.Popen(
        ["powershell", "-NoProfile", "-WindowStyle", "Hidden",
         "-Command", "Start-Process ms-settings:network-wifi"],
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    return ctx.reply("Открываю настройки WiFi")


def handle_hotspot_on(cmd, ctx):
    """Включает мобильную точку доступа."""
    subprocess.Popen(
        ["powershell", "-NoProfile", "-WindowStyle", "Hidden",
         "-Command", "Start-Process ms-settings:network-mobilehotspot"],
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    return ctx.reply("Открываю настройки точки доступа")


def handle_airplane_on(cmd, ctx):
    """Включает режим в самолёте."""
    subprocess.Popen(
        ["powershell", "-NoProfile", "-WindowStyle", "Hidden",
         "-Command", "Start-Process ms-settings:network-airplanemode"],
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    return ctx.reply("Открываю настройки режима в самолёте")
