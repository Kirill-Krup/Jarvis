"""Обращение («сэр») в конце фразы — только иногда, а не в каждой реплике."""
import random
import re

from config.profile_manager import ProfileManager


def soften(text: str, honorific: str | None = None, chance: float | None = None) -> str:
    """Убирает «, сэр» из текста; с вероятностью `chance` оставляет одно
    обращение в конце. Так речь звучит живее и не повторяет одно и то же."""
    if not text:
        return text
    profile = ProfileManager()
    honorific = honorific or profile.honorific
    chance = profile.honorific_chance if chance is None else chance
    if not honorific:
        return text

    pattern = re.compile(rf",\s*{re.escape(honorific)}(?!\w)", re.IGNORECASE)
    matches = list(pattern.finditer(text))
    if not matches:
        return text

    keep_last = random.random() < chance
    result, last_end = [], 0
    for i, m in enumerate(matches):
        result.append(text[last_end:m.start()])
        if keep_last and i == len(matches) - 1:
            result.append(m.group(0))
        last_end = m.end()
    result.append(text[last_end:])
    return "".join(result)
