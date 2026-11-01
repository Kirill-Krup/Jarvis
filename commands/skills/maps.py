"""Карты и отзывы: адреса, маршруты, «где поесть рядом», отзывы на места и вещи."""
import re
import urllib.parse

from commands.skills.registry import skill
from config.setup_wizard import DEFAULT_CITIES
from core.browser import open_url

CATEGORY = "🗺 Карты и отзывы"

# что искать на карте по смыслу вопроса «где …»
NEARBY_TOPICS = [
    (r"поесть|покушать|пообедать|поужинать|позавтракать|перекусить|голодн|ресторан", "рестораны и кафе"),
    (r"кофе|кофейн", "кофейни"),
    (r"выпить|бар\b|паб\b", "бары"),
    (r"аптек|лекарств", "аптеки"),
    (r"заправ|бензин", "автозаправки"),
    (r"банкомат|снять деньги|наличные", "банкоматы"),
    (r"продукт|супермаркет|магазин", "продуктовые магазины"),
    (r"погулять|парк\b|прогуляться", "парки"),
    (r"кино|фильм посмотреть", "кинотеатры"),
    (r"отел|переночевать|гостиниц|хостел", "отели"),
    (r"туалет", "общественные туалеты"),
    (r"парковк|припарковаться", "парковки"),
    (r"шиномонтаж|автосервис|починить машину", "автосервисы"),
    (r"подстричься|парикмахер|барбер", "парикмахерские и барбершопы"),
    (r"спортзал|фитнес|качалк", "спортзалы"),
    (r"больниц|поликлиник|врач", "клиники и поликлиники"),
    (r"пицц", "пиццерии"),
    (r"суши|роллы", "суши и роллы"),
    (r"шаурм|бургер|фастфуд", "фастфуд"),
]
QUALITY_RE = re.compile(r"вкусно|хорош|лучш|отличн|годн|достойн")

# слова, по которым понятно, что это место, а не вещь
PLACE_WORDS = (
    "кафе", "ресторан", "бар", "паб", "кофейн", "столов", "пиццери", "суши", "бургерн", "магазин",
    "аптек", "клиник", "больниц", "поликлиник", "отел", "гостиниц", "хостел", "салон", "барбершоп",
    "парикмахер", "спортзал", "фитнес", "кинотеатр", "театр", "музей", "банк", "шиномонтаж",
    "автосервис", "стоматолог", "школ", "детский сад", "университет", "торговый центр", "трц",
    "парк", "заправк", "мойк", "кальянн", "караоке", "бассейн",
)

_TAIL = re.compile(r"\s+(?:пожалуйста|на карте|мне)$")
_NEAR_ME = re.compile(r"\b(?:рядом|поблизости|около меня|возле меня|недалеко|ближайш\w+)\b")


def _provider(profile) -> str:
    return str(profile.current.get("map_provider", "google"))


def _with_city(query: str, profile) -> str:
    """Дописывает город из настроек, если в запросе другого города нет."""
    low = query.lower()
    if any(city.lower()[:5] in low for city in DEFAULT_CITIES):
        return query
    return f"{query} {profile.city}"


def map_search_url(query: str, provider: str) -> str:
    q = urllib.parse.quote_plus(query)
    if provider == "yandex":
        return f"https://yandex.ru/maps/?text={q}"
    return f"https://www.google.com/maps/search/?api=1&query={q}"


def route_url(destination: str, provider: str) -> str:
    q = urllib.parse.quote_plus(destination)
    if provider == "yandex":
        return f"https://yandex.ru/maps/?rtext=~{q}&rtt=auto"
    return f"https://www.google.com/maps/dir/?api=1&destination={q}&travelmode=driving"


def _clean(text: str) -> str:
    return _TAIL.sub("", text.strip())


# ---------------------------------------------------------------- навыки

@skill(CATEGORY, "Показать адрес или место на карте",
       ["покажи где находится улица интернациональная 20", "где находится кафе пушкин",
        "покажи на карте вокзал", "открой карту"],
       [r"^(?:джарвис\s+)?(?:покажи|найди|открой)\s+(?:мне\s+)?(?:где\s+(?:находится|расположен\w*)|на карте)\s+\S",
        r"^где\s+(?:находится|расположен\w*)\s+\S", r"^(?:открой|покажи)\s+карту\b"],
       exclusive=True)
