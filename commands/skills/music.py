"""Музыка: найти песню и сразу включить её, либо запустить плейлист под настроение/сезон/вайб."""
import random
import re
import urllib.parse

import requests

from commands.skills.registry import skill
from commands.skills.vibe_matcher import parse_vibe
from config.setup_wizard import MUSIC_PLAYERS
from core.browser import open_url

CATEGORY = "🎵 Музыка"

YOUTUBE_SEARCH = "https://www.youtube.com/results?search_query="
VIDEO_ID_RE = re.compile(r'"videoRenderer":\{"videoId":"([\w-]{11})"')
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
           "Accept-Language": "ru-RU,ru;q=0.9"}

# Базовые темы (используются как резерв, если запрос не составной)
MOODS = [
    # Времена года
    (r"осен|осень|осенн", "осенний уютный плейлист cozy autumn chill", "осенний плейлист"),
    (r"зим|зиму|зима|зимн|новогодн|новый\s+год|рождеств", "новогодняя зимняя музыка уютный зимний плейлист", "зимнюю подборку"),
    (r"весна|весну|весенн", "весенний плейлист весеннее настроение spring vibes", "весенний плейлист"),
    (r"лето|лету|летн", "летний плейлист летние хиты summer vibes music", "летний плейлист"),

    # Погода и атмосфера
    (r"дожд|ливень|гроза|пасмурн", "музыка под дождь cozy rainy day chill lofi", "музыку под дождь"),
    (r"вечер|закат|сумерк", "уютная вечерняя музыка evening chill acoustic", "вечернюю подборку"),
    (r"ноч|ночь|ночн|дорог|поездк|в пути|за рул", "night drive chill phonk synthwave атмосферная музыка", "музыку для ночной дороги"),
    (r"утр|кофе|рассвет|пробужден|проснут", "утренняя музыка для хорошего настроения coffee jazz morning chill", "утренний плейлист"),
    (r"уют|камин|плед|тепло", "уютная акустическая музыка cozy fireplace acoustic vibes", "уютную подборку"),

    # Состояния и дела
    (r"работ|концентрац|фокус|учёб|учеб|программир|кодинг", "lofi hip hop radio focus study beats", "музыку для концентрации"),
    (r"расслаб|спокойн|отдых|релакс|чилл", "relaxing chill ambient music playlist", "расслабляющую музыку"),
    (r"сон|засып|уснуть|колыбельн", "deep sleep music relaxing ambient", "музыку для сна"),
    (r"спорт|тренировк|зал|качалк|бодр|энерги|мотивац", "workout motivation music mix", "энергичную музыку для тренировки"),
    (r"игр|геймер|стрим", "gaming music mix synthwave electronic", "музыку для игр"),
    (r"груст|меланхол|поплакат|тоск|печал", "грустная атмосферная музыка sad songs playlist", "грустную подборку"),
    (r"романтик|свидан|люб|любов|для двоих", "romantic love songs acoustic chill playlist", "романтическую музыку"),
    (r"вечеринк|тусовк|дискотек|пати|танц|клуб", "party dance hits club remix playlist", "музыку для вечеринки"),
    (r"медитац|йог|дзен|спа", "meditation ambient music healing sounds", "музыку для медитации"),

    # Жанры
    (r"киберпанк", "cyberpunk dark synthwave", "киберпанк"),
    (r"фонк|дрифт", "phonk mix drift aggressive", "фонк"),
    (r"\bрок\b|\bрока\b|\bроку\b|метал|\bпанк\b|альтернатив", "рок хиты плейлист лучшие рок песни", "рок"),
    (r"рэп|реп|хип-?хоп", "русский рэп хиты плейлист", "рэп"),
    (r"джаз|блюз", "jazz blues relaxing cafe playlist", "джаз"),
    (r"классик", "classical music playlist mozart vivaldi", "классическую музыку"),
    (r"электрон|техно|хаус|edm|edmr", "electronic techno house music mix", "электронную музыку"),
    (r"поп|популярн|чарт", "топ поп хиты плейлист", "популярную музыку"),
    (r"инди", "indie aesthetic music chill playlist", "инди-музыку"),
    (r"ретро|диско|синтвейв|80-|90-|восьмидесят|девяност", "retro synthwave 80s hits playlist", "ретро-подборку"),
]

RANDOM_QUERIES = [
    "лучшие хиты mix", "популярная музыка плейлист", "indie music mix",
    "русские хиты плейлист", "chill vibes playlist"
]

_FILLER = re.compile(
    r"\b(?:включи|поставь|вруби|запусти|сыграй|хочу|послушать|послушаем|мне|пожалуйста|"
    r"песню|песня|песни|трек|композицию|музыку|музыка|исполнителя|группу|альбом|давай)\b")


def find_video_id(query: str) -> str | None:
    """Первое видео из результатов поиска YouTube (без API и ключей)."""
    try:
        r = requests.get(YOUTUBE_SEARCH + urllib.parse.quote_plus(query),
                         headers=HEADERS, timeout=2.5)
        m = VIDEO_ID_RE.search(r.text)
        if m:
            return m.group(1)
        alt_m = re.search(r'/watch\?v=([\w-]{11})', r.text)
        if alt_m:
            return alt_m.group(1)
    except Exception as e:
        print(f"[MUSIC] Быстрый поиск YouTube не удался: {e}")
    return None


def _service(profile) -> tuple[str, str]:
    name = profile.music_player
    return name, MUSIC_PLAYERS.get(name, "https://music.youtube.com")


