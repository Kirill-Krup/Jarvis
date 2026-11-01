"""Реестр навыков Джарвиса.

Навык — это команда, которая распознаётся по шаблонам (регулярным
выражениям) ещё до нейросетевого разбора намерений. Один и тот же реестр
используется для выполнения команд и для вкладки «Команды» в интерфейсе, так
что список возможностей всегда актуален.
"""
import re
from dataclasses import dataclass
from typing import Callable


@dataclass
class Skill:
    name: str
    category: str
    description: str
    examples: list[str]
    patterns: list[re.Pattern]
    handler: Callable
    exclusive: bool = False  # True: фразу нельзя дробить на несколько команд

    def matches(self, text: str) -> bool:
        return any(p.search(text) for p in self.patterns)


_REGISTRY: list[Skill] = []


def skill(category: str, description: str, examples: list[str],
          patterns: list[str], exclusive: bool = False):
    """Декоратор: регистрирует функцию (cmd, ctx) -> str как навык."""
    def decorator(func):
        _REGISTRY.append(Skill(
            name=func.__name__, category=category, description=description,
            examples=examples, handler=func, exclusive=exclusive,
            patterns=[re.compile(p) for p in patterns]))
        return func
    return decorator


def find_skill(text: str) -> Skill | None:
    for item in _REGISTRY:
        if item.matches(text):
            return item
    return None


def all_skills() -> list[Skill]:
    return list(_REGISTRY)
