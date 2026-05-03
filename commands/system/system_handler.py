import os
import subprocess


CLOSE_PREFIXES = ("закрой", "закрыть", "выключи", "останови", "завершить")


class SystemHandler:
    def __init__(self):
        self.commands = {
            "настройки":              lambda: os.system("start ms-settings:"),
            "панель управления":      lambda: os.system("start control"),
            "калькулятор":            lambda: subprocess.Popen("calc.exe", shell=True),
            "проводник":              lambda: os.system("start ."),
            "диспетчер задач":        lambda: os.system("start taskmgr"),
            "консоль":                lambda: os.system("start cmd"),
            "командная строка":       lambda: os.system("start cmd"),
            "терминал админа":        lambda: os.system("powershell Start-Process cmd -Verb RunAs"),
            "консоль администратора": lambda: os.system("powershell Start-Process cmd -Verb RunAs"),
            "установленные приложения": lambda: os.system("start ms-settings:appsfeatures"),
            "приложения":             lambda: os.system("start ms-settings:appsfeatures"),
            "удаление программ":      lambda: os.system("start appwiz.cpl"),
        }

    def execute(self, task: str) -> bool:
        task = task.lower().strip()

        if any(task.startswith(prefix) for prefix in CLOSE_PREFIXES):
            return False

        for cmd_name, action in self.commands.items():
            if cmd_name in task:
                action()
                return True
        return False