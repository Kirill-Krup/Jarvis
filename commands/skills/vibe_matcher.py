"""Интеллектуальный разбор музыкальных запросов по атмосфере, вайбу, сезонам и жанрам.

Позволяет Джарвису понимать многосоставные запросы вроде:
- «хочу что-то под вайб лета, но при этом спокойное»
- «поставь что-нибудь под атмосферу осени, но бодрое»
- «включи музыку под вайб ночного города»
- «хочу спокойный джаз под чашечку кофе»
- «включи грустный рок под дождь»
- «поставь бодрый фонк для тренировки»
"""
import re

# 1. Настроение / Энергия / Темп: (паттерн, поисковые теги, женский род, мужской род)
MOODS_DATA = [
    (r"спокойн|чилл|расслабл|релакс|тихое|тихий|медленн|нежн|мягк|легк",
     ["chill", "relaxing", "calm"], "спокойную", "спокойный"),
    (r"бодр|энергичн|драйв|мощн|зажигательн|быстр|мотивац|качалк",
     ["energetic", "upbeat", "motivation"], "бодрую", "бодрый"),
    (r"грустн|меланхол|печальн|тоск|поплакат|депресс",
     ["sad", "melancholic", "nostalgic"], "грустную", "грустный"),
    (r"позитивн|весел|солнечн|радостн",
     ["happy", "positive", "sunny upbeat"], "позитивную", "позитивный"),
    (r"уютн|лампов|тепл|камин|плед",
     ["cozy", "warm acoustic"], "уютную", "уютный"),
    (r"романтич|люб|любов|свидан|для двоих",
     ["romantic", "love songs chill"], "романтическую", "романтический"),
    (r"мечтательн|космос|эмбиент|эфирн",
     ["dreamy", "space ambient"], "мечтательную", "мечтательный"),
    (r"темн|тёмн|мрачн|агрессивн|дрифт",
     ["dark", "aggressive drift"], "тёмную", "тёмный"),
]

# 2. Сезоны и времена года
SEASONS_DATA = [
    (r"лет|летн", ["summer vibes"], "летнюю", "летний"),
    (r"осен|осенн", ["autumn chill", "cozy autumn"], "осеннюю", "осенний"),
    (r"зим|зимн|новогод|новый\s+год|рождеств", ["winter cozy"], "зимнюю", "зимний"),
    (r"весен|весн", ["spring vibes"], "весеннюю", "весенний"),
]

# 3. Контекст, погода и окружение
CONTEXTS_DATA = [
    (r"дожд|ливень|гроз|пасмурн", ["rainy day", "cozy rain lofi"], "под дождь"),
    (r"вечер|закат|сумерк", ["evening sunset chill"], "на вечер"),
    (r"ночн\w*\s+город|город|неон", ["night city neon synthwave"], "под вайб ночного города"),
    (r"ноч|полноч|ночн", ["night drive", "late night"], "на ночь"),
    (r"утр|рассвет|кофе", ["morning coffee jazz"], "на утро"),
    (r"дорог|поездк|в пути|за рул|авто|трасс", ["road trip", "car drive"], "в дорогу"),
    (r"работ|учеб|кодинг|программир|фокус|концентрац", ["focus study lofi beats"], "для работы"),
    (r"тренировк|спорт|зал|качалк|бег|фитнес", ["workout gym motivation"], "для тренировки"),
    (r"сон|засып|уснуть|спать", ["deep sleep ambient"], "для сна"),
    (r"игр|геймер|стрим|катк", ["gaming mix synthwave"], "для игр"),
    (r"вечеринк|тусовк|танц|пати|клуб", ["party dance hits club"], "для вечеринки"),
    (r"медитац|йог|дзен|спа", ["meditation ambient healing"], "для медитации"),
]

