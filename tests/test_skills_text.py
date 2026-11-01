"""Проверки разбора фраз: калькулятор, выбор вариантов, исправление речи."""
import pytest

from commands.skills.calc import calculate
from commands.skills.fun import split_options
from nlu.speech_fix import fix_speech


@pytest.mark.parametrize("phrase,expected", [
    ("сколько будет пять плюс три", 8),
    ("сколько будет 25 умножить на 4", 100),
    ("посчитай 100 разделить на 8", 12.5),
    ("корень из 144", 12),
    ("15 процентов от 200", 30),
    ("сколько будет 2 в степени 10", 1024),
    ("вычисли десять минус двадцать", -10),
])
def test_calculate(phrase, expected):
    assert calculate(phrase) == pytest.approx(expected)


def test_calculate_rejects_garbage():
    with pytest.raises(ValueError):
        calculate("сколько будет открой стим")


def test_split_options_without_commas():
    known = {"доту", "роблокс", "майнкрафт", "геншин", "стим"}
    assert split_options("доту роблокс майнкрафт или геншин", known) == [
        "доту", "роблокс", "майнкрафт", "геншин"]
    assert split_options("пиццу или суши", known) == ["пиццу", "суши"]
    assert split_options("чай, кофе", known) == ["чай", "кофе"]


KNOWN = {"дискорд", "стим", "телеграм", "интеллиджей идея", "пай чарм", "роблокс"}


@pytest.mark.parametrize("heard,fixed", [
    ("включи дискомфорт", "включи дискорд"),
    ("открой дискорд", "открой дискорд"),
    ("включи звук", "включи звук"),
    ("включи музыку", "включи музыку"),
    ("открой блютуз", "открой блютуз"),
])
def test_fix_speech(heard, fixed):
    assert fix_speech(heard, [], KNOWN) == fixed


def test_fix_speech_uses_alternatives():
    assert fix_speech("включи степь", ["включи стим"], KNOWN) == "включи стим"
