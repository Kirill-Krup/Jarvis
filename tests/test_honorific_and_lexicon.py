import random

import pytest

from core.honorific import soften
from commands.skills import all_skills, find_skill
from nlu import lexicon


def test_honorific_never_with_zero_chance():
    for _ in range(50):
        assert soften("Запускаю стим, сэр", "сэр", 0.0) == "Запускаю стим"


def test_honorific_always_with_full_chance():
    assert soften("Запускаю стим, сэр", "сэр", 1.0) == "Запускаю стим, сэр"


def test_honorific_is_occasional():
    random.seed(7)
    kept = sum(soften("Готово, сэр", "сэр", 0.25).endswith("сэр") for _ in range(400))
    assert 60 < kept < 140   # около 25 %


def test_honorific_keeps_only_one_in_multi_reply():
    text = "Запускаю дискорд, сэр. Запускаю стим, сэр"
    for _ in range(30):
        assert soften(text, "сэр", 1.0).count("сэр") == 1


def test_honorific_ignores_other_words():
    assert soften("Сэр, это сэрьёзно", "сэр", 0.0) == "Сэр, это сэрьёзно"


@pytest.mark.parametrize("spoken,expected", [
    ("интеллиджей идея", "idea"),
    ("интелиджи идея", "idea"),
    ("пай чарм", "pycharm"),
    ("роблокс", "roblox"),
    ("геншин импакт", "genshin"),
    ("андроид студио", "androidstudio"),
    ("ди эскорт", "discord"),
    ("дискомфорт", "discord"),
])
def test_lexicon_matches_spoken_names(spoken, expected):
    names = lexicon.builtin_names()
    found = lexicon.best_match(spoken, names, 75)
    assert found is not None, spoken
    assert names[found[0]] == expected


@pytest.mark.parametrize("spoken", ["музыку", "блютуз", "громкость", "сайт", "привет"])
def test_lexicon_ignores_unrelated_words(spoken):
    assert lexicon.best_match(spoken, lexicon.builtin_names(), 80) is None


@pytest.mark.parametrize("phrase", [
    "включи песню звери районы кварталы",
    "включи музыку для работы",
    "открой проект джарвис",
    "открой последний проект",
    "да или нет",
    "выбери число от 1 до 3",
    "я не знаю во что поиграть запусти мне доту роблокс майнкрафт или геншин",
    "напомни через 10 минут выпить воды",
    "поставь таймер на 5 минут",
    "сколько будет 5 плюс 3",
    "расскажи анекдот",
    "сколько заряда батареи",
])
def test_skills_match_target_phrases(phrase):
    assert find_skill(phrase) is not None, phrase


@pytest.mark.parametrize("phrase", [
    "включи дискорд", "открой телеграм", "закрой стим", "громкость 50",
    "какая погода", "сделай скриншот",
])
def test_skills_do_not_steal_regular_commands(phrase):
    assert find_skill(phrase) is None, phrase


def test_every_skill_has_examples_that_match_itself():
    for item in all_skills():
        assert item.examples, item.name
        assert any(item.matches(e.lower().replace(",", "")) for e in item.examples), item.name


@pytest.mark.parametrize("phrase", [
    "покажи где находится улица интернациональная 20",
    "где находится кафе пушкин",
    "покажи на карте вокзал",
    "где можно вкусно покушать",
    "где ближайшая аптека",
    "как добраться до вокзала",
    "проложи маршрут до улицы ленина 5",
    "покажи отзывы на кафе пушкин",
    "что пишут про айфон 15",
])
def test_maps_skills_match(phrase):
    assert find_skill(phrase) is not None, phrase
