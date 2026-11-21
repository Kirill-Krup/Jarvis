"""Управление окнами и вкладками Windows."""
import pyautogui
from commands.skills.registry import skill

pyautogui.FAILSAFE = False

CATEGORY = "🪟 Управление окнами"


@skill(CATEGORY, "Закрепить активное окно слева",
       ["окно влево", "прикрепи окно влево", "окно на левую половину"],
       [r"^окно\s+влево\b", r"прикрепи\s+окно\s+влево\b", r"окно\s+на\s+левую\s+половину\b"],
       exclusive=True)
def handle_snap_left(cmd, ctx):
    pyautogui.hotkey("win", "left")
    return ctx.reply("Окно закреплено на левой половине")


@skill(CATEGORY, "Закрепить активное окно справа",
       ["окно вправо", "прикрепи окно вправо", "окно на правую половину"],
       [r"^окно\s+вправо\b", r"прикрепи\s+окно\s+вправо\b", r"окно\s+на\s+правую\s+половину\b"],
       exclusive=True)
def handle_snap_right(cmd, ctx):
    pyautogui.hotkey("win", "right")
    return ctx.reply("Окно закреплено на правой половине")


@skill(CATEGORY, "Развернуть окно на весь экран",
       ["разверни окно", "окно на весь экран", "полный экран окна"],
       [r"^разверни\s+окно\b", r"^окно\s+на\s+весь\s+экран\b"],
       exclusive=True)
def handle_maximize(cmd, ctx):
    pyautogui.hotkey("win", "up")
    return ctx.reply("Окно развернуто")


@skill(CATEGORY, "Свернуть все окна и показать рабочий стол",
       ["сверни всё", "сверни все окна", "покажи рабочий стол"],
       [r"^сверни\s+(?:всё|все\s+окна)\b", r"^покажи\s+рабочий\s+стол\b"],
       exclusive=True)
def handle_minimize_all(cmd, ctx):
    pyautogui.hotkey("win", "d")
    return ctx.reply("Все окна свернуты")


@skill(CATEGORY, "Закрыть текущую вкладку в браузере или приложении",
       ["закрой вкладку", "закрой эту вкладку"],
       [r"^закрой\s+(?:эту\s+)?вкладку\b"],
       exclusive=True)
def handle_close_tab(cmd, ctx):
    pyautogui.hotkey("ctrl", "w")
    return ctx.reply("Вкладка закрыта")


@skill(CATEGORY, "Восстановить последнюю закрытую вкладку",
       ["верни вкладку", "открой закрытую вкладку", "восстанови вкладку"],
       [r"^(?:верни|открой|восстанови)\s+(?:закрытую\s+)?вкладку\b"],
       exclusive=True)
def handle_reopen_tab(cmd, ctx):
    pyautogui.hotkey("ctrl", "shift", "t")
    return ctx.reply("Восстановил закрытую вкладку")
