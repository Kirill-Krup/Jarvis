"""Преобразование чисел, дат, времени и единиц измерения в слова на русском языке.

Используется перед синтезом речи (TTS), чтобы Джарвис правильно и естественно
произносил любые числа, проценты, градусы, время, даты, формулы и единицы.
Полностью автономен и не требует сторонних библиотек (работает без num2words).
"""
import re

# -----------------------------------------------------------------------------
# Базовые таблицы числительных
# -----------------------------------------------------------------------------

_UNITS_M = {
    0: "ноль", 1: "один", 2: "два", 3: "три", 4: "четыре", 5: "пять",
    6: "шесть", 7: "семь", 8: "восемь", 9: "девять",
}
_UNITS_F = {
    0: "ноль", 1: "одна", 2: "две", 3: "три", 4: "четыре", 5: "пять",
    6: "шесть", 7: "семь", 8: "восемь", 9: "девять",
}
_UNITS_N = {
    0: "ноль", 1: "одно", 2: "два", 3: "три", 4: "четыре", 5: "пять",
    6: "шесть", 7: "семь", 8: "восемь", 9: "девять",
}

_TEENS = {
    10: "десять", 11: "одиннадцать", 12: "двенадцать", 13: "тринадцать",
    14: "четырнадцать", 15: "пятнадцать", 16: "шестнадцать", 17: "семнадцать",
    18: "восемнадцать", 19: "девятнадцать",
}

_TENS = {
    20: "двадцать", 30: "тридцать", 40: "сорок", 50: "пятьдесят",
    60: "шестьдесят", 70: "семьдесят", 80: "восемьдесят", 90: "девяносто",
}

_HUNDREDS = {
    100: "сто", 200: "двести", 300: "триста", 400: "четыреста", 500: "пятьсот",
    600: "шестьсот", 700: "семьсот", 800: "восемьсот", 900: "девятьсот",
}

# (one, few, many, gender)
_ORDERS = [
    ("", "", "", "m"),
    ("тысяча", "тысячи", "тысяч", "f"),
    ("миллион", "миллиона", "миллионов", "m"),
    ("миллиард", "миллиарда", "миллиардов", "m"),
    ("триллион", "триллиона", "триллионов", "m"),
]

_MONTHS_GEN = {
    1: "января", 2: "февраля", 3: "марта", 4: "апреля",
    5: "мая", 6: "июня", 7: "июля", 8: "августа",
    9: "сентября", 10: "октября", 11: "ноября", 12: "декабря",
}

_DAYS_ORDINAL_N = {
    1: "первое", 2: "второе", 3: "третье", 4: "четвёртое", 5: "пятое",
    6: "шестое", 7: "седьмое", 8: "восьмое", 9: "девятое", 10: "десятое",
    11: "одиннадцатое", 12: "двенадцатое", 13: "тринадцатое", 14: "четырнадцатое",
    15: "пятнадцатое", 16: "шестнадцатое", 17: "семнадцатое", 18: "восемнадцатое",
    19: "девятнадцатое", 20: "двадцатое", 21: "двадцать первое", 22: "двадцать второе",
    23: "двадцать третье", 24: "двадцать четвёртое", 25: "двадцать пятое",
    26: "двадцать шестое", 27: "двадцать седьмое", 28: "двадцать восьмое",
    29: "двадцать девятое", 30: "тридцатое", 31: "тридцать первое",
}

_ORDINALS_M = {
    0: "нулевой", 1: "первый", 2: "второй", 3: "третий", 4: "четвёртый", 5: "пятый",
    6: "шестой", 7: "седьмой", 8: "восьмой", 9: "девятый", 10: "десятый",
    11: "одиннадцатый", 12: "двенадцатый", 13: "тринадцатый", 14: "четырнадцатый",
    15: "пятнадцатый", 16: "шестнадцатый", 17: "семнадцатый", 18: "восемнадцатый",
    19: "девятнадцатый", 20: "двадцатый", 30: "тридцатый", 40: "сороковой",
    50: "пятидесятый", 60: "шестидесятый", 70: "семидесятый", 80: "восьмидесятый",
    90: "девяностый", 100: "сотый", 200: "двухсотый", 300: "трёхсотый",
    400: "четырёхсотый", 500: "пятисотый", 600: "шестисотый", 700: "семисотый",
    800: "восьмисотый", 900: "девятисотый", 1000: "тысячный",
}

