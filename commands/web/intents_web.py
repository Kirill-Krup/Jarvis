import webbrowser
import subprocess
import os
import re
import urllib.parse
import requests
from ddgs import DDGS


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
    """Тщательно очищает запрос, удаляя слова-паразиты и мусорные символы."""
    text = text.lower()

    # Список слов, которые нужно удалить (целиком слова)
    stop_words = [
        "хочу посмотреть", "хочу глянуть", "давай посмотрим", "давай глянем",
        "посмотреть", "глянуть", "найди", "включи", "поищи", "покажи",
        "фильм", "сериал", "аниме", "анимэ", "аниму", "anime", "кино",
        "пожалуйста", "мне", "хочу", "они", "мое", "моё", "этот", "это"
    ]

    # Заменяем слова на пробел (используя границы слов \b)
    for w in stop_words:
        text = re.sub(rf'\b{w}\b', ' ', text)

    # Удаляем все знаки препинания и кавычки
    text = re.sub(r'[^\w\s]', '', text)

    # Убираем лишние пробелы
    return re.sub(r"\s+", " ", text).strip()


def _is_anime_query(text: str) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in ANIME_KEYWORDS)


def handle_anime_search(raw_query: str, ctx):
    clean = _clean_query(raw_query)

    if not clean:
        open_browser_url("https://ru.yummyani.me")
        return ctx.reply("Открываю каталог аниме на YummyAnime")

    url = _get_first_link(clean, "ru.yummyani.me")

    if url:
        open_browser_url(url)
        return ctx.reply(f"Открываю аниме «{clean}» на YummyAnime")
    else:
        fallback_url = f"https://yandex.ru/search/?text={urllib.parse.quote_plus(f'site:ru.yummyani.me {clean}')}"
        open_browser_url(fallback_url)
        return ctx.reply(f"Не удалось найти точную ссылку, открываю поиск по «{clean}»")


def handle_movie_search(cmd, ctx):
    text = cmd.text_lower

    if _is_anime_query(text):
        return handle_anime_search(text, ctx)

    cleaned = _clean_query(text)

    if not cleaned:
        return ctx.reply("Какой фильм искать?")

    url = _get_first_link(cleaned, "kinogo-film.fm")

    if url:
        open_browser_url(url)
        return ctx.reply(f"Открываю фильм «{cleaned}» на KinoGo")
    else:
        fallback_url = f"https://yandex.ru/search/?text={urllib.parse.quote_plus(f'site:kinogo-film.fm {cleaned}')}"
        open_browser_url(fallback_url)
        return ctx.reply(f"Открываю поиск фильма «{cleaned}»")


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
    url, player_name = _get_music_url()
    open_browser_url(url)
    return ctx.reply(f"Открываю {player_name}")


def handle_weather(cmd, ctx):
    text = cmd.text_lower
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

    if "завтра" in text:
        search = "погода завтра"
    elif query_parts:
        search = f"погода {query_parts[0]}"
    else:
        search = "погода сегодня"

    url = f"https://www.google.com/search?q={urllib.parse.quote_plus(search)}"
    open_browser_url(url)

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


def handle_play_song(cmd, ctx):
    """Открывает поиск конкретной песни в выбранном сервисе."""
    text = cmd.text_lower

    # Убираем слова команды, оставляя только название песни
    song_name = re.sub(r'\b(включи|поставь|вруби|хочу|послушать|песню|трек|музыку)\b', '', text)
    song_name = re.sub(r'[^\w\s]', '', song_name).strip()  # Убираем кавычки и знаки препинания

    if not song_name:
        return ctx.reply("Какую песню включить?")

    base_url, player_name = _get_music_url()
    encoded_song = urllib.parse.quote_plus(song_name)

    if "youtube.com" in base_url:
        url = f"https://music.youtube.com/search?q={encoded_song}"
    elif "spotify.com" in base_url:
        url = f"https://open.spotify.com/search/{encoded_song}"
    elif "yandex.ru" in base_url:
        url = f"https://music.yandex.ru/search?text={encoded_song}"
    elif "vk.com" in base_url:
        url = f"https://vk.com/audio?q={encoded_song}"
    else:
        url = base_url

    open_browser_url(url)
    return ctx.reply(f"Ищу «{song_name}» в {player_name}")