import datetime

from commands.reminders import parse_when

NOW = datetime.datetime(2026, 11, 1, 12, 0)


def _due(text):
    result = parse_when(text, NOW)
    assert result is not None, text
    return result


def test_relative_minutes():
    due, task = _due("напомни через 10 минут позвонить маме")
    assert due == NOW + datetime.timedelta(minutes=10)
    assert task == "позвонить маме"


def test_relative_words_and_default_amount():
    assert _due("напомни через пять минут выпить воды")[0] == NOW + datetime.timedelta(minutes=5)
    assert _due("напомни через час проверить суп")[0] == NOW + datetime.timedelta(hours=1)
    assert _due("напомни через минуту проверить")[0] == NOW + datetime.timedelta(minutes=1)


def test_half_hour():
    due, task = _due("напомни через полчаса выключить плиту")
    assert due == NOW + datetime.timedelta(minutes=30)
    assert task == "выключить плиту"


def test_absolute_time_today_and_tomorrow():
    due, task = _due("напомни в 18:30 купить хлеб")
    assert due == NOW.replace(hour=18, minute=30)
    assert task == "купить хлеб"
    assert _due("напомни завтра в 9 утра созвон")[0] == NOW.replace(hour=9) + datetime.timedelta(days=1)
    assert _due("напомни в 7 вечера тренировка")[0] == NOW.replace(hour=19)


def test_past_time_moves_to_next_day():
    assert _due("напомни в 8 утра зарядка")[0] == NOW.replace(hour=8) + datetime.timedelta(days=1)


def test_no_time():
    assert parse_when("напомни про отчёт", NOW) is None
