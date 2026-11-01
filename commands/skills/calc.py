"""Голосовой калькулятор: «сколько будет двадцать умножить на три»."""
import ast
import math
import operator
import re

from commands.skills.registry import skill

CATEGORY = "🧮 Вычисления"

_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod,
    ast.USub: operator.neg, ast.UAdd: operator.pos,
}
MAX_POWER = 1000

# порядок важен: длинные формулировки раньше коротких
_WORDS = [
    (r"(\d+(?:[.,]\d+)?)\s*процент(?:ов|а)?\s+от\s+(\d+(?:[.,]\d+)?)", r"(\1/100*\2)"),
    (r"(?:корень|корня)\s+(?:квадратный\s+)?из\s+(\d+(?:[.,]\d+)?)", r"sqrt(\1)"),
    (r"(\d+(?:[.,]\d+)?)\s+в\s+квадрате", r"(\1**2)"),
    (r"(\d+(?:[.,]\d+)?)\s+в\s+кубе", r"(\1**3)"),
    (r"в\s+степени", "**"),
    (r"умножить\s+на|умножь\s+на|помножить\s+на|умножить|\bх\b|\bx\b", "*"),
    (r"разделить\s+на|поделить\s+на|делить\s+на|разделить", "/"),
    (r"\bплюс\b", "+"), (r"\bминус\b", "-"),
    (r"остаток\s+от\s+деления\s+на", "%"),
]
_LEAD = re.compile(
    r"^(?:сколько\s+(?:будет|получится|это)|посчитай|подсчитай|вычисли|реши|сколько)\s*")
_ALLOWED = re.compile(r"^[\d\s+\-*/().,%sqrt]+$")


def _eval(node):
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        left, right = _eval(node.left), _eval(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > MAX_POWER:
            raise ValueError("слишком большая степень")
        return _OPS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.operand))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "sqrt" and len(node.args) == 1:
        return math.sqrt(_eval(node.args[0]))
    raise ValueError("неподдерживаемое выражение")


def to_expression(text: str) -> str:
    from nlu.numbers import ru_numbers_to_digits
    text = ru_numbers_to_digits(text.lower().strip())
    text = _LEAD.sub("", text)
    for pattern, repl in _WORDS:
        text = re.sub(pattern, repl, text)
    return text.replace(",", ".").strip()


def calculate(text: str):
    """Значение выражения из фразы. Бросает ValueError, если это не выражение."""
    expr = to_expression(text)
    if not expr or not re.search(r"\d", expr) or not _ALLOWED.match(expr.replace("**", "^").replace("^", "*")):
        raise ValueError("не выражение")
    return _eval(ast.parse(expr, mode="eval"))


def _format(value) -> str:
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return f"{value:.4f}".rstrip("0").rstrip(".").replace(".", ",")
    return str(value)


@skill(CATEGORY, "Посчитать пример: сложение, вычитание, умножение, деление, степень, корень, проценты",
       ["сколько будет 25 умножить на 4", "посчитай 100 разделить на 8",
        "корень из 144", "15 процентов от 200"],
       [r"^(?:сколько\s+(?:будет|получится)|посчитай|подсчитай|вычисли|реши)\s+\S",
        r"\bкорень\s+(?:квадратный\s+)?из\s+\d+", r"\d+\s*процент\w*\s+от\s+\d+"])
def calc_cmd(cmd, ctx):
    try:
        result = calculate(cmd.text_lower)
    except ZeroDivisionError:
        return ctx.reply("На ноль делить нельзя, даже мне")
    except (ValueError, SyntaxError, OverflowError):
        return ctx.reply("Не смог разобрать пример. Скажите, например: сколько будет пять плюс три")
    return ctx.reply(f"Получится {_format(result)}")
