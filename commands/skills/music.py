"""Музыка: найти песню и сразу включить её (а не просто открыть поиск)."""
import random
import re
import urllib.parse

import requests

from commands.skills.registry import skill
from config.setup_wizard import MUSIC_PLAYERS
from core.browser import open_url

CATEGORY = "🎵 Музыка"

YOUTUBE_SEARCH = "https://www.youtube.com/results?search_query="
VIDEO_ID_RE = re.compile(r'"videoRenderer":\{"videoId":"([\w-]{11})"')
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
           "Accept-Language": "ru-RU,ru;q=0.9"}

# «включи музыку для работы» -> что искать
MOODS = {
    r"работ|концентрац|фокус|учёб|учеб|программир": "lofi hip hop radio focus",
    r"расслаб|спокойн|отдых|сон|засып": "relaxing chill music playlist",
    r"бодр|тренировк|спорт|зал": "workout motivation music mix",
    r"игр|геймер": "gaming music mix",
    r"рок": "рок хиты плейлист",
    r"рэп|реп|хип-?хоп": "русский рэп хиты плейлист",
    r"джаз": "jazz relaxing music",
    r"классик": "classical music playlist",
    r"электрон|техно|хаус": "electronic music mix",
    r"поп": "поп хиты плейлист",
    r"фонк": "phonk mix",
}
RANDOM_QUERIES = ["лучшие хиты mix", "популярная музыка плейлист", "indie music mix",
                  "русские хиты плейлист", "chill vibes playlist"]

_FILLER = re.compile(
    r"\b(?:включи|поставь|вруби|запусти|сыграй|хочу|послушать|послушаем|мне|пожалуйста|"
    r"песню|песня|песни|трек|композицию|музыку|музыка|исполнителя|группу|альбом|давай)\b")


def find_video_id(query: str) -> str | None:
    """Первое видео из результатов поиска YouTube (без API и ключей)."""
    try:
        r = requests.get(YOUTUBE_SEARCH + urllib.parse.quote_plus(query),
                         headers=HEADERS, timeout=6)
        m = VIDEO_ID_RE.search(r.text)
        return m.group(1) if m else None
    except Exception as e:
        print(f"[MUSIC] Поиск не удался: {e}")
        return None


def _service(profile) -> tuple[str, str]:
    name = profile.music_player
    return name, MUSIC_PLAYERS.get(name, "https://music.youtube.com")


def play_query(query: str, profile) -> tuple[bool, str]:
    """Открывает воспроизведение. Возвращает (играет ли сразу, название сервиса)."""
    name, base = _service(profile)
    encoded = urllib.parse.quote_plus(query)

    # YouTube / YouTube Music умеют включать трек по ссылке на видео
    if "youtube" in base:
        video_id = find_video_id(query + (" audio" if "music" in base else ""))
        if video_id:
            host = "music.youtube.com" if "music.youtube" in base else "www.youtube.com"
            open_url(f"https://{host}/watch?v={video_id}&autoplay=1")
            return True, name
        open_url(f"https://music.youtube.com/search?q={encoded}")
        return False, name

    # у остальных сервисов автозапуск без входа в аккаунт невозможен: открываем поиск
    search_urls = {
        "spotify": f"https://open.spotify.com/search/{encoded}",
        "yandex": f"https://music.yandex.ru/search?text={encoded}",
        "vk.com": f"https://vk.com/audio?q={encoded}",
        "soundcloud": f"https://soundcloud.com/search?q={encoded}",
        "deezer": f"https://www.deezer.com/search/{encoded}",
        "apple": f"https://music.apple.com/search?term={encoded}",
    }
    url = next((u for key, u in search_urls.items() if key in base), None)
    if url:
        open_url(url)
        return False, name
    # запасной путь: сыграем через YouTube
    video_id = find_video_id(query)
    open_url(f"https://www.youtube.com/watch?v={video_id}&autoplay=1" if video_id
             else f"{YOUTUBE_SEARCH}{encoded}")
    return bool(video_id), "YouTube"


@skill(CATEGORY, "Найти песню и сразу включить её",
       ["включи песню звери районы кварталы", "поставь трек numb",
        "включи группу кино", "хочу послушать queen"],
       [r"^(?:включи|поставь|вруби|запусти|сыграй)\s+(?:мне\s+)?(?:песню|песня|трек|композицию|группу|исполнителя|альбом)\s+\S",
        r"^(?:включи|поставь|вруби|запусти)\s+музыку\s+(?!для\b|в\b|на\b|погромче|потише)\S",
        r"^(?:хочу|давай)\s+послушать\s+\S"],
       exclusive=True)
def play_song(cmd, ctx):
    query = re.sub(r"\s+", " ", _FILLER.sub(" ", cmd.text_lower)).strip()
    if not query:
        return ctx.reply("Какую песню включить?")
    started, service = play_query(query, ctx.profile)
    if started:
        return ctx.reply(f"Включаю «{query}»")
    return ctx.reply(f"Открыл поиск «{query}» в {service}. Нажмите на нужный трек")


@skill(CATEGORY, "Включить музыку под настроение или жанр",
       ["включи музыку для работы", "поставь что-нибудь расслабляющее", "включи рок",
        "включи случайную музыку"],
       [r"^(?:включи|поставь|вруби)\s+музыку\s+для\b", r"^(?:включи|поставь|вруби)\s+(?:что[- ]нибудь|случайную музыку|какую[- ]нибудь музыку)",
        r"^(?:включи|поставь|вруби)\s+(?:рок|рэп|реп|хип-?хоп|джаз|классику|фонк|электронную музыку)\b"],
       exclusive=True)
def play_mood(cmd, ctx):
    text = cmd.text_lower
    query = next((q for pattern, q in MOODS.items() if re.search(pattern, text)), None)
    if not query:
        query = random.choice(RANDOM_QUERIES)
    started, service = play_query(query, ctx.profile)
    return ctx.reply("Включаю подборку" if started else f"Открыл подборку в {service}")
