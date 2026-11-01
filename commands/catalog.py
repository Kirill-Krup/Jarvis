"""Каталог команд для вкладки «Команды»: что умеет Джарвис.

Навыки берутся прямо из реестра (commands.skills), поэтому список
возможностей не устаревает. Базовые команды описаны здесь.
"""
from dataclasses import dataclass, field

from commands.skills import all_skills


@dataclass
class CatalogItem:
    description: str
    examples: list[str] = field(default_factory=list)


@dataclass
class CatalogCategory:
    title: str
    items: list[CatalogItem]


BASE_CATEGORIES = [
    CatalogCategory("🖥 Программы и папки", [
        CatalogItem("Открыть или закрыть программу (понимает и русские, и английские названия)",
                    ["открой дискорд", "запусти интеллиджей идея", "закрой стим"]),
        CatalogItem("Открыть папку или сайт", ["открой папку загрузки", "открой сайт гитхаб", "открой рабочий стол"]),
        CatalogItem("Несколько действий в одной фразе (цепочки)",
                    ["открой ютуб и телеграм", "включи музыку и сделай громче", "закрой стим и дискорд"]),
    ]),
    CatalogCategory("🔊 Звук и медиа", [
        CatalogItem("Громкость компьютера", ["громкость 50", "громче", "тише", "выключи звук", "включи звук"]),
        CatalogItem("Управление воспроизведением", ["пауза", "продолжи", "следующий трек", "предыдущий трек"]),
        CatalogItem("Открыть музыкальный сервис", ["включи музыку"]),
        CatalogItem("Управление YouTube", ["полный экран", "перемотай вперёд", "перемотай назад"]),
    ]),
    CatalogCategory("🌐 Интернет", [
        CatalogItem("Поиск в Google и на YouTube",
                    ["загугли рецепт борща", "найди на ютубе уроки python", "найди видео про космос"]),
        CatalogItem("Погода и курсы валют",
                    ["какая погода", "какая завтра погода в самаре", "курс доллара"]),
        CatalogItem("Фильмы и аниме на выбранном в настройках сайте",
                    ["хочу посмотреть фильм интерстеллар", "посмотреть аниме наруто"]),
    ]),
    CatalogCategory("📋 Список дел", [
        CatalogItem("Вести список дел",
                    ["добавь в список дел купить хлеб", "список дел", "очисти список дел"]),
    ]),
    CatalogCategory("⚙️ Windows", [
        CatalogItem("Системные окна и утилиты",
                    ["открой диспетчер задач", "открой проводник", "открой калькулятор", "сделай скриншот"]),
        CatalogItem("Время и дата", ["который час", "какая дата"]),
        CatalogItem("Питание и блокировка (выключение — с подтверждением)",
                    ["заблокируй компьютер", "перезагрузи компьютер", "завершить работу", "отдыхай"]),
        CatalogItem("Bluetooth, Wi-Fi, точка доступа",
                    ["включи блютуз", "выключи вай фай", "включи точку доступа", "режим в самолёте"]),
    ]),
    CatalogCategory("🖼 Экраны и яркость", [
        CatalogItem("Режимы нескольких мониторов",
                    ["расширь экраны", "дублируй экраны", "только первый экран", "сколько мониторов"]),
        CatalogItem("Яркость", ["ярче", "темнее", "яркость 70", "яркость второго монитора 40"]),
    ]),
    CatalogCategory("🛡 Защита", [
        CatalogItem("Проверка на вирусы",
                    ["быстрая проверка", "полная проверка", "просканируй диск d", "останови сканирование"]),
    ]),
    CatalogCategory("💬 Разговор", [
        CatalogItem("Просто поболтать: Джарвис поддерживает беседу, делится мнением и задаёт вопросы "
                    "(лучше всего работает с установленной Ollama)",
                    ["а ты бы хотел чувствовать", "расскажи о себе", "мне скучно", "как дела"]),
    ]),
]


def get_catalog() -> list[CatalogCategory]:
    """Базовые команды + все зарегистрированные навыки, сгруппированные по категориям."""
    categories = list(BASE_CATEGORIES)
    by_title: dict[str, CatalogCategory] = {}
    for skill in all_skills():
        category = by_title.get(skill.category)
        if category is None:
            category = by_title[skill.category] = CatalogCategory(skill.category, [])
            categories.append(category)
        category.items.append(CatalogItem(skill.description, list(skill.examples)))
    return categories


def search(query: str) -> list[CatalogCategory]:
    """Категории, где что-то совпало с поисковой строкой (по описанию или примерам)."""
    query = query.lower().strip()
    if not query:
        return get_catalog()
    result = []
    for category in get_catalog():
        items = [i for i in category.items
                 if query in i.description.lower() or any(query in e.lower() for e in i.examples)
                 or query in category.title.lower()]
        if items:
            result.append(CatalogCategory(category.title, items))
    return result