def show_on_map(cmd, ctx):
    text = cmd.text_lower
    m = re.search(r"(?:где\s+(?:находится|расположен\w*)|на карте)\s+(.+)$", text)
    provider = _provider(ctx.profile)
    if not m:  # просто «открой карту»
        open_url("https://yandex.ru/maps/" if provider == "yandex" else "https://www.google.com/maps")
        return ctx.reply("Открываю карту")
    place = _clean(m.group(1))
    open_url(map_search_url(_with_city(place, ctx.profile), provider))
    return ctx.reply(f"Показываю на карте: {place}")


@skill(CATEGORY, "Построить маршрут до места",
       ["как добраться до вокзала", "проложи маршрут до улицы ленина 5", "веди меня в кафе пушкин"],
       [r"^(?:как\s+(?:добраться|доехать|дойти|пройти)|проложи\s+маршрут|построй\s+маршрут|веди\s+меня|маршрут)\s+(?:до|в|на|к)?\s*\S"],
       exclusive=True)
def build_route(cmd, ctx):
    m = re.match(
        r"^(?:как\s+(?:добраться|доехать|дойти|пройти)|проложи\s+маршрут|построй\s+маршрут|веди\s+меня|маршрут)"
        r"\s*(?:до|в|на|к)?\s+(.+)$", cmd.text_lower)
    if not m:
        return ctx.reply("Куда построить маршрут?")
    destination = _clean(m.group(1))
    open_url(route_url(_with_city(destination, ctx.profile), _provider(ctx.profile)))
    return ctx.reply(f"Строю маршрут до {destination}. Отправная точка — ваше местоположение")


@skill(CATEGORY, "Найти места поблизости и показать метки на карте",
       ["где можно вкусно покушать", "где ближайшая аптека", "где выпить кофе рядом", "найди рядом заправку"],
       [r"^где\s+(?:тут\s+|здесь\s+)?(?:можно\s+|есть\s+|найти\s+|купить\s+)?(?:\w+\s+)?(?:" +
        "|".join(p for p, _ in NEARBY_TOPICS) + r")",
        r"^(?:найди|покажи)\s+(?:мне\s+)?(?:рядом|поблизости|ближайш\w+)\s+\S",
        r"^где\s+(?:тут\s+)?ближайш\w+\s+\S", r"^что\s+(?:есть\s+)?(?:интересного\s+)?(?:рядом|поблизости)"],
       exclusive=True)
def find_nearby(cmd, ctx):
    text = cmd.text_lower
    topic = next((q for pattern, q in NEARBY_TOPICS if re.search(pattern, text)), None)
    if topic is None:
        m = re.search(r"(?:рядом|поблизости|ближайш\w+)\s+(.+)$", text)
        topic = _clean(m.group(1)) if m else "интересные места"
    if QUALITY_RE.search(text):
        topic = f"лучшие {topic}"
    # без города: карта сама возьмёт ваше местоположение
    open_url(map_search_url(f"{topic} рядом", _provider(ctx.profile)))
    return ctx.reply(f"Показываю на карте: {topic} рядом с вами")


@skill(CATEGORY, "Открыть отзывы на заведение или вещь",
       ["покажи отзывы на кафе пушкин", "отзывы о айфон 15", "что пишут про ресторан меркурий",
        "какие отзывы на пылесос дайсон"],
       [r"\bотзыв\w*\s+(?:на|о|об|про)\s+\S", r"^что\s+(?:говорят|пишут)\s+(?:о|об|про)\s+\S",
        r"^(?:покажи|найди|открой)\s+отзывы\s+\S"],
       exclusive=True)
def show_reviews(cmd, ctx):
    text = cmd.text_lower
    m = (re.search(r"\bотзыв\w*\s+(?:на|о|об|про)\s+(.+)$", text)
         or re.search(r"(?:говорят|пишут)\s+(?:о|об|про)\s+(.+)$", text)
         or re.search(r"отзывы\s+(.+)$", text))
    subject = _clean(m.group(1)) if m else ""
    if not subject:
        return ctx.reply("Отзывы на что показать?")

    provider = _provider(ctx.profile)
    if any(w in subject for w in PLACE_WORDS):
        # заведение: карточка на карте с рейтингом и отзывами
        open_url(map_search_url(_with_city(subject, ctx.profile), provider))
        return ctx.reply(f"Открываю {subject} на карте. Отзывы и рейтинг в карточке места")
    q = urllib.parse.quote_plus(f"{subject} отзывы")
    open_url(f"https://yandex.ru/search/?text={q}" if provider == "yandex"
             else f"https://www.google.com/search?q={q}")
    return ctx.reply(f"Ищу отзывы: {subject}")
