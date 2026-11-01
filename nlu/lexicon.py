"""Фонетическое сопоставление русской речи и английских названий.

Vosk — русская модель: английские слова она записывает кириллицей
(«интеллиджей идея» вместо «IntelliJ IDEA»), а иногда подменяет похожими
русскими («дискомфорт» вместо «дискорд»). Здесь сравниваются не буквы, а
звучание: оба названия приводятся к одному упрощённому «фонетическому ключу».
"""
import re

from thefuzz import fuzz
from transliterate import translit

from config.basic_apps import BASIC_APPS

# Английские сочетания -> как они звучат по-русски (порядок важен)
_EN_RULES = [
    ("tch", "ч"), ("sch", "ск"), ("ck", "к"), ("ph", "ф"), ("sh", "ш"),
    ("ch", "ч"), ("th", "з"), ("wh", "в"), ("qu", "кв"), ("oo", "у"),
    ("ee", "и"), ("ea", "и"), ("ou", "а"), ("igh", "ай"), ("gh", ""),
    ("kn", "н"), ("wr", "р"), ("x", "кс"), ("j", "дж"), ("w", "в"),
    ("q", "к"), ("y", "и"), ("h", "х"),
]
_SOFT_C = re.compile(r"c(?=[eiy])")

# Упрощение русских гласных/согласных: «звучат одинаково» -> одна буква
_RU_SIMPLIFY = str.maketrans({
    "ё": "е", "э": "е", "е": "и", "й": "и", "ы": "и", "я": "а", "ю": "у",
    "о": "а", "ъ": "", "ь": "", "з": "с", "д": "т", "б": "п", "г": "к",
    "в": "ф", "ж": "ш",
})


def en_to_ru(text: str) -> str:
    """Приблизительное русское звучание английского текста."""
    t = _SOFT_C.sub("с", text.lower())
    t = t.replace("c", "к")
    for src, dst in _EN_RULES:
        t = t.replace(src, dst)
    try:
        return translit(t, "ru")
    except Exception:
        return t


def phonetic_key(text: str) -> str:
    """Ключ звучания: для русского и английского текста выглядит одинаково."""
    t = text.lower()
    if re.search(r"[a-z]", t):
        t = en_to_ru(t)
    t = t.translate(_RU_SIMPLIFY)
    t = re.sub(r"[^а-я ]", "", t)
    t = re.sub(r"(.)\1+", r"\1", t)
    return t.replace(" ", "")


def similarity(spoken: str, name: str) -> int:
    """Насколько фраза похожа на название (0-100): по буквам и по звучанию."""
    a, b = spoken.lower().strip(), name.lower().strip()
    if a == b:
        return 100
    ka, kb = phonetic_key(a), phonetic_key(b)
    if not ka or not kb:
        return 0
    phon = fuzz.ratio(ka, kb)
    # «идея» -> «intellij idea»: короткое имя целиком внутри длинного
    if len(ka) >= 4 and ka in kb and len(ka) / len(kb) >= 0.4:
        phon = max(phon, 88)
    return max(phon, fuzz.ratio(a, b))


# ----------------------------------------------------------------- названия

def builtin_names() -> dict[str, str]:
    """Все известные названия из BASIC_APPS: {вариант произношения: id}."""
    names: dict[str, str] = {}
    for item in BASIC_APPS:
        for variant in (*item.get("aliases", []), item["title"], *item.get("search_names", [])):
            names[variant.lower().strip()] = item["id"]
    return names


def best_match(spoken: str, names, min_score: int = 80) -> tuple[str, int] | None:
    """Лучшее название из `names`, похожее на сказанное. None, если не нашли."""
    spoken = spoken.lower().strip()
    if len(spoken) < 3:
        return None
    best, best_score = None, 0
    for name in names:
        if abs(len(name) - len(spoken)) > max(len(name), len(spoken)) * 0.6:
            continue  # слишком разной длины: ложное совпадение
        score = similarity(spoken, name)
        if score > best_score:
            best, best_score = name, score
    if best and best_score >= min_score:
        return best, best_score
    return None
