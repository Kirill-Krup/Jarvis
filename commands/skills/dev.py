"""Навыки разработчика: запуск IDE и открытие проектов голосом."""
import glob
import json
import os
import re
import shutil
import subprocess

from commands.skills.registry import skill
from nlu import lexicon

CATEGORY = "💻 Разработка"
STATE_FILE = "config/dev_state.json"
PROJECT_MIN_SCORE = 70

LOCAL = os.environ.get("LOCALAPPDATA", "")
PROGRAM_FILES = [os.environ.get("ProgramFiles", "C:/Program Files"),
                 os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)")]

# id совпадает с id из config/basic_apps.py
IDES = {
    "idea": {"title": "IntelliJ IDEA", "cli": ["idea64", "idea"],
             "globs": [f"{LOCAL}/JetBrains/Toolbox/scripts/idea.cmd",
                       f"{LOCAL}/JetBrains/Toolbox/apps/*/ch-*/*/bin/idea64.exe",
                       f"{LOCAL}/Programs/IntelliJ*/bin/idea64.exe",
                       "{pf}/JetBrains/IntelliJ*/bin/idea64.exe"]},
    "pycharm": {"title": "PyCharm", "cli": ["pycharm64", "pycharm"],
                "globs": [f"{LOCAL}/JetBrains/Toolbox/scripts/pycharm.cmd",
                          f"{LOCAL}/JetBrains/Toolbox/apps/*/ch-*/*/bin/pycharm64.exe",
                          f"{LOCAL}/Programs/PyCharm*/bin/pycharm64.exe",
                          "{pf}/JetBrains/PyCharm*/bin/pycharm64.exe"]},
    "webstorm": {"title": "WebStorm", "cli": ["webstorm64", "webstorm"],
                 "globs": [f"{LOCAL}/JetBrains/Toolbox/scripts/webstorm.cmd",
                           f"{LOCAL}/JetBrains/Toolbox/apps/*/ch-*/*/bin/webstorm64.exe",
                           "{pf}/JetBrains/WebStorm*/bin/webstorm64.exe"]},
    "androidstudio": {"title": "Android Studio", "cli": ["studio64", "studio"],
                      "globs": ["{pf}/Android/Android Studio*/bin/studio64.exe",
                                f"{LOCAL}/Programs/Android Studio*/bin/studio64.exe"]},
    "vscode": {"title": "Visual Studio Code", "cli": ["code"],
               "globs": [f"{LOCAL}/Programs/Microsoft VS Code/bin/code.cmd",
                         "{pf}/Microsoft VS Code/bin/code.cmd"]},
    "cursor": {"title": "Cursor", "cli": ["cursor"],
               "globs": [f"{LOCAL}/Programs/cursor/resources/app/bin/cursor.cmd"]},
    "visualstudio": {"title": "Visual Studio", "cli": ["devenv"],
                     "globs": ["{pf}/Microsoft Visual Studio/*/*/Common7/IDE/devenv.exe"]},
}

# какую IDE предпочесть, по файлам проекта
PROJECT_MARKERS = [
    (("pubspec.yaml",), ["androidstudio", "vscode"]),
    (("pom.xml", "build.gradle", "build.gradle.kts"), ["idea", "androidstudio"]),
    (("pyproject.toml", "requirements.txt", "setup.py", "main.py"), ["pycharm", "vscode"]),
    (("package.json",), ["webstorm", "vscode", "cursor"]),
    (("*.sln", "*.csproj"), ["visualstudio"]),
]

_ide_cache: dict[str, str | None] = {}


# ------------------------------------------------------------------ IDE

def find_ide(ide_id: str) -> str | None:
    """Путь к запускаемому файлу IDE или None, если она не установлена."""
    if ide_id in _ide_cache:
        return _ide_cache[ide_id]
    spec = IDES.get(ide_id)
    path = None
    if spec:
        for name in spec["cli"]:
            path = shutil.which(name)
            if path:
                break
        if not path:
            for pattern in spec["globs"]:
                for pf in PROGRAM_FILES if "{pf}" in pattern else [""]:
                    hits = sorted(glob.glob(pattern.replace("{pf}", pf)), reverse=True)
                    if hits:
                        path = hits[0]
                        break
                if path:
                    break
    _ide_cache[ide_id] = path
    return path


def installed_ides() -> list[str]:
    return [i for i in IDES if find_ide(i)]


def _ide_from_text(text: str) -> str | None:
    """Определяет IDE по сказанному («в идее», «в пай чарме», «в вс коде»)."""
    text = text.strip()
    if not text:
        return None
    names = lexicon.builtin_names()
    found = lexicon.best_match(text, names, 80)
    if found and names[found[0]] in IDES:
        return names[found[0]]
    return None


def _ide_for_project(path: str, preferred: str | None, default: str) -> str | None:
    if preferred and find_ide(preferred):
        return preferred
    for markers, ides in PROJECT_MARKERS:
        if any(glob.glob(os.path.join(path, m)) for m in markers):
            for ide_id in ides:
                if find_ide(ide_id):
                    return ide_id
    if find_ide(default):
        return default
    return next(iter(installed_ides()), None)


# --------------------------------------------------------------- проекты