# 4. Жанры
GENRES_DATA = [
    (r"киберпанк|cyberpunk", ["cyberpunk dark synthwave"], "киберпанк"),
    (r"фонк|phonk", ["phonk drift"], "фонк"),
    (r"\bрок\b|\bрока\b|\bроку\b|метал|\bпанк\b|\bпанка\b|альтернатив", ["rock hits"], "рок"),
    (r"рэп|реп|хип-?хоп", ["hip hop rap"], "рэп"),
    (r"джаз|блюз", ["jazz blues cafe"], "джаз"),
    (r"классик|пианино|фортепиано", ["classical piano"], "классику"),
    (r"синтвейв|ретровейв|80-|90-|восьмидесят|девяност|ретро|диско", ["synthwave 80s retrowave"], "синтвейв"),
    (r"электрон|техно|хаус|edm", ["electronic techno house"], "электронную музыку"),
    (r"инди", ["indie aesthetic chill"], "инди"),
    (r"\bпоп\b|\bпопса\b|\bпопсы\b|\bпопсу\b|чарт", ["pop hits"], "поп-музыку"),
    (r"акустик|гитар", ["acoustic guitar"], "акустику"),
    (r"лоуфай|lo-?fi", ["lofi hip hop"], "лоуфай"),
]


def parse_vibe(text: str) -> tuple[str, str] | None:
    """Анализирует текст запроса и возвращает (query_for_youtube, reply_title).

    Если запрос не связан с вайбом, настроением или музыкой, возвращает None.
    """
    if not text:
        return None
    text_low = text.lower().strip()

    # Проверка, что запрос вообще музыкальный или про настроение
    music_markers = (
        "вайб", "атмосфер", "настроени", "музык", "плейлист", "трек", "песн", "звуч",
        "подборк", "песен", "сыграй", "послушать", "послушаем"
    )
    is_vibe = any(m in text_low for m in music_markers) or bool(
        re.search(r"^(?:хочу|включи|поставь|вруби|запусти|найди)\s+(?:что[- ]то|что[- ]нибудь)", text_low)
    )

    tags: list[str] = []
    adjs_f: list[str] = []
    adjs_m: list[str] = []
    ctx_str: str | None = None
    genre_str: str | None = None

    # Поиск настроения
    for pat, t_list, af, am in MOODS_DATA:
        if re.search(pat, text_low):
            tags.extend(t_list)
            adjs_f.append(af)
            adjs_m.append(am)
            break

    # Поиск сезона
    for pat, t_list, af, am in SEASONS_DATA:
        if re.search(pat, text_low):
            tags.extend(t_list)
            adjs_f.append(af)
            adjs_m.append(am)
            break

    # Поиск жанра
    for pat, t_list, g in GENRES_DATA:
        if re.search(pat, text_low):
            tags.extend(t_list)
            genre_str = g
            break

    # Поиск контекста / окружения
    for pat, t_list, c in CONTEXTS_DATA:
        if re.search(pat, text_low):
            tags.extend(t_list)
            ctx_str = c
            break

    # Если ничего не нашли из списков, проверим свободный запрос с ключевым словом «вайб»
    if not tags:
        m = re.search(r"вайб(?:ом)?\s+([а-яёa-z0-9\s]+)", text_low)
        if m:
            vt = m.group(1).strip()
            vt = re.sub(r"\s+(?:но|при|этом|пожалуйста|мне|бы|же).*$", "", vt).strip()
            if vt and len(vt) >= 3:
                return f"{vt} vibes chill playlist", f"подборку под вайб {vt}"
        return None

    # Сборка естественного русского ответа
    if genre_str:
        prefix = " ".join(adjs_m)
        core = f"{prefix} {genre_str}".strip()
    else:
        prefix = " ".join(adjs_f)
        core = f"{prefix} подборку".strip() if prefix else "подборку"

    if ctx_str:
        if ctx_str.startswith(("под", "на", "в", "для")):
            title = f"{core} {ctx_str}"
        else:
            title = f"{core} с вайбом {ctx_str}"
    else:
        title = core

    # Поисковый запрос для YouTube / музыкального сервиса
    query = " ".join(tags + ["playlist"])
    return query, title
