"""Уведомления: всплывающее окно Windows и/или сообщение в Telegram.

Канал выбирается в настройках («Куда присылать напоминания»):
  pc        — уведомление на компьютере
  telegram  — сообщение от вашего Telegram-бота
  both      — и там, и там
"""
import base64
import subprocess
import threading

import requests

from config.profile_manager import ProfileManager

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"


def _ps_escape(text: str) -> str:
    return text.replace("'", "''")


def notify_pc(title: str, message: str) -> bool:
    """Системное уведомление Windows (значок в трее на пару секунд)."""
    script = (
        "Add-Type -AssemblyName System.Windows.Forms;"
        "Add-Type -AssemblyName System.Drawing;"
        "$n = New-Object System.Windows.Forms.NotifyIcon;"
        "$n.Icon = [System.Drawing.SystemIcons]::Information;"
        "$n.Visible = $true;"
        f"$n.ShowBalloonTip(10000, '{_ps_escape(title)}', '{_ps_escape(message)}', "
        "[System.Windows.Forms.ToolTipIcon]::Info);"
        "Start-Sleep -Seconds 11; $n.Dispose()"
    )
    encoded = base64.b64encode(script.encode("utf-16-le")).decode()
    try:
        subprocess.Popen(
            ["powershell", "-NoProfile", "-WindowStyle", "Hidden",
             "-EncodedCommand", encoded],
            creationflags=subprocess.CREATE_NO_WINDOW)
        return True
    except OSError as e:
        print(f"[NOTIFY] Не удалось показать уведомление: {e}")
        return False


def notify_telegram(message: str, token: str = "", chat_id: str = "") -> tuple[bool, str]:
    """Отправляет сообщение через бота. Возвращает (успех, описание ошибки)."""
    profile = ProfileManager()
    token = token or profile.telegram_token
    chat_id = chat_id or profile.telegram_chat_id
    if not token or not chat_id:
        return False, "Не заданы токен бота или chat_id"
    try:
        r = requests.post(
            TELEGRAM_API.format(token=token, method="sendMessage"),
            json={"chat_id": chat_id, "text": message}, timeout=10)
        if r.ok:
            return True, ""
        return False, r.json().get("description", f"HTTP {r.status_code}")
    except Exception as e:
        return False, str(e)


def detect_chat_id(token: str) -> tuple[str, str]:
    """Находит chat_id по последнему сообщению, отправленному боту.
    Возвращает (chat_id, ошибка)."""
    try:
        r = requests.get(
            TELEGRAM_API.format(token=token, method="getUpdates"), timeout=10)
        data = r.json()
        if not data.get("ok"):
            return "", data.get("description", "неверный токен")
        for update in reversed(data.get("result", [])):
            message = update.get("message") or update.get("channel_post")
            if message:
                return str(message["chat"]["id"]), ""
        return "", "Сначала отправьте боту любое сообщение в Telegram"
    except Exception as e:
        return "", str(e)


def notify(title: str, message: str, channel: str | None = None) -> None:
    """Отправляет уведомление в выбранный в настройках канал (в фоне)."""
    channel = channel or ProfileManager().notify_channel

    def _send():
        if channel in ("pc", "both"):
            notify_pc(title, message)
        if channel in ("telegram", "both"):
            ok, err = notify_telegram(f"{title}\n{message}")
            if not ok:
                print(f"[NOTIFY] Telegram: {err}")

    threading.Thread(target=_send, daemon=True).start()
