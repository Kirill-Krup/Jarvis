import webbrowser
import subprocess
import os
import re
import urllib.parse
import requests


def open_browser_url(url: str):
    try:
        cmd = ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", f"Start-Process '{url}'"]
        subprocess.Popen(cmd, creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception:
        webbrowser.open(url)


# Маппинг музыкальных сервисов
MUSIC_PLAYER_URLS = {
    "YouTube Music": "https://music.youtube.com",
    "Spotify": "https://open.spotify.com",
    "Яндекс Музыка": "https://music.yandex.ru",
    "VK Музыка": "https://vk.com/audio",
    "SoundCloud": "https://soundcloud.com",
    "Apple Music": "https://music.apple.com",
    "Deezer": "https://www.deezer.com",
}

# Ключевые слова для определения аниме
ANIME_KEYWORDS = [
    "аниме", "анимэ", "аниму", "anime", "онгоинг", "тайтл",
    "восхождение в тени", "наруто", "ван пис", "атака титанов",
    "тетрадь смерти", "магическая битва", "клинок рассекающий демонов",
    "клинок", "блич", "хантер", "токийский гуль", "магическая академия",
    "ван панч мен", "ванпанчмен", "моб психо", "стальной алхимик",
    "ковбой бибоп", "евангелион", "сказка о хвосте феи",
    "мой герой академия", "геройская академия", "семья шпиона",
    "бездомный бог", "мастера меча онлайн", "синий экзорцист",
    "обещанный неверленд", "доктор стоун", "джоджо", "код гиас",
    "тёмный дворецкий", "чёрный клевер", "синий замок", "re zero",
    "ре зеро", "врата штейна", "человек бензопила", "берсерк",
    "соло левелинг", "поднятие уровня в одиночку", "хвост феи"
]


def _get_music_url() -> tuple[str, str]:
    """Возвращает (url, имя сервиса) из конфига пользователя."""
    try:
        config_path = "config/user_config.json"
        if os.path.exists(config_path):
            import json
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            player = config.get("music_player", "YouTube Music")
            url = MUSIC_PLAYER_URLS.get(player, "https://music.youtube.com")
            return url, player
    except Exception:
        pass
    return "https://music.youtube.com", "YouTube Music"


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

    # Если запрос про аниме ("найди аниме ...")
    if _is_anime_query(query):
        return handle_anime_search(query, ctx)

    if not query:
        return ctx.reply("Что именно найти?")

    search_url = f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}"
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
    url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(query)}"
    open_browser_url(url)
    return ctx.reply(f"Ищу видео {query}")


def handle_music(cmd, ctx):
    """Открывает музыкальный сервис, выбранный пользователем при настройке."""
    url, player_name = _get_music_url()
    open_browser_url(url)
    return ctx.reply(f"Открываю {player_name}")


def _is_anime_query(text: str) -> bool:
    """Определяет, относится ли запрос к просмотру аниме."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in ANIME_KEYWORDS)


def handle_anime_search(raw_query: str, ctx):
    """Специализированный поиск и открытие аниме на AnimeGO / Jut.su."""
    clean = raw_query.lower()
    # Удаляем служебные слова и кавычки
    for w in (
        "хочу посмотреть", "давай посмотрим", "посмотреть", "глянуть",
        "найди", "включи", "аниме", "анимэ", "аниму", "anime", "сериал", "мультик",
        '"', "'", "«", "»", "“", "”"
    ):
        clean = clean.replace(w, " ")
    clean = re.sub(r"\s+", " ", clean).strip()

    if not clean:
        open_browser_url("https://animego.org/anime")
        return ctx.reply("Открываю каталог аниме на АнимеГо")

    encoded = urllib.parse.quote_plus(clean)
    url = f"https://animego.org/search/anime?q={encoded}"
    open_browser_url(url)
    return ctx.reply(f"Ищу аниме «{clean}» на АнимеГо")


def handle_movie_search(cmd, ctx):
    """Поиск фильмов/сериалов/аниме."""
    text = cmd.text_lower

    # Если это аниме — сразу отправляем на специализированный аниме-сайт (AnimeGO)
    if _is_anime_query(text):
        return handle_anime_search(text, ctx)

    # Обычный фильм или сериал
    cleaned = text
    for prefix in (
        "хочу посмотреть фильм", "хочу посмотреть сериал", "хочу посмотреть",
        "давай посмотрим фильм", "давай посмотрим сериал", "давай посмотрим",
        "посмотреть фильм", "посмотреть сериал", "посмотреть",
        "хочу глянуть фильм", "хочу глянуть", "давай глянем",
        "найди фильм", "найди где посмотреть", "включи фильм",
    ):
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):].strip()
            break

    # Удаляем кавычки
    cleaned = cleaned.replace('"', "").replace("'", "").replace("«", "").replace("»", "").strip()

    if not cleaned:
        return ctx.reply("Какой фильм или сериал вы хотите посмотреть?")

    encoded = urllib.parse.quote_plus(cleaned)
    url = f"https://www.kinopoisk.ru/index.php?kp_query={encoded}"
    open_browser_url(url)
    return ctx.reply(f"Ищу что посмотреть по запросу {cleaned}")


def handle_weather(cmd, ctx):
    """Обработчик погоды: 'какая погода', 'какая завтра погода' и т.д."""
    text = cmd.text_lower

    # Извлекаем город или время
    query_parts = []
    for prefix in (
        "какая погода", "погода", "какая будет погода",
        "какая завтра погода", "какая сегодня погода",
        "скажи погоду", "покажи погоду",
    ):
        if prefix in text:
            remainder = text.replace(prefix, "").strip()
            if remainder:
                query_parts.append(remainder)
            break

    # Формируем поисковый запрос
    if "завтра" in text:
        search = "погода завтра"
    elif query_parts:
        search = f"погода {query_parts[0]}"
    else:
        search = "погода сегодня"

    url = f"https://www.google.com/search?q={urllib.parse.quote_plus(search)}"
    open_browser_url(url)

    # Пробуем получить погоду через API wttr.in
    try:
        r = requests.get(
            "https://wttr.in/?format=%C+%t&lang=ru",
            timeout=2,
            headers={"User-Agent": "curl"},
        )
        if r.status_code == 200:
            weather_text = r.text.strip()
            return ctx.reply(f"Сейчас {weather_text}. Подробнее в браузере")
    except Exception:
        pass

    return ctx.reply("Открываю прогноз погоды в браузере")
