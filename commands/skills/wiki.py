"""Голосовая Википедия: краткие факты и справка вслух без открытия браузера."""
import re
import urllib.parse
import requests

from commands.skills.registry import skill

CATEGORY = "📖 Справка и знания"

WIKI_API = "https://ru.wikipedia.org/api/rest_v1/page/summary/"
HEADERS = {"User-Agent": "JarvisAssistant/2.0 (Windows NT 10.0; Win64; x64)"}

STOP_WORDS = {
    "кто", "такой", "такая", "такое", "такие", "что", "это", "значит",
    "найди", "в", "википедии", "вики", "расскажи", "кратко", "про", "о", "об",
    "пожалуйста", "мне", "поясни", "информацию",
}

EXCLUDED_QUERIES = {"дела", "погода", "время", "ты", "сам", "жизнь", "настроение"}


def _clean_extract(extract: str) -> str:
    # Удаляем знаки ударения
    clean = re.sub(r"[\u0301\u0300]", "", extract)
    # Удаляем скобки с датами и оригинальными названиями
    clean = re.sub(r"\s*\([^)]*\)", "", clean)
    clean = re.sub(r"[«»\"'<>]", " ", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    sentences = re.split(r"(?<=[.!?])\s+", clean)
    return " ".join(sentences[:2]).strip()


def get_wiki_summary(term: str) -> str | None:
    """Делает быстрый запрос к Википедии и возвращает 1-2 предложения."""
    term = term.strip()
    if not term or term.lower() in EXCLUDED_QUERIES:
        return None

    # Кандидаты для проверки: полный термин и при необходимости первое ключевое слово
    candidates = [
        term.capitalize(),
        term.title(),
        term,
    ]
    parts = term.split()
    if len(parts) > 1 and parts[0].lower() not in STOP_WORDS:
        candidates.append(parts[0].capitalize())

    for cand in candidates:
        try:
            formatted = cand.replace(" ", "_")
            url = WIKI_API + urllib.parse.quote(formatted)
            resp = requests.get(url, headers=HEADERS, timeout=2.5)
            if resp.status_code == 200:
                data = resp.json()
                extract = data.get("extract", "")
                if extract:
                    summary = _clean_extract(extract)
                    if summary:
                        return summary
        except Exception:
            pass

    return None


@skill(CATEGORY, "Быстрая справка из Википедии вслух",
       ["кто такой Илон Маск", "что такое сингулярность", "найди в википедии квантовый компьютер",
        "расскажи про питон", "кто такие ацтеки"],
       [r"^(?:кто\s+(?:такой|такая|такие)|что\s+(?:такое|значит))\s+[а-яёa-z0-9]",
        r"^(?:найди\s+в\s+википедии|найди\s+в\s+вики|расскажи\s+(?:кратко\s+)?про)\s+[а-яёa-z0-9]"],
       exclusive=True)
def handle_wiki_search(cmd, ctx):
    text = getattr(cmd, "text_lower", str(cmd).lower()).strip()

    # Извлекаем ключевой термин
    words = text.split()
    query_words = [w for w in words if w not in STOP_WORDS]
    term = " ".join(query_words).strip()

    if not term:
        return ctx.reply("О ком или о чём именно рассказать?")

    summary = get_wiki_summary(term)
    if summary:
        return ctx.reply(summary)

    # Если точной статьи нет, открываем поиск в браузере как резервный вариант
    from core.browser import open_url
    search_url = f"https://ru.wikipedia.org/w/index.php?search={urllib.parse.quote_plus(term)}"
    open_url(search_url)
    return ctx.reply(f"Не нашел краткую статью по запросу {term}. Открыл поиск в браузере.")
