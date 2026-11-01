"""Исправление ошибок распознавания речи в названиях программ.

Vosk часто слышит «включи дискомфорт» вместо «включи дискорд». После глаголов
«открой / запусти / включи / закрой…» сказанное название сверяется со списком
известных программ по звучанию, а также с запасными вариантами, которые
вернул распознаватель (alternatives).
"""
import re

from nlu.lexicon import best_match

ACTION_VERBS = (
    "открой", "запусти", "включи", "закрой", "закрыть", "выключи", "запускай",
    "вруби", "выруби", "открыть", "запустить",
)
_VERB_RE = re.compile(rf"^({'|'.join(ACTION_VERBS)})\s+(.+)$")

# Эти слова обрабатываются другими командами: их «исправлять» нельзя
PROTECTED_STARTS = (
    "музык", "песн", "трек", "звук", "громк", "блютуз", "bluetooth", "вай", "wifi",
    "точк", "сайт", "папк", "приложени", "программ", "экран", "яркост", "скриншот",
    "диспетчер", "режим", "таймер", "канал", "ютуб", "фильм", "сериал", "аниме",
    "компьютер", "ноутбук", "пк", "что", "как", "мне", "мой", "проект", "список",
    "окно", "окна", "вкладк", "страниц", "радио", "плейлист", "погод", "свет",
)
MAX_TARGET_WORDS = 4
MIN_SCORE = 78

# Частые устойчивые ослышки (то, что Vosk выдаёт чаще всего)
CONFUSIONS = {
    "дискомфорт": "дискорд", "дискомфорта": "дискорд", "дискомфорте": "дискорд",
    "дисках": "дискорд", "диск корт": "дискорд", "дискорт": "дискорд",
    "телеграмма": "телеграм", "телеграмм": "телеграм",
    "стимер": "стим", "степь": "стим",
}


def _split(text: str):
    m = _VERB_RE.match(text)
    if not m:
        return None
    target = re.sub(r"\s+(пожалуйста|мне)$", "", m.group(2)).strip()
    return m.group(1), target


def fix_speech(text: str, alternatives=(), known_names=()) -> str:
    """Возвращает фразу с исправленным названием программы (или как была)."""
    parts = _split(text.lower().strip())
    if not parts:
        return text
    verb, target = parts
    if (not target or len(target.split()) > MAX_TARGET_WORDS
            or target.startswith(PROTECTED_STARTS)):
        return text

    known = set(known_names)
    if target in known:
        return text
    if target in CONFUSIONS:
        return f"{verb} {CONFUSIONS[target]}"

    # кандидаты: основной вариант + то, что Vosk считал запасными
    candidates = [target]
    for alt in alternatives:
        alt_parts = _split(alt.lower().strip())
        if alt_parts and alt_parts[1] not in candidates:
            candidates.append(alt_parts[1])

    best, best_score = None, 0
    for cand in candidates:
        if cand in known:
            return f"{verb} {cand}"
        if cand.startswith(PROTECTED_STARTS):
            continue
        found = best_match(cand, known, MIN_SCORE)
        if found and found[1] > best_score:
            best, best_score = found
    if best:
        print(f"[SPEECH-FIX] «{target}» -> «{best}» ({best_score})")
        return f"{verb} {best}"
    return text
