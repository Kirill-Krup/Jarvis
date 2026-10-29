import webbrowser
import subprocess

def open_browser_url(url: str):
    try:
        cmd = ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", f"Start-Process '{url}'"]
        subprocess.Popen(cmd, creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception:
        open_browser_url(url)

import requests


def handle_currency(cmd, ctx):
    """
    'курс доллара', 'какой курс доллара', 'сколько стоит доллар', 'курс евро', 'курс валют'
    """
    text = cmd.text_lower

    # Открываем актуальную страницу с котировками в браузере
    open_browser_url("https://www.google.com/search?q=курс+доллара")

    usd_rub, eur_rub, usd_byn = None, None, None
    try:
        r = requests.get("https://www.cbr-xml-daily.ru/daily_json.js", timeout=1.5).json()
        usd_rub = r.get("Valute", {}).get("USD", {}).get("Value")
        eur_rub = r.get("Valute", {}).get("EUR", {}).get("Value")
    except Exception:
        pass

    try:
        r2 = requests.get("https://api.nbrb.by/exrates/rates/USD?parammode=2", timeout=1.5).json()
        usd_byn = r2.get("Cur_OfficialRate")
    except Exception:
        pass

    if "евро" in text and eur_rub:
        return ctx.reply(f"Курс евро сейчас {eur_rub:.2f} рублей")

    if usd_rub and usd_byn:
        return ctx.reply(f"Курс доллара: {usd_rub:.2f} российских рублей или {usd_byn:.2f} белорусских рублей")
    elif usd_rub:
        return ctx.reply(f"Курс доллара сейчас {usd_rub:.2f} рублей")
    elif usd_byn:
        return ctx.reply(f"Курс доллара сейчас {usd_byn:.2f} белорусских рублей")
    else:
        return ctx.reply("Открываю актуальный курс валют в браузере")


def handle_web(cmd, ctx):
    """
    'открой сайт ...', 'найди сайт ...', 'зайди на ...'
    """
    text = cmd.text_lower
    query = (
        text.replace("открой сайт", "")
            .replace("найди сайт", "")
            .replace("зайди на", "")
            .strip()
    )

    if not query:
        return ctx.reply("Какой сайт открыть?")

    return ctx.web_handler.open_site(query, ctx.profile.honorific)


def handle_search(cmd, ctx):
    """
    'загугли ...', 'прогугли ...', 'погугли ...', 'найди ...', 'поиск ...'
    """
    text = cmd.text_lower
    query = text

    for prefix in (
        "найди в интернете", "найди в гугле", "найди информацию про",
        "найди информацию о", "найди информацию", "прогугли мне", "загугли мне",
        "погугли мне", "прогугли", "загугли", "погугли", "поищи", "найди", "поиск"
    ):
        if query.startswith(prefix):
            query = query[len(prefix):].strip()
            break

    # Если запрос про курс валют
    if any(w in query for w in ("курс доллара", "курс валют", "курс евро", "сколько стоит доллар", "почем доллар", "доллар")):
        return handle_currency(cmd, ctx)

    if not query:
        return ctx.reply("Что именно найти?")

    search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
    open_browser_url(search_url)
    return ctx.reply(f"Ищу {query}")


def handle_info_search(cmd, ctx):
    """
    'найди информацию по запросу ...', 'найди информацию ...', 'хочу узнать ...'
    """
    text = cmd.text_lower
    query = (
        text.replace("найди информацию по запросу", "")
            .replace("найди информацию по", "")
            .replace("найди информацию", "")
            .replace("хочу узнать", "")
            .strip()
    )

    if not query:
        return ctx.reply("Какую информацию искать?")

    return handle_search(cmd, ctx)


def handle_youtube(cmd, ctx):
    open_browser_url("https://youtube.com")
    return ctx.reply("Открываю YouTube")


def handle_video_search(cmd, ctx):
    text = cmd.text_lower
    query = text.replace("найди видео", "").strip()
    if not query:
        return ctx.reply("Какое видео найти?")
    url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
    open_browser_url(url)
    return ctx.reply(f"Ищу видео {query}")


def handle_music(cmd, ctx):
    open_browser_url("https://music.youtube.com")
    return ctx.reply("Открываю музыку")


def handle_movie_search(cmd, ctx):
    text = cmd.text_lower
    cleaned = (
        text.replace("хочу посмотреть", "")
            .replace("давай посмотрим", "")
            .replace("посмотреть фильм", "")
            .replace("посмотреть сериал", "")
            .strip()
    )

    if not cleaned:
        return ctx.reply("Какой фильм или сериал вы хотите посмотреть?")

    query = cleaned.replace(" ", "+")
    url = f"https://www.kinopoisk.ru/index.php?kp_query={query}"
    open_browser_url(url)
    return ctx.reply(f"Ищу что посмотреть по запросу {cleaned}")
