import random
import re


def handle_volume_up(cmd, ctx):
    ctx.volume_control.change_volume(+10)
    return ctx.reply(random.choice(["Звук увеличен", "Слушаюсь", "Готово"]))


def handle_volume_down(cmd, ctx):
    ctx.volume_control.change_volume(-10)
    return ctx.reply(random.choice(["Звук уменьшен", "Слушаюсь", "Готово"]))


def handle_mute(cmd, ctx):
    ctx.volume_control.mute()
    return ctx.reply("Аудиосистемы выключены")


def handle_unmute(cmd, ctx):
    ctx.volume_control.unmute()
    return ctx.reply("Аудиосистемы активированы")


def handle_volume_set(cmd, ctx):
    text = cmd.text_lower
    numbers = re.findall(r'\d+', text)
    if numbers:
        level = int(numbers[0])
        ctx.volume_control.set_volume(level)
        return ctx.reply(f"Устанавливаю громкость на {level} процентов")
    return ctx.reply("Укажите уровень громкости")