def play_query(query: str, profile) -> tuple[bool, str]:
    """Открывает воспроизведение. Возвращает (играет ли сразу, название сервиса)."""
    name, base = _service(profile)
    encoded = urllib.parse.quote_plus(query)

    # 1. Если настроен специфичный плеер кроме YouTube Music
    search_urls = {
        "spotify": f"https://open.spotify.com/search/{encoded}",
        "yandex": f"https://music.yandex.ru/search?text={encoded}",
        "vk.com": f"https://vk.com/audio?q={encoded}",
        "soundcloud": f"https://soundcloud.com/search?q={encoded}",
        "deezer": f"https://www.deezer.com/search/{encoded}",
        "apple": f"https://music.apple.com/search?term={encoded}",
    }
    custom_url = next((u for key, u in search_urls.items() if key in base.lower()), None)
    if custom_url:
        open_url(custom_url)
        return False, name

    # 2. YouTube / YouTube Music: пытаемся сразу включить трек
    video_id = find_video_id(query + (" audio" if "music" in base.lower() else ""))
    if video_id:
        open_url(f"https://www.youtube.com/watch?v={video_id}&autoplay=1")
        return True, "YouTube"

    # 3. Резервный поиск, если прямой ID не получен за 2.5 сек (не зависаем)
    open_url(f"{YOUTUBE_SEARCH}{encoded}")
    return False, "YouTube"


@skill(CATEGORY, "Включить музыку под сезон, настроение, вайб или жанр",
       ["включи музыку под осень", "включи музыку под зиму", "поставь осенний плейлист",
        "хочу что-то под вайб лета но при этом спокойное", "музыка под дождь",
        "включи музыку под вайб ночного города", "хочу спокойный джаз под чашечку кофе",
        "включи грустный рок под дождь", "поставь бодрый фонк для тренировки",
        "включи музыку для работы", "поставь что-нибудь расслабляющее",
        "включи музыку в дорогу", "включи рок", "включи случайную музыку"],
       [r"^(?:включи|поставь|вруби|запусти|сыграй)\s+музыку\s+(?:под|для|на|в|про)\b",
        r"^(?:хочу|поставь|включи|вруби|найди|сыграй)\s+(?:что[- ]то|что[- ]нибудь)\s+(?:под|с|для|в|про|на)\b",
        r"\b(?:вайб|вайбом|вайба|вайбе|атмосферу|атмосферой|атмосфера)\b",
        r"^(?:включи|поставь|вруби|запусти|сыграй)\s+(?:осенн\w*|зимн\w*|новогодн\w*|весенн\w*|летн\w*|вечерн\w*|утренн\w*|грустн\w*|романтич\w*|расслабляющ\w*|спокойн\w*|бодр\w*|электронн\w*|атмосферн\w*|уютн\w*)\s+(?:музыку|плейлист|подборку|треки|песни)\b",
        r"^(?:включи|поставь|вруби|запусти)\s+(?:осенний|зимний|новогодний|весенний|летний|вечерний|утренний|грустный|романтический|расслабляющий|уютный)\s+плейлист\b",
        r"^(?:включи|поставь|вруби|запусти)\s+(?:что[- ]нибудь|случайную музыку|какую[- ]нибудь музыку)",
        r"^(?:музыка|плейлист|подборка)\s+(?:под|для|на)\s+\S",
        r"^(?:хочу|включи|поставь|вруби)\s+(?:спокойный|бодрый|грустный|уютный|романтический|тёмный|темный)\s+(?:джаз|рок|фонк|рэп|реп|блюз|синтвейв|лоуфай|поп|инди)\b",
        r"^(?:включи|поставь|вруби|запусти)\s+(?:рок|рэп|реп|хип-?хоп|джаз|классику|фонк|электронную музыку|попсу|инди|ретро|блюз|киберпанк)\b"],
       exclusive=True)
def play_mood(cmd, ctx):
    text = cmd.text_lower

    # 1. Интеллектуальный разбор составного вайба и ключевых слов
    vibe_match = parse_vibe(text)
    if vibe_match:
        query, title = vibe_match
        msg = f"Включаю {title}"
    else:
        # 2. Резервный поиск по базовым темам
        found = next(((q, title) for pattern, q, title in MOODS if re.search(pattern, text)), None)
        if found:
            query, title = found
            msg = f"Включаю {title}"
        else:
            query = random.choice(RANDOM_QUERIES)
            msg = "Включаю случайную подборку"

    started, service = play_query(query, ctx.profile)
    return ctx.reply(msg if started else f"Открыл подборку в {service}")


@skill(CATEGORY, "Найти песню и сразу включить её",
       ["включи песню звери районы кварталы", "поставь трек numb",
        "включи группу кино", "хочу послушать queen", "включи песню", "поставь трек"],
       [r"^(?:включи|поставь|вруби|запусти|сыграй)\s+(?:мне\s+)?(?:песню|песня|трек|композицию|группу|исполнителя|альбом)\b(?:\s+.+)?$",
        r"^(?:включи|поставь|вруби|запусти)\s+музыку\s+(?!для\b|под\b|на\b|в\b|про\b|с\b|подборку\b|плейлист\b|погромче\b|потише\b)\S",
        r"^(?:хочу|давай)\s+послушать\s+\S",
        r"^(?:включи|поставь|вруби|сыграй)\s+.*?\s+(?:от|группы)\s+[а-яёa-z0-9]+"],
       exclusive=True)
def play_song(cmd, ctx):
    query = re.sub(r"\s+", " ", _FILLER.sub(" ", cmd.text_lower)).strip()
    if not query:
        if hasattr(ctx, "set_pending"):
            ctx.set_pending("play_song")
        return ctx.reply("Какую песню включить?")
    started, service = play_query(query, ctx.profile)
    if started:
        return ctx.reply(f"Включаю «{query}»")
    return ctx.reply(f"Открыл поиск «{query}» в {service}")
