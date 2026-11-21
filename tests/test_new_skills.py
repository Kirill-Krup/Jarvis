"""Тесты новых навыков: управление окнами/вкладками, буфером обмена и системными утилитами."""
from commands.skills.registry import find_skill


def test_browser_windows_skills_match():
    assert find_skill("новая вкладка").name == "new_tab"
    assert find_skill("открой новую вкладку").name == "new_tab"
    assert find_skill("закрой вкладку").name == "close_tab"
    assert find_skill("закрой эту вкладку").name == "close_tab"
    assert find_skill("верни вкладку").name == "reopen_tab"
    assert find_skill("восстанови вкладку").name == "reopen_tab"
    assert find_skill("следующая вкладка").name == "switch_tab"
    assert find_skill("предыдущая вкладка").name == "switch_tab"
    assert find_skill("обнови страницу").name == "refresh_page"
    assert find_skill("закрой текущее окно").name == "close_window"
    assert find_skill("скопируй").name == "copy_selection"
    assert find_skill("вставь").name == "paste_clipboard"
    assert find_skill("выдели всё").name == "select_all"
    assert find_skill("отмени действие").name == "undo_action"


def test_tools_skills_match():
    assert find_skill("проверь интернет").name == "check_ping"
    assert find_skill("проверь пинг").name == "check_ping"
    assert find_skill("какой мой ip").name == "get_ip"
    assert find_skill("очисти корзину").name == "empty_recycle_bin"
    assert find_skill("сгенерируй пароль").name == "generate_password"
    assert find_skill("открой терминал").name == "open_terminal"
    assert find_skill("открой блокнот").name == "open_notepad"
