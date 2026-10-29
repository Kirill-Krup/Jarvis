MAX_RESULTS = 5
MAX_SNIPPET_CHARS = 300


def _get_ddgs():
    try:
        from ddgs import DDGS
    except ImportError:
        from duckduckgo_search import DDGS
    return DDGS


def search(query: str) -> str:
    """Возвращает короткую сводку найденного текстом для передачи в LLM."""
    query = (query or "").strip()
    if not query:
        return "Пустой поисковый запрос."

    try:
        DDGS = _get_ddgs()
    except ImportError:
        return "Поиск недоступен: не установлен пакет ddgs (pip install ddgs)."

    try:
        results = DDGS().text(query, region="ru-ru", max_results=MAX_RESULTS)
    except Exception as e:
        return f"Поиск не удался: {e}"

    if not results:
        return "По этому запросу ничего не найдено."

    lines = []
    for item in results:
        title = (item.get("title") or "").strip()
        body = (item.get("body") or "").strip()[:MAX_SNIPPET_CHARS]
        lines.append(f"- {title}: {body}")
    return "\n".join(lines)
