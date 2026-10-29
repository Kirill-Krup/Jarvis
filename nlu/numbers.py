"""Русские числа словами -> цифры («громкость пятьдесят» -> «громкость 50»).

Vosk возвращает числа словами, а обработчики громкости и яркости ищут \\d+.
Поддерживаются числа 0–999.
"""
_UNITS = {
    "ноль": 0, "нуль": 0, "один": 1, "одна": 1, "одно": 1, "два": 2, "две": 2, "три": 3, "четыре": 4,
    "пять": 5, "шесть": 6, "семь": 7, "восемь": 8, "девять": 9, "десять": 10, "одиннадцать": 11,
    "двенадцать": 12, "тринадцать": 13, "четырнадцать": 14, "пятнадцать": 15, "шестнадцать": 16,
    "семнадцать": 17, "восемнадцать": 18, "девятнадцать": 19,
}
_TENS = {
    "двадцать": 20, "тридцать": 30, "сорок": 40, "пятьдесят": 50, "шестьдесят": 60,
    "семьдесят": 70, "восемьдесят": 80, "девяносто": 90,
}
_HUNDREDS = {
    "сто": 100, "двести": 200, "триста": 300, "четыреста": 400, "пятьсот": 500,
    "шестьсот": 600, "семьсот": 700, "восемьсот": 800, "девятьсот": 900,
}


def _rank(word: str):
    if word in _HUNDREDS:
        return 3
    if word in _TENS:
        return 2
    if word in _UNITS:
        return 1
    return 0


def _value(word: str) -> int:
    return _HUNDREDS.get(word) or _TENS.get(word) or _UNITS.get(word, 0)


def ru_numbers_to_digits(text: str) -> str:
    words = text.split()
    out = []
    i = 0
    while i < len(words):
        word = words[i].lower()
        rank = _rank(word)
        if not rank:
            out.append(words[i])
            i += 1
            continue

        total = _value(word)
        last_rank = rank
        i += 1
        while i < len(words):
            nxt = words[i].lower()
            nxt_rank = _rank(nxt)
            # число продолжается, пока разряды идут по убыванию: сто двадцать пять
            if nxt_rank and nxt_rank < last_rank and not (last_rank == 2 and _value(nxt) >= 10):
                total += _value(nxt)
                last_rank = nxt_rank
                i += 1
            else:
                break
        out.append(str(total))
    return " ".join(out)