_ROMAN_VALUES = {
    "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8, "IX": 9,
    "X": 10, "XI": 11, "XII": 12, "XIII": 13, "XIV": 14, "XV": 15, "XVI": 16,
    "XVII": 17, "XVIII": 18, "XIX": 19, "XX": 20, "XXI": 21,
}


def plural_form(n: int, one: str, few: str, many: str) -> str:
    """Выбор правильного окончания существительного в зависимости от числа."""
    n_abs = abs(int(n)) % 100
    if 11 <= n_abs <= 14:
        return many
    rem = n_abs % 10
    if rem == 1:
        return one
    if 2 <= rem <= 4:
        return few
    return many


def _triplet_to_words(n: int, gender: str = "m") -> list[str]:
    """Разбор трёхзначного числа (0-999)."""
    words = []
    h = (n // 100) * 100
    if h in _HUNDREDS:
        words.append(_HUNDREDS[h])
    rem = n % 100
    if 10 <= rem <= 19:
        words.append(_TEENS[rem])
    else:
        t = (rem // 10) * 10
        if t in _TENS:
            words.append(_TENS[t])
        u = rem % 10
        if u > 0 or (n == 0 and not words):
            table = _UNITS_F if gender == "f" else (_UNITS_N if gender == "n" else _UNITS_M)
            words.append(table[u])
    return words


def int_to_words_ru(n: int, gender: str = "m") -> str:
    """Преобразование целого числа в текст на русском языке."""
    if n == 0:
        return "ноль"
    sign = "минус " if n < 0 else ""
    n = abs(n)
    if n > 999_999_999_999:
        return f"{sign}{n}"

    triplets = []
    temp = n
    while temp > 0:
        triplets.append(temp % 1000)
        temp //= 1000

    parts = []
    for idx, triplet in enumerate(triplets):
        if triplet == 0:
            continue
        order_one, order_few, order_many, order_gender = _ORDERS[idx]
        g = order_gender if idx > 0 else gender
        w = _triplet_to_words(triplet, g)
        if idx > 0:
            w.append(plural_form(triplet, order_one, order_few, order_many))
        parts = w + parts

    return sign + " ".join(parts)


def ordinal_year_genitive(year: int) -> str:
    """Год в родительном падеже: '2026' -> 'две тысячи двадцать шестого года'."""
    if year < 1000 or year > 2100:
        return f"{int_to_words_ru(year)} года"
    thousands = year // 1000
    rem = year % 1000
    prefix_words = []
    if thousands == 2:
        prefix_words.append("две тысячи")
    elif thousands == 1:
        prefix_words.append("тысяча")

    tens_units = rem % 100
    hundreds = (rem // 100) * 100
    if hundreds in _HUNDREDS:
        prefix_words.append(_HUNDREDS[hundreds])

_ORD_GEN = {
    0: "нулевого", 1: "первого", 2: "второго", 3: "третьего", 4: "четвёртого",
    5: "пятого", 6: "шестого", 7: "седьмого", 8: "восьмого", 9: "девятого",
    10: "десятого", 11: "одиннадцатого", 12: "двенадцатого", 13: "тринадцатого",
    14: "четырнадцатого", 15: "пятнадцатого", 16: "шестнадцатого",
    17: "семнадцатого", 18: "восемнадцатого", 19: "девятнадцатого",
    20: "двадцатого", 30: "тридцатого", 40: "сорокового", 50: "пятидесятого",
    60: "шестидесятого", 70: "семидесятого", 80: "восьмидесятого", 90: "девяностого",
}

_ORD_PREP = {
    0: "нулевом", 1: "первом", 2: "втором", 3: "третьем", 4: "четвёртом",
    5: "пятом", 6: "шестом", 7: "седьмом", 8: "восьмом", 9: "девятом",
    10: "десятом", 11: "одиннадцатом", 12: "двенадцатом", 13: "тринадцатом",
    14: "четырнадцатом", 15: "пятнадцатом", 16: "шестнадцатом",
    17: "семнадцатом", 18: "восемнадцатом", 19: "девятнадцатом",
    20: "двадцатом", 30: "тридцатом", 40: "сороковом", 50: "пятидесятом",
    60: "шестидесятом", 70: "семидесятом", 80: "восьмидесятом", 90: "девяностом",
}


def ordinal_year_words(year: int, case: str = "gen") -> str:
    """Год словами: 2024 -> две тысячи двадцать четвёртый (nom), четвёртого (gen), четвёртом (prep)."""
    if year < 1000 or year > 2100:
        return f"{int_to_words_ru(year)} года"
    thousands = year // 1000
    rem = year % 1000
    prefix_words = []
    if thousands == 2:
        prefix_words.append("две тысячи")
    elif thousands == 1:
        prefix_words.append("тысяча")

    tens_units = rem % 100
    hundreds = (rem // 100) * 100
    if hundreds in _HUNDREDS:
        prefix_words.append(_HUNDREDS[hundreds])

    table = _ORD_PREP if case == "prep" else (_ORD_GEN if case == "gen" else _ORDINALS_M)

    if 10 <= tens_units <= 19 or tens_units in table:
        prefix_words.append(table[tens_units])
    else:
        t = (tens_units // 10) * 10
        if t in _TENS:
            prefix_words.append(_TENS[t])
        u = tens_units % 10
        if u in table:
            prefix_words.append(table[u])

    return " ".join(prefix_words)


def ordinal_year_genitive(year: int) -> str:
    return ordinal_year_words(year, case="gen")


def decimal_to_words_ru(whole_str: str, frac_str: str) -> str:
    """Десятичная дробь -> русский текст."""
    try:
        whole = int(whole_str)
        frac = int(frac_str)
    except ValueError:
        return f"{whole_str}.{frac_str}"

    whole_words = int_to_words_ru(whole, gender="f")
    whole_form = "целая" if abs(whole) % 10 == 1 and abs(whole) % 100 != 11 else "целых"

    digits_count = len(frac_str)
    if digits_count == 1:
        name_one, name_few, name_many = "десятая", "десятых", "десятых"
    elif digits_count == 2:
        name_one, name_few, name_many = "сотая", "сотых", "сотых"
    elif digits_count == 3:
        name_one, name_few, name_many = "тысячная", "тысячных", "тысячных"
    elif digits_count == 4:
        name_one, name_few, name_many = "десятитысячная", "десятитысячных", "десятитысячных"
    else:
        name_one, name_few, name_many = "сотых", "сотых", "сотых"

    frac_words = int_to_words_ru(frac, gender="f")
    frac_form = plural_form(frac, name_one, name_few, name_many)

    return f"{whole_words} {whole_form} {frac_words} {frac_form}"


def _replace_time(m: re.Match) -> str:
    h = int(m.group(1))
    mins = int(m.group(2))
    h_word = int_to_words_ru(h, gender="m")
    if mins == 0:
        return f"{h_word} ноль ноль"
    elif mins < 10:
        return f"{h_word} ноль {int_to_words_ru(mins, gender='m')}"
    else:
        return f"{h_word} {int_to_words_ru(mins, gender='m')}"


def _replace_date(m: re.Match) -> str:
    day = int(m.group(1))
    month = int(m.group(2))
    year = int(m.group(3))
    day_str = _DAYS_ORDINAL_N.get(day, int_to_words_ru(day, "n"))
    month_str = _MONTHS_GEN.get(month, "")
    year_str = ordinal_year_genitive(year) + " года"
    return f"{day_str} {month_str} {year_str}".strip()


def _replace_year_standalone(m: re.Match) -> str:
    year = int(m.group(1))
    suffix = (m.group(2) or "").strip().lower()
    if "году" in suffix:
        return f"{ordinal_year_words(year, case='prep')} году"
    elif suffix in ("года", "г.", "г"):
        return f"{ordinal_year_words(year, case='gen')} года"
    else:
        return f"{ordinal_year_words(year, case='nom')} год"


def _replace_percent(m: re.Match) -> str:
    num_str = m.group(1).replace(",", ".")
    if "." in num_str:
        w, f = num_str.split(".", 1)
        return f"{decimal_to_words_ru(w, f)} процента"
    n = int(num_str)
    words = int_to_words_ru(n, gender="m")
    form = plural_form(n, "процент", "процента", "процентов")
    return f"{words} {form}"


def _replace_temperature(m: re.Match) -> str:
    sign_str = m.group(1) or ""
    val = int(m.group(2))
    unit = m.group(3) or ""

    prefix = "минус " if sign_str == "-" else ("плюс " if sign_str == "+" else "")
    words = int_to_words_ru(val, gender="m")
    form = plural_form(val, "градус", "градуса", "градусов")
    celsius = " Цельсия" if "c" in unit.lower() or "с" in unit.lower() else ""
    return f"{prefix}{words} {form}{celsius}"


def _replace_unit(m: re.Match) -> str:
    num_str = m.group(1)
    unit = m.group(2).lower().rstrip(".")
    n = int(num_str)

    units_map = {
        "км/ч": ("километр в час", "километра в час", "километров в час", "m"),
        "м/с": ("метр в секунду", "метра в секунду", "метров в секунду", "m"),
        "км": ("километр", "километра", "километров", "m"),
        "м": ("метр", "метра", "метров", "m"),
        "см": ("сантиметр", "сантиметра", "сантиметров", "m"),
        "мм": ("миллиметр", "миллиметра", "миллиметров", "m"),
        "кг": ("килограмм", "килограмма", "килограммов", "m"),
        "г": ("грамм", "грамма", "граммов", "m"),
        "гб": ("гигабайт", "гигабайта", "гигабайт", "m"),
        "gb": ("гигабайт", "гигабайта", "гигабайт", "m"),
        "мб": ("мегабайт", "мегабайта", "мегабайт", "m"),
        "mb": ("мегабайт", "мегабайта", "мегабайт", "m"),
        "кб": ("килобайт", "килобайта", "килобайт", "m"),
        "kb": ("килобайт", "килобайта", "килобайт", "m"),
        "тб": ("терабайт", "терабайта", "терабайт", "m"),
        "tb": ("терабайт", "терабайта", "терабайт", "m"),
        "руб": ("рубль", "рубля", "рублей", "m"),
        "₽": ("рубль", "рубля", "рублей", "m"),
        "$": ("доллар", "доллара", "долларов", "m"),
        "€": ("евро", "евро", "евро", "m"),
        "мин": ("минута", "минуты", "минут", "f"),
        "сек": ("секунда", "секунды", "секунд", "f"),
        "с": ("секунда", "секунды", "секунд", "f"),
        "ч": ("час", "часа", "часов", "m"),
        "год": ("год", "года", "лет", "m"),
        "года": ("год", "года", "лет", "m"),
        "лет": ("год", "года", "лет", "m"),
        "день": ("день", "дня", "дней", "m"),
        "дня": ("день", "дня", "дней", "m"),
        "дней": ("день", "дня", "дней", "m"),
        "неделя": ("неделя", "недели", "недель", "f"),
        "недели": ("неделя", "недели", "недель", "f"),
        "недель": ("неделя", "недели", "недель", "f"),
        "месяц": ("месяц", "месяца", "месяцев", "m"),
        "месяца": ("месяц", "месяца", "месяцев", "m"),
        "месяцев": ("месяц", "месяца", "месяцев", "m"),
    }

    if unit in units_map:
        one, few, many, gender = units_map[unit]
        words = int_to_words_ru(n, gender=gender)
        form = plural_form(n, one, few, many)
        return f"{words} {form}"
    return f"{int_to_words_ru(n)} {unit}"


def _replace_currency(m: re.Match) -> str:
    curr = m.group(1) or m.group(4)
    val = int(m.group(2) or m.group(3))
    w = int_to_words_ru(val, gender="m")
    if curr == "$":
        f = plural_form(val, "доллар", "доллара", "долларов")
    elif curr == "€":
        f = "евро"
    else:
        f = plural_form(val, "рубль", "рубля", "рублей")
    return f"{w} {f}"


def _replace_ordinal_hyphen(m: re.Match) -> str:
    n = int(m.group(1))
    suffix = m.group(2).lower()
    base_m = _ORDINALS_M.get(n)
    if not base_m:
        words = int_to_words_ru(n, gender="m")
        return f"{words}-{suffix}"

    if suffix in ("й", "ой", "ый"):
        return base_m
    elif suffix in ("я", "ая"):
        return re.sub(r"(?:ый|ой|ий)$", "ая", base_m)
    elif suffix in ("е", "ое", "ье"):
        return re.sub(r"(?:ый|ой|ий)$", "ое", base_m)
    elif suffix in ("го", "ого", "его"):
        return re.sub(r"(?:ый|ой)$", "ого", re.sub(r"ий$", "его", base_m))
    elif suffix in ("му", "ому", "ему"):
        return re.sub(r"(?:ый|ой)$", "ому", re.sub(r"ий$", "ему", base_m))
    elif suffix in ("м", "ом", "ем", "им"):
        return re.sub(r"(?:ый|ой)$", "ом", re.sub(r"ий$", "ем", base_m))
    return base_m


def _replace_range(m: re.Match) -> str:
    n1 = int(m.group(1))
    n2 = int(m.group(2))
    _GEN_SMALL = {
        0: "ноля", 1: "одного", 2: "двух", 3: "трёх", 4: "четырёх", 5: "пяти",
        6: "шести", 7: "семи", 8: "восьми", 9: "девяти", 10: "десяти",
        15: "пятнадцати", 20: "двадцати", 30: "тридцати", 50: "пятидесяти",
        100: "ста",
    }
    w1 = _GEN_SMALL.get(n1, int_to_words_ru(n1))
    w2 = _GEN_SMALL.get(n2, int_to_words_ru(n2))
    return f"от {w1} до {w2}"


def ordinal_ru(n: int, case: str = "nom") -> str:
    """Порядковое числительное: 21 -> двадцать первый (nom), двадцать первом (prep), двадцать первого (gen)."""
    tens_units = n % 100
    prefix = []
    h = (n // 100) * 100
    if h in _HUNDREDS:
        prefix.append(_HUNDREDS[h])
    if tens_units in _ORDINALS_M:
        last = _ORDINALS_M[tens_units]
    else:
        t = (tens_units // 10) * 10
        if t in _TENS:
            prefix.append(_TENS[t])
        u = tens_units % 10
        last = _ORDINALS_M.get(u, "первый")

    if case == "gen":
        last = re.sub(r"(?:ый|ой)$", "ого", re.sub(r"ий$", "его", last))
    elif case == "prep":
        last = re.sub(r"(?:ый|ой)$", "ом", re.sub(r"ий$", "ем", last))
    elif case == "dat":
        last = re.sub(r"(?:ый|ой)$", "ому", re.sub(r"ий$", "ему", last))
    elif case == "inst":
        last = re.sub(r"(?:ый|ой)$", "ым", re.sub(r"ий$", "им", last))

    return " ".join(prefix + [last])


def _replace_roman(m: re.Match) -> str:
    roman = m.group(1)
    century_word = m.group(2) or ""
    val = _ROMAN_VALUES.get(roman)
    if not val:
        return m.group(0)

    # XXI век / в XXI веке
    if century_word:
        low = century_word.lower()
        if "веке" in low:
            return f"{ordinal_ru(val, case='prep')} {century_word}"
        elif "века" in low:
            return f"{ordinal_ru(val, case='gen')} {century_word}"
        else:
            return f"{ordinal_ru(val, case='nom')} {century_word}"

    return ordinal_ru(val, case="nom")


# -----------------------------------------------------------------------------
# Главная функция вербализации текста
# -----------------------------------------------------------------------------

def verbalize_numbers(text: str) -> str:
    """Преобразует любые числа, даты, дроби, время и символы в русские слова."""
    if not text:
        return ""
    text = str(text)

    # 1. Время формата ЧЧ:ММ (например: 14:30, 08:00, 18:05)
    text = re.sub(r"\b([01]?\d|2[0-3]):([0-5]\d)(?::[0-5]\d)?\b", _replace_time, text)

    # 2. Даты формата ДД.ММ.ГГГГ (например: 03.11.2026, 1.05.2024)
    text = re.sub(r"\b([0-2]?\d|3[01])\.(0\d|1[0-2])\.(\d{4})\b", _replace_date, text)

    # 3. Год с ключевым словом: "2026 год", "в 2026 году", "2024 г."
    text = re.sub(r"\b(19\d\d|20\d\d)\s*(год[ауе]?|г\.|г)\b", _replace_year_standalone, text, flags=re.IGNORECASE)

    # 4. Температура и градусы (+25°C, -5°, 20 градусов)
    text = re.sub(r"([+-])?(\d+)\s*°\s*([cCсС]?)(?!\w)", _replace_temperature, text)
    text = re.sub(r"([+-])(\d+)\s*(градус\w*)",
                  lambda m: f"{'минус ' if m.group(1)=='-' else 'плюс '}{int_to_words_ru(int(m.group(2)))} {m.group(3)}",
                  text)

    # 5. Проценты (50%, 12.5%, 1%)
    text = re.sub(r"\b(\d+(?:[.,]\d+)?)\s*%", _replace_percent, text)

    # 6. Валюты ($100, 100$, €50, ₽500, 500 ₽)
    text = re.sub(r"([$€₽])\s*(\d+)\b|\b(\d+)\s*([$€₽])", _replace_currency, text)

    # 7. Единицы измерения (100 км/ч, 5 км, 500 руб, 16 ГБ, 5 мин, 30 сек, 2 ч, 3 дня, 2 недели)
    text = re.sub(r"\b(\d+)\s*(км/ч|м/с|км|мм|см|кг|гб|gb|мб|mb|кб|kb|тб|tb|руб\.?|мин\.?|сек\.?|ч\.?|лет|год[а]?|дн[ей|я]|день|недел[и|ь|я]|месяц[ев|а]?)\b",
                 _replace_unit, text, flags=re.IGNORECASE)

    # 8. Диапазоны чисел (5-10, 1-2)
    text = re.sub(r"\b(\d+)\s*[-—–]\s*(\d+)\b", _replace_range, text)

    # 9. Порядковые числительные с дефисом (1-й, 2-го, 3-я, 5-е)
    text = re.sub(r"\b(\d+)-([а-яёА-ЯЁ]{1,3})\b", _replace_ordinal_hyphen, text)

    # 10. Римские цифры (в XXI веке, XXI век, глава IV)
    text = re.sub(r"\b(XXI|XX|XIX|XVIII|XVII|XVI|XV|XIV|XIII|XII|XI|X|IX|VIII|VII|VI|V|IV|III|II|I)\b(?:\s+(век[аеуом]?|в\.))?",
                  _replace_roman, text)

    # 11. Математические операторы в формулах (2 + 2 = 4, 100 / 5)
    text = re.sub(r"(\d+)\s*\+\s*(\d+)", lambda m: f"{m.group(1)} плюс {m.group(2)}", text)
    text = re.sub(r"(\d+)\s*[-−]\s*(\d+)", lambda m: f"{m.group(1)} минус {m.group(2)}", text)
    text = re.sub(r"(\d+)\s*[*×]\s*(\d+)", lambda m: f"{m.group(1)} умножить на {m.group(2)}", text)
    text = re.sub(r"(\d+)\s*[/÷]\s*(\d+)", lambda m: f"{m.group(1)} разделить на {m.group(2)}", text)
    text = re.sub(r"\s*=\s*", " равно ", text)

    # 12. Десятичные дроби (3.14, 0,5, 12.01)
    def _frac_repl(m):
        raw = m.group(0).replace(",", ".")
        w, f = raw.split(".", 1)
        return decimal_to_words_ru(w, f)
    text = re.sub(r"\b\d+[.,]\d+\b", _frac_repl, text)

    # 13. Отрицательные и положительные числа со знаком (-5, +10)
    text = re.sub(r"(?:(?<=\s)|^)[-−](\d+)\b", lambda m: f"минус {int_to_words_ru(int(m.group(1)))}", text)
    text = re.sub(r"(?:(?<=\s)|^)\+(\d+)\b", lambda m: f"плюс {int_to_words_ru(int(m.group(1)))}", text)

    # 14. Любые оставшиеся целые числа
    text = re.sub(r"\b\d+\b", lambda m: int_to_words_ru(int(m.group(0))), text)

    # 15. Чистка лишних пробелов
    text = re.sub(r"\s+", " ", text).strip()
    return text
