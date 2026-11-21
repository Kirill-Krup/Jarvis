"""Навыки системных инструментов: проверка пинга, IP, очистка корзины, генерация паролей."""
import ctypes
import os
import random
import secrets
import socket
import string
import subprocess
import time

import pyperclip

from commands.skills.registry import skill

CATEGORY = "🛠 Инструменты и сеть"


@skill(CATEGORY, "Проверить интернет и измерить пинг",
       ["проверь интернет", "проверь пинг", "есть ли интернет", "какой пинг"],
       [r"^(?:проверь|измерь|какой|есть\s+ли)\s+(?:интернет|пинг|сеть|связь)\b",
        r"^провер(?:ь|ить)\s+подключение\s+к\s+интернету"],
       exclusive=True)
def check_ping(cmd, ctx):
    t0 = time.time()
    try:
        s = socket.create_connection(("1.1.1.1", 53), timeout=2.0)
        s.close()
        ms = max(1, round((time.time() - t0) * 1000))
        return ctx.reply(f"Интернет работает стабильно. Пинг {ms} миллисекунд")
    except Exception:
        return ctx.reply("Подключение к интернету отсутствует или заблокировано")


@skill(CATEGORY, "Узнать свой локальный IP-адрес",
       ["какой мой ip", "мой ip", "узнай мой ip адрес", "мой локальный ip"],
       [r"^(?:какой\s+)?мой\s+(?:ip|айпи|ай\s+пи)(?:\s+адрес)?\b", r"^узнай\s+(?:мой\s+)?ip\b"],
       exclusive=True)
def get_ip(cmd, ctx):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ctx.reply(f"Ваш локальный ай пи адрес: {ip}")


@skill(CATEGORY, "Очистить корзину Windows",
       ["очисти корзину", "очистить корзину", "опустоши корзину"],
       [r"^(?:очисти|очистить|опустоши|опустошить|сбрось)\s+корзину\b"],
       exclusive=True)
def empty_recycle_bin(cmd, ctx):
    try:
        # 7 = SHERB_NOCONFIRMATION (1) | SHERB_NOPROGRESSUI (2) | SHERB_NOSOUND (4)
        res = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 7)
        return ctx.reply("Корзина успешно очищена")
    except Exception as e:
        return ctx.reply("Не удалось очистить корзину")


@skill(CATEGORY, "Сгенерировать надёжный пароль и скопировать его в буфер обмена",
       ["сгенерируй пароль", "придумай пароль", "создай надёжный пароль", "новый пароль"],
       [r"^(?:сгенерируй|придумай|создай|новый)\s+(?:мне\s+)?(?:надёжный\s+|надежный\s+)?пароль\b"],
       exclusive=True)
def generate_password(cmd, ctx):
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    # Гарантируем наличие хотя бы одной заглавной, строчной буквы, цифры и символа
    pwd = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
        secrets.choice("!@#$%^&*"),
    ]
    pwd += [secrets.choice(alphabet) for _ in range(10)]
    random.shuffle(pwd)
    result = "".join(pwd)

    try:
        pyperclip.copy(result)
        return ctx.reply("Сгенерировал надёжный пароль из 14 символов и скопировал его в буфер обмена")
    except Exception:
        return ctx.reply("Пароль сгенерирован")


@skill(CATEGORY, "Открыть командную строку или PowerShell",
       ["открой терминал", "открой командную строку", "открой cmd", "открой powershell"],
       [r"^(?:открой|запусти)\s+(?:терминал|командную\s+строку|cmd|powershell|павершелл)\b"],
       exclusive=True)
def open_terminal(cmd, ctx):
    target = "powershell" if "powershell" in cmd.text_lower or "павершелл" in cmd.text_lower else "cmd"
    subprocess.Popen(f"start {target}", shell=True)
    return ctx.reply("Открываю командную строку")


@skill(CATEGORY, "Открыть Блокнот",
       ["открой блокнот", "запусти блокнот"],
       [r"^(?:открой|запусти)\s+блокнот\b"],
       exclusive=True)
def open_notepad(cmd, ctx):
    subprocess.Popen("notepad")
    return ctx.reply("Открываю блокнот")

@skill(CATEGORY, "Прочитать содержимое буфера обмена",
       ["прочитай буфер обмена", "что в буфере", "озвучь буфер"],
       [r"^(?:прочитай|озвучь|что\s+в)\s+(?:буфер|буфере|буфер\s+обмена|буфере\s+обмена)\b",
        r"^буфер\s+обмена\b"],
       exclusive=True)
def read_clipboard(cmd, ctx):
    try:
        content = pyperclip.paste().strip()
        if not content:
            return ctx.reply("Буфер обмена пуст")
        if len(content) > 180:
            content = content[:180] + " и так далее"
        return ctx.reply(f"В буфере обмена находится: {content}")
    except Exception:
        return ctx.reply("Не удалось прочитать буфер обмена")


@skill(CATEGORY, "Очистить буфер обмена",
       ["очисти буфер обмена", "очистить буфер", "сотри буфер"],
       [r"^(?:очисти|очистить|сотри|опустоши)\s+буфер(?:\s+обмена)?\b"],
       exclusive=True)
def clear_clipboard(cmd, ctx):
    try:
        pyperclip.copy("")
        return ctx.reply("Буфер обмена успешно очищен")
    except Exception:
        return ctx.reply("Не удалось очистить буфер обмена")

