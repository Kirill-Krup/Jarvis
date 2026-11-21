"""Тесты распознавания музыкальных команд под сезоны, атмосферу, вайб и жанры."""
import re
from commands.skills.music import MOODS
from commands.skills.vibe_matcher import parse_vibe
from commands.skills.registry import find_skill


def test_mood_matching_autumn_winter():
    skill = find_skill("включи музыку под осень")
    assert skill is not None
    assert skill.name == "play_mood"

    skill_winter = find_skill("включи музыку под зиму")
    assert skill_winter is not None
    assert skill_winter.name == "play_mood"

    skill_rain = find_skill("музыка под дождь")
    assert skill_rain is not None
    assert skill_rain.name == "play_mood"

    skill_work = find_skill("включи музыку для работы")
    assert skill_work is not None
    assert skill_work.name == "play_mood"


def test_vibe_matcher_multi_attribute():
    # Лето + спокойное
    query, title = parse_vibe("хочу что-то под вайб лета, но при этом спокойное")
    assert "summer" in query and "chill" in query
    assert "спокойн" in title and "летн" in title

    # Осень + бодрое
    query2, title2 = parse_vibe("поставь что-нибудь под атмосферу осени, но бодрое")
    assert "autumn" in query2 and ("upbeat" in query2 or "energetic" in query2)
    assert "бодр" in title2 and "осенн" in title2

    # Фонк + тренировка
    query3, title3 = parse_vibe("поставь бодрый фонк для тренировки")
    assert "phonk" in query3 and "workout" in query3
    assert "фонк" in title3 and "тренировк" in title3

    # Грустный рок под дождь
    query4, title4 = parse_vibe("включи грустный рок под дождь")
    assert "rock" in query4 and "rain" in query4 and "sad" in query4
    assert "рок" in title4 and "дождь" in title4


def test_vibe_skill_dispatch():
    skill = find_skill("хочу что-то под вайб лета но при этом спокойное")
    assert skill is not None
    assert skill.name == "play_mood"

    skill2 = find_skill("включи музыку под вайб ночного города")
    assert skill2 is not None
    assert skill2.name == "play_mood"


def test_specific_songs_still_play_song():
    skill = find_skill("включи песню звери районы кварталы")
    assert skill is not None
    assert skill.name == "play_song"

    skill2 = find_skill("поставь трек numb")
    assert skill2 is not None
    assert skill2.name == "play_song"