def list_projects(profile) -> dict[str, str]:
    """{название папки: путь} из папки проектов и списка projects в настройках."""
    projects: dict[str, str] = {}
    root = profile.projects_root
    if root and os.path.isdir(root):
        for entry in sorted(os.scandir(root), key=lambda e: e.name.lower()):
            if entry.is_dir() and not entry.name.startswith((".", "_")):
                projects[entry.name] = entry.path
    for name, path in (profile.current.get("projects") or {}).items():
        if os.path.isdir(path):
            projects[name] = path
    return projects


def find_project(spoken: str, projects: dict[str, str]) -> tuple[str, str] | None:
    spoken = spoken.strip()
    if not spoken:
        return None
    normalized = {re.sub(r"[-_.]+", " ", n).lower(): n for n in projects}
    found = lexicon.best_match(spoken, normalized, PROJECT_MIN_SCORE)
    if not found:
        return None
    name = normalized[found[0]]
    return name, projects[name]


def _load_state() -> dict:
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_state(state: dict):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def _launch_ide(ide_path: str, project_path: str | None = None):
    args = [ide_path] + ([project_path] if project_path else [])
    if ide_path.lower().endswith((".cmd", ".bat")):
        args = ["cmd", "/c"] + args
    flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
    subprocess.Popen(args, creationflags=flags, close_fds=True,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def open_project(name: str, path: str, ctx, ide_id: str | None = None) -> str:
    ide_id = _ide_for_project(path, ide_id, ctx.profile.default_ide)
    if not ide_id:
        os.startfile(path)
        return ctx.reply(f"IDE не найдена, открываю папку проекта {name}")
    _launch_ide(find_ide(ide_id), path)
    _save_state({"last_project": {"name": name, "path": path, "ide": ide_id}})
    return ctx.reply(f"Открываю проект {name} в {IDES[ide_id]['title']}")


# ---------------------------------------------------------------- навыки

_VERB = r"(?:открой|запусти|загрузи|подними|включи|покажи)"


@skill(CATEGORY, "Открыть проект из папки проектов в подходящей IDE",
       ["открой проект джарвис", "запусти проект калькулятор в идее",
        "загрузи проект сайт в вс коде"],
       [rf"^{_VERB}\s+(?:мой\s+)?проект\s+\S"], exclusive=True)
def open_project_cmd(cmd, ctx):
    m = re.match(rf"^{_VERB}\s+(?:мой\s+)?проект\s+(.+)$", cmd.text_lower)
    rest = m.group(1)
    ide_id = None
    in_ide = re.match(r"^(.+?)\s+в\s+(.+)$", rest)
    if in_ide and (ide := _ide_from_text(in_ide.group(2))):
        rest, ide_id = in_ide.group(1), ide

    if not ctx.profile.projects_root and not ctx.profile.current.get("projects"):
        return ctx.reply("Папка с проектами не задана. Укажите её в настройках, в разделе «Разработка»")
    found = find_project(rest, list_projects(ctx.profile))
    if not found:
        return ctx.reply(f"Не нашёл проект {rest}")
    return open_project(*found, ctx, ide_id)


@skill(CATEGORY, "Открыть любую программу или проект в конкретной IDE",
       ["открой джарвис в идее", "запусти бот в пайчарме"],
       [rf"^{_VERB}\s+.+\s+в\s+.+$"])
def open_in_ide_cmd(cmd, ctx):
    m = re.match(rf"^{_VERB}\s+(.+?)\s+в\s+(.+)$", cmd.text_lower)
    ide_id = _ide_from_text(m.group(2))
    if not ide_id:
        return None  # не про IDE: пусть обработают обычные команды
    projects = list_projects(ctx.profile)
    if not projects:
        return ctx.reply("Папка с проектами не задана. Укажите её в настройках, в разделе «Разработка»")
    found = find_project(m.group(1), projects)
    if not found:
        return ctx.reply(f"Не нашёл проект {m.group(1)}")
    return open_project(*found, ctx, ide_id)


@skill(CATEGORY, "Открыть проект, с которым работали в прошлый раз",
       ["открой последний проект", "продолжим работу над проектом"],
       [r"последний проект", r"продолж\w+ (?:работу|работать) над проектом"])
def open_last_project_cmd(cmd, ctx):
    last = _load_state().get("last_project")
    if not last or not os.path.isdir(last["path"]):
        return ctx.reply("Я ещё не открывал ваши проекты")
    return open_project(last["name"], last["path"], ctx, last.get("ide"))


@skill(CATEGORY, "Назвать проекты из папки проектов",
       ["какие у меня проекты", "список проектов"],
       [r"(?:какие|список|перечисли)\W+(?:у меня\W+)?проект"])
def list_projects_cmd(cmd, ctx):
    projects = list_projects(ctx.profile)
    if not projects:
        return ctx.reply("Проектов не нашёл. Укажите папку с проектами в настройках")
    names = list(projects)
    shown = ", ".join(names[:8])
    more = f" и ещё {len(names) - 8}" if len(names) > 8 else ""
    return ctx.reply(f"Проектов: {len(names)}. {shown}{more}")


@skill(CATEGORY, "Какие среды разработки установлены",
       ["какие у меня среды разработки", "какие ide установлены"],
       [r"какие\W+(?:у меня\W+)?(?:сред\w+ разработки|ide)"])
def list_ides_cmd(cmd, ctx):
    ides = [IDES[i]["title"] for i in installed_ides()]
    if not ides:
        return ctx.reply("Среды разработки не нашёл")
    return ctx.reply("Установлено: " + ", ".join(ides))
