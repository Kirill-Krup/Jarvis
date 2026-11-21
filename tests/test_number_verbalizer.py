"""Тесты преобразования чисел, времени, дат и единиц измерения в слова."""
from core.speakers.number_verbalizer import verbalize_numbers, int_to_words_ru, plural_form


def test_basic_integers():
    assert int_to_words_ru(0) == "ноль"
    assert int_to_words_ru(1) == "один"
    assert int_to_words_ru(1, gender="f") == "одна"
    assert int_to_words_ru(2, gender="f") == "две"
    assert int_to_words_ru(15) == "пятнадцать"
    assert int_to_words_ru(42) == "сорок два"
    assert int_to_words_ru(100) == "сто"
    assert int_to_words_ru(1000) == "одна тысяча"
    assert int_to_words_ru(2026) == "две тысячи двадцать шесть"
    assert int_to_words_ru(1000000) == "один миллион"


def test_plural_form():
    assert plural_form(1, "градус", "градуса", "градусов") == "градус"
    assert plural_form(2, "градус", "градуса", "градусов") == "градуса"
    assert plural_form(5, "градус", "градуса", "градусов") == "градусов"
    assert plural_form(21, "градус", "градуса", "градусов") == "градус"
    assert plural_form(12, "градус", "градуса", "градусов") == "градусов"


def test_time():
    assert verbalize_numbers("Сейчас 14:30") == "Сейчас четырнадцать тридцать"
    assert verbalize_numbers("Сейчас 08:05") == "Сейчас восемь ноль пять"
    assert verbalize_numbers("Сейчас 12:00") == "Сейчас двенадцать ноль ноль"


def test_date_and_year():
    assert verbalize_numbers("Сегодня 03.11.2026") == "Сегодня третье ноября две тысячи двадцать шестого года"
    assert verbalize_numbers("В 2026 году") == "В две тысячи двадцать шестом году"
    assert verbalize_numbers("2024 год") == "две тысячи двадцать четвёртый год"


def test_percents():
    assert verbalize_numbers("Зарядка 100%") == "Зарядка сто процентов"
    assert verbalize_numbers("1%") == "один процент"
    assert verbalize_numbers("2%") == "два процента"
    assert verbalize_numbers("15.5%") == "пятнадцать целых пять десятых процента"


def test_temperatures():
    assert verbalize_numbers("Температура +25°C") == "Температура плюс двадцать пять градусов Цельсия"
    assert verbalize_numbers("-5°") == "минус пять градусов"
    assert verbalize_numbers("0°") == "ноль градусов"
    assert verbalize_numbers("+21°") == "плюс двадцать один градус"


def test_units_and_currencies():
    assert verbalize_numbers("Свободно 256 ГБ") == "Свободно двести пятьдесят шесть гигабайт"
    assert verbalize_numbers("Таймер на 5 минут") == "Таймер на пять минут"
    assert verbalize_numbers("30 сек") == "тридцать секунд"
    assert verbalize_numbers("500 руб") == "пятьсот рублей"
    assert verbalize_numbers("100 км/ч") == "сто километров в час"


def test_math_expressions():
    assert verbalize_numbers("2 + 2 = 4") == "два плюс два равно четыре"
    assert verbalize_numbers("100 / 5 = 20") == "сто разделить на пять равно двадцать"
    assert verbalize_numbers("Результат: 12.5") == "Результат: двенадцать целых пять десятых"


def test_ranges_and_ordinals():
    assert verbalize_numbers("Диапазон 5-10") == "Диапазон от пяти до десяти"
    assert verbalize_numbers("Шаг 1-й и 2-й") == "Шаг первый и второй"
    assert verbalize_numbers("В XXI веке") == "В двадцать первом веке"
