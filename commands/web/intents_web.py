import webbrowser
import subprocess
import os
import re
import urllib.parse
import requests
from ddgs import DDGS

from config.setup_wizard import MUSIC_PLAYERS, MOVIE_SOURCES, ANIME_SOURCES, load_config


def open_browser_url(url: str):
    try:
        cmd = ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", f"Start-Process '{url}'"]
        subprocess.Popen(cmd, creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception:
        webbrowser.open(url)


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


def _get_config() -> dict:
    try:
        return load_config()
    except Exception:
        return {}


def _get_first_link(query: str, site: str = "") -> str:
    """Ищет запрос в DuckDuckGo (ddgs) и возвращает первую ссылку."""
    search_query = f"site:{site} {query}" if site else query
    try:
        results = list(DDGS().text(search_query, max_results=1))
        if results:
            return results[0]['href']
    except Exception as e:
        print(f"[DDGS] Ошибка поиска: {e}")
    return None


def _clean_query(text: str) -> str:
    """Тщательно очищает запрос, удаляя слова-паразиты и знаки препинания."""
    text = text.lower()
    stop_words = [
        "хочу посмотреть", "хочу глянуть", "давай посмотрим", "давай глянем",
        "посмотреть", "глянуть", "найди", "включи", "поищи", "покажи",
        "фильм", "сериал", "аниме", "анимэ", "аниму", "anime", "кино",
        "пожалуйста", "мне", "хочу", "они", "мое", "моё", "этот", "это"
    ]
    for w in stop_words:
        text = re.sub(rf'\b{w}\b', ' ', text)
    text = re.sub(r'[^\w\s]', '', text)
    return re.sub(r"\s+", " ", text).strip()


def _is_anime_query(text: str) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in ANIME_KEYWORDS)


def handle_anime_search(raw_query, ctx):
    """Поиск аниме согласно выбранному пользователем источнику."""
    cfg = _get_config()
    anime_src_key = cfg.get("anime_source", "AnimeGO")
    src_info = ANIME_SOURCES.get(anime_src_key, ANIME_SOURCES["AnimeGO"])
    src_name = src_info.get("name", "AnimeGO")

    query_str = getattr(raw_query, "text_lower", str(raw_query))
    clean = _clean_query(query_str)

    if not clean:
        catalog_url = src_info.get("catalog", "https://animego.org/anime")
        open_browser_url(catalog_url)
        return ctx.reply(f"Открываю каталог аниме на {src_name}")

    # 1. Прямой URL поиска сайта (если поддерживается)
    if "url" in src_info:
        url = f"{src_info['url']}{urllib.parse.quote_plus(clean)}"
        open_browser_url(url)
        return ctx.reply(f"Ищу аниме «{clean}» на {src_name}")

    # 2. Поисковый запрос через domain / search
    if "domain" in src_info:
        domain = src_info["domain"]
        first_link = _get_first_link(clean, domain)
        if first_link:
            open_browser_url(first_link)
            return ctx.reply(f"Открываю аниме «{clean}» на {src_name}")
        else:
            fallback = f"https://yandex.ru/search/?text={urllib.parse.quote_plus(f'site:{domain} {clean}')}"
            open_browser_url(fallback)
            return ctx.reply(f"Ищу аниме «{clean}» на {src_name}")

    if "search" in src_info:
        template = src_info["search"]
        url = template.format(q=urllib.parse.quote_plus(clean))
        open_browser_url(url)
        return ctx.reply(f"Ищу аниме «{clean}» в {src_name}")

    # Fallback на AnimeGO
    open_browser_url(f"https://animego.org/search/anime?q={urllib.parse.quote_plus(clean)}")
    return ctx.reply(f"Ищу аниме «{clean}» на AnimeGO")


def handle_movie_search(cmd, ctx):
    """Поиск фильмов согласно выбранному пользователем источнику."""
    text = getattr(cmd, "text_lower", str(cmd).lower())

    if _is_anime_query(text):
        return handle_anime_search(text, ctx)

    cfg = _get_config()
    movie_src_key = cfg.get("movie_source", "KinoGo")
    src_info = MOVIE_SOURCES.get(movie_src_key, MOVIE_SOURCES["KinoGo"])
    src_name = src_info.get("name", "KinoGo")

    cleaned = _clean_query(text)
    if not cleaned:
        return ctx.reply("Какой фильм вы хотите посмотреть?")

    # 1. Прямой URL сайта (например, КиноПоиск)
    if "url" in src_info:
        url = f"{src_info['url']}{urllib.parse.quote_plus(cleaned)}"
        open_browser_url(url)
        return ctx.reply(f"Ищу фильм «{cleaned}» на {src_name}")

    # 2. Доменный поиск через DuckDuckGo (KinoGo, HDRezka, Ivi, Okko)
    if "domain" in src_info:
        domain = src_info["domain"]
        first_link = _get_first_link(cleaned, domain)
        if first_link:
            open_browser_url(first_link)
            return ctx.reply(f"Открываю фильм «{cleaned}» на {src_name}")
        else:
            fallback = f"https://yandex.ru/search/?text={urllib.parse.quote_plus(f'site:{domain} {cleaned}')}"
            open_browser_url(fallback)
            return ctx.reply(f"Ищу фильм «{cleaned}» на {src_name}")

    # 3. Шаблонный поиск (Яндекс онлайн)
    if "search" in src_info:
        url = src_info["search"].format(q=urllib.parse.quote_plus(cleaned))
        open_browser_url(url)
        return ctx.reply(f"Ищу фильм «{cleaned}» в {src_name}")

    # Fallback
    open_browser_url(f"https://yandex.ru/search/?text={urllib.parse.quote_plus(f'смотреть фильм {cleaned} онлайн')}")
    return ctx.reply(f"Ищу фильм «{cleaned}» в браузере")


