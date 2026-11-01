"""Навыки напоминаний и таймеров."""
from commands import reminders, todo_handler
from commands.skills.registry import skill

CATEGORY = "⏰ Напоминания и таймеры"


@skill(CATEGORY,
       "Напомнить о деле через время или в заданный час (голосом и уведомлением на ПК или в Telegram)",
       ["напомни через 10 минут выпить воды", "напомни в 18:30 позвонить маме",
        "напомни завтра в 9 утра про созвон", "поставь таймер на 5 минут"],
       [r"^(?:мне\s+)?напомни", r"\bтаймер\s+(?:на\s+)?\d", r"поставь\s+таймер"],
       exclusive=True)
def set_reminder(cmd, ctx):
    text = cmd.text_lower
    if reminders.parse_when(text) is None and "таймер" not in text:
        # времени нет: просто запишем дело в список
        task = text
        for prefix in ("напомни мне", "напомни"):
            if task.startswith(prefix):
                task = task[len(prefix):].strip()
                break
        return ctx.reply(todo_handler.add_todo(task) if task
                         else "Не понял, о чём и когда напомнить")
    return ctx.reply(reminders.set_reminder(text))


@skill(CATEGORY, "Назвать запланированные напоминания",
       ["какие у меня напоминания", "покажи таймеры"],
       [r"(?:какие|список|покажи|перечисли)\W+(?:у меня\W+)?(?:напоминани|таймер)"])
def list_reminders(cmd, ctx):
    return ctx.reply(reminders.describe_reminders())


@skill(CATEGORY, "Отменить все напоминания и таймеры",
       ["отмени все напоминания", "сбрось таймер"],
       [r"(?:отмени|удали|сбрось|очисти)\W+(?:все\W+)?(?:напоминани|таймер)"])
def cancel_reminders(cmd, ctx):
    count = reminders.cancel_all()
    return ctx.reply(f"Отменил напоминаний: {count}" if count else "Отменять нечего")
