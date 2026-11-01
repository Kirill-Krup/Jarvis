"""Навыки Джарвиса. Импорт модулей регистрирует их команды в реестре."""
from commands.skills import calc, dev, fun, maps, music, system_info, timers  # noqa: F401  (регистрируют навыки)
from commands.skills.registry import all_skills, find_skill  # noqa: F401