def _get_music_url() -> tuple[str, str]:
    """Возвращает (url, имя сервиса) из конфига пользователя."""
    cfg = _get_config()
    player = cfg.get("music_player", "YouTube Music")
    url = MUSIC_PLAYERS.get(player, "https://music.youtube.com")
    return url, player


def handle_currency(cmd, ctx):
    text = cmd.text_lower
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

    if any(w in query for w in
           ("курс доллара", "курс валют", "курс евро", "сколько стоит доллар", "почем доллар", "доллар")):
        return handle_currency(cmd, ctx)

    if _is_anime_query(query):
        return handle_anime_search(query, ctx)

    if not query:
        return ctx.reply("Что именно найти?")

    search_url = f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}"
    open_browser_url(search_url)
    return ctx.reply(f"Ищу {query}")


def handle_info_search(cmd, ctx):
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


def handle_play_song(cmd, ctx):
    """Открывает поиск конкретной песни в выбранном сервисе."""
    text = getattr(cmd, "text_lower", str(cmd).lower())
    song_name = re.sub(r'\b(включи|поставь|вруби|хочу|послушать|песню|песня|трек|музыку|сыграй|композицию)\b', '', text)
    song_name = re.sub(r'[^\w\s]', '', song_name).strip()

    if not song_name:
        return ctx.reply("Какую песню включить?")

    base_url, player_name = _get_music_url()
    encoded_song = urllib.parse.quote_plus(song_name)

    if "youtube.com" in base_url or "music.youtube.com" in base_url:
        url = f"https://music.youtube.com/search?q={encoded_song}"
    elif "spotify.com" in base_url:
        url = f"https://open.spotify.com/search/{encoded_song}"
    elif "yandex.ru" in base_url:
        url = f"https://music.yandex.ru/search?text={encoded_song}"
    elif "vk.com" in base_url:
        url = f"https://vk.com/audio?q={encoded_song}"
    else:
        url = f"https://music.youtube.com/search?q={encoded_song}"

    open_browser_url(url)
    return ctx.reply(f"Включаю «{song_name}» в {player_name}")


def handle_weather(cmd, ctx):
    """Обработчик погоды с учетом выбранного в настройках города."""
    text = getattr(cmd, "text_lower", str(cmd).lower())
    cfg = _get_config()
    default_city = cfg.get("city", "Москва")

    # Ищем, упомянул ли пользователь конкретный город в фразе
    target_city = None
    city_match = re.search(r'\bв\s+([а-яё\-]+)', text)
    if city_match:
        cand = city_match.group(1).strip()
        if cand not in ("сети", "интернете", "гугле", "браузере", "неделю", "выходные"):
            target_city = cand.capitalize()

    final_city = target_city or default_city
    is_tomorrow = "завтра" in text

    # Проверяем, просит ли пользователь открыть/показать в браузере
    should_google = (
        any(w in text for w in ("покажи", "открой", "гугли", "загугли", "браузер", "неделю", "выходные", "прогноз"))
        or text.strip() in ("погода", "погоду")
    )

    if should_google:
        search_query = f"погода в {final_city}" + (" завтра" if is_tomorrow else " сегодня")
        url = f"https://www.google.com/search?q={urllib.parse.quote_plus(search_query)}"
        open_browser_url(url)
        day_label = "на завтра" if is_tomorrow else "на сегодня"
        return ctx.reply(f"Открываю прогноз погоды для города {final_city} {day_label}")

    # Иначе пользователь просто спросил голосом: "какая сейчас погода", "какая погода", "сколько градусов"
    # Отвечаем ТОЛЬКО голосом БЕЗ открытия браузера!
    try:
        encoded_city = urllib.parse.quote(final_city)
        endpoint = f"https://wttr.in/{encoded_city}?format=%C+%t&lang=ru"
        r = requests.get(endpoint, timeout=2.5, headers={"User-Agent": "curl"})
        if r.status_code == 200 and r.text.strip():
            weather_text = r.text.strip()
            day_label = "завтра" if is_tomorrow else "сейчас"
            return ctx.reply(f"В городе {final_city} {day_label} {weather_text}")
    except Exception:
        pass

    # Если API wttr.in временно недоступен
    day_label = "завтра" if is_tomorrow else "сейчас"
    return ctx.reply(f"Не удалось получить сводку погоды для города {final_city}. Скажите «покажи погоду», чтобы открыть её в браузере.")
