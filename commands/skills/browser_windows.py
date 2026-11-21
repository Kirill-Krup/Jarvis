"""Навыки управления вкладками браузера, активным окном и буфером обмена."""
import pyautogui
from commands.skills.registry import skill

CATEGORY = "📑 Вкладки и буфер обмена"


@skill(CATEGORY, "Открыть новую вкладку в браузере",
       ["новая вкладка", "открой новую вкладку", "создай вкладку"],
       [r"^(?:открой\s+|создай\s+)?новую?\s+вкладк\w*", r"^нов(?:ая|ую)\s+вкладк\w*"],
       exclusive=True)
def new_tab(cmd, ctx):
    pyautogui.hotkey("ctrl", "t")
    return ctx.reply("Открыл новую вкладку")


@skill(CATEGORY, "Закрыть текущую вкладку в браузере",
       ["закрой вкладку", "закрой эту вкладку", "закрой текущую вкладку"],
       [r"^закрой\w*\s+(?:эту\s+|текущую\s+)?вкладк\w*"],
       exclusive=True)
def close_tab(cmd, ctx):
    pyautogui.hotkey("ctrl", "w")
    return ctx.reply("Закрыл вкладку")


@skill(CATEGORY, "Восстановить случайно закрытую вкладку",
       ["верни вкладку", "восстанови вкладку", "открой закрытую вкладку"],
       [r"^(?:верни|восстанови|открой)\s+(?:закрытую\s+)?вкладк\w*"],
       exclusive=True)
def reopen_tab(cmd, ctx):
    pyautogui.hotkey("ctrl", "shift", "t")
    return ctx.reply("Восстановил закрытую вкладку")


@skill(CATEGORY, "Переключиться на следующую или предыдущую вкладку",
       ["следующая вкладка", "переключи вкладку", "предыдущая вкладка"],
       [r"^(?:следующая|переключи|предыдущая)\s+вкладк\w*"],
       exclusive=True)
def switch_tab(cmd, ctx):
    if "предыдущ" in cmd.text_lower:
        pyautogui.hotkey("ctrl", "shift", "tab")
        return ctx.reply("Предыдущая вкладка")
    pyautogui.hotkey("ctrl", "tab")
    return ctx.reply("Переключил вкладку")


@skill(CATEGORY, "Обновить страницу в браузере",
       ["обнови страницу", "перезагрузи страницу", "обнови сайт"],
       [r"^(?:обнови|перезагрузи)\s+(?:эту\s+)?(?:страницу|сайт|страничку)"],
       exclusive=True)
def refresh_page(cmd, ctx):
    pyautogui.hotkey("f5")
    return ctx.reply("Обновил страницу")


@skill(CATEGORY, "Закрыть текущее активное окно программы",
       ["закрой текущее окно", "закрой это окно", "закрой окно программы"],
       [r"^закрой\s+(?:текущее\s+|это\s+)?окно(?:\s+программы)?$"],
       exclusive=True)
def close_window(cmd, ctx):
    pyautogui.hotkey("alt", "f4")
    return ctx.reply("Закрыл активное окно")


@skill(CATEGORY, "Скопировать выделенный текст или объект",
       ["скопируй", "скопируй это", "скопируй текст"],
       [r"^скопируй(?:\s+(?:это|текст|выделенное))?$"],
       exclusive=True)
def copy_selection(cmd, ctx):
    pyautogui.hotkey("ctrl", "c")
    return ctx.reply("Скопировал")


@skill(CATEGORY, "Вставить текст из буфера обмена",
       ["вставь", "вставь сюда", "вставь текст"],
       [r"^вставь(?:\s+(?:сюда|текст))?$"],
       exclusive=True)
def paste_clipboard(cmd, ctx):
    pyautogui.hotkey("ctrl", "v")
    return ctx.reply("Вставил")


@skill(CATEGORY, "Выделить всё содержимое (текст или файлы)",
       ["выдели всё", "выделить всё", "выдели весь текст"],
       [r"^(?:выдели|выделить)\s+(?:всё|все|весь\s+текст)$"],
       exclusive=True)
def select_all(cmd, ctx):
    pyautogui.hotkey("ctrl", "a")
    return ctx.reply("Выделил всё")


@skill(CATEGORY, "Отменить последнее действие",
       ["отмени", "отмени действие", "отмени последнее действие"],
       [r"^отмени(?:\s+(?:действие|последнее\s+действие))?$"],
       exclusive=True)
def undo_action(cmd, ctx):
    pyautogui.hotkey("ctrl", "z")
    return ctx.reply("Отменил действие")
