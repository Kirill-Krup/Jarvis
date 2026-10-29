import random
import re
from nlu.numbers import ru_numbers_to_digits


def handle_volume_up(cmd, ctx):
    ctx.volume_control.change_volume(+10)
    return ctx.reply(random.choice(["Звук увеличен", "Слушаюсь", "Готово"]))


def handle_volume_down(cmd, ctx):
    ctx.volume_control.change_volume(-10)
    return ctx.reply(random.choice(["Звук уменьшен", "Слушаюсь", "Готово"]))


def handle_mute(cmd, ctx):
    # Сначала отвечаем голосом, и только ПОСЛЕ ответа выключаем звук
    reply_text = "Аудиосистемы выключены"
    ctx.speaker.speak(reply_text)
    ctx.volume_control.mute()
    return ""


def handle_unmute(cmd, ctx):
    ctx.volume_control.unmute()
    return ctx.reply("Аудиосистемы активированы")


def handle_volume_set(cmd, ctx):
    raw_text = cmd.text_lower
    # Преобразуем числительные словами в цифры («сто» -> «100», «пятьдесят» -> «50»)
    text = ru_numbers_to_digits(raw_text)

    # Проверка ключевых слов максимума и минимума
    if any(w in raw_text for w in ("максимум", "максимально", "на всю", "на полную", "на максимум", "полная", "максимальная")):
        level = 100
    elif any(w in raw_text for w in ("минимум", "минимально", "на минимум", "ноль", "нуль", "минимальная")):
        level = 0
    else:
        numbers = re.findall(r'\d+', text)
        if numbers:
            level = max(0, min(100, int(numbers[0])))
        else:
            return ctx.reply("Укажите уровень громкости")

    ctx.volume_control.set_volume(level)
    return ctx.reply(f"Устанавливаю громкость на {level} процентов")
