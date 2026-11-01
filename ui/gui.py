import os
import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import subprocess

from config.autostart import enable_autostart, disable_autostart, is_autostart_enabled
from config.setup_wizard import (
    load_config, save_config,
    MUSIC_PLAYERS, MOVIE_SOURCES, ANIME_SOURCES, DEFAULT_CITIES
)
from config.profile_manager import ProfileManager
from config.audio_device_manager import AudioDeviceManager
from core.logging_utils import subscribe_log, unsubscribe_log, get_log_file_path, log
from commands import catalog, reminders
from commands.skills.dev import IDES
from core import notifier
from commands.todo_handler import (
    get_all_todos, add_todo, delete_todo_by_index,
    toggle_todo_by_index, clear_done, clear_all
)

try:
    import cv2
    from PIL import Image, ImageTk
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

_ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")


class SplashScreen:
    WIDTH  = 960
    HEIGHT = 540

    def __init__(self, root: tk.Tk):
        self._root    = root
        self._running = True
        self._photo   = None
        self._cap     = None
        self._root.withdraw()

        self._win = tk.Toplevel(self._root)
        self._win.overrideredirect(True)
        self._win.configure(bg="#000000")
        self._win.attributes("-topmost", True)

        sw = self._root.winfo_screenwidth()
        sh = self._root.winfo_screenheight()
        self._win.geometry(
            f"{self.WIDTH}x{self.HEIGHT}"
            f"+{(sw - self.WIDTH) // 2}+{(sh - self.HEIGHT) // 2}"
        )

        self._build_ui()
        self._win.update_idletasks()
        self._start_video()

    def _build_ui(self):
        self.canvas = tk.Canvas(
            self._win, width=self.WIDTH, height=self.HEIGHT,
            bg="#000000", highlightthickness=0,
        )
        self.canvas.place(x=0, y=0)

        self._video_item = self.canvas.create_image(0, 0, anchor="nw", tags="video_bg")

        self.canvas.create_text(
            self.WIDTH // 2, self.HEIGHT // 2 - 40,
            text="JARVIS", font=("Courier New", 110, "bold"),
            fill="#1c3352", tags="title",
        )
        self.canvas.create_text(
            self.WIDTH // 2, self.HEIGHT // 2 + 75,
            text="J . A . R . V . I . S",
            font=("Courier New", 14, "bold"),
            fill="#1e3d5a", tags="subtitle",
        )
        self.canvas.create_text(
            self.WIDTH // 2, self.HEIGHT // 2 + 100,
            text="Just A Rather Very Intelligent System",
            font=("Courier New", 10),
            fill="#132840", tags="tagline",
        )

        BOTTOM_H = 80
        bottom = tk.Frame(self._win, bg="#000000")
        bottom.place(x=0, y=self.HEIGHT - BOTTOM_H,
                     width=self.WIDTH, height=BOTTOM_H)
        bottom.lift()

        tk.Frame(bottom, bg="#0d2035", height=1).pack(fill="x")

        row = tk.Frame(bottom, bg="#000000")
        row.pack(fill="x", padx=30, pady=(8, 0))

        self._status_var = tk.StringVar(value="Инициализация...")
        tk.Label(
            row, textvariable=self._status_var,
            font=("Courier New", 9), fg="#2a5f82",
            bg="#000000", anchor="w",
        ).pack(side="left")

        self._percent_var = tk.StringVar(value="0 %")
        tk.Label(
            row, textvariable=self._percent_var,
            font=("Courier New", 11, "bold"), fg="#1a7fbf",
            bg="#000000", anchor="e",
        ).pack(side="right")

        style = ttk.Style(self._root)
        style.theme_use("default")
        style.configure(
            "Jarvis.Horizontal.TProgressbar",
            troughcolor="#060d16",
            background="#1a7fbf",
            darkcolor="#1a7fbf",
            lightcolor="#2a9fd6",
            bordercolor="#060d16",
            thickness=3,
        )

        self._progress = ttk.Progressbar(
            bottom, style="Jarvis.Horizontal.TProgressbar",
            orient="horizontal", mode="determinate",
            maximum=100,
        )
        self._progress.pack(fill="x", padx=30, pady=(6, 12))

    def update_progress(self, percent: int, text: str):
        self._percent_var.set(f"{percent} %")
        self._status_var.set(text)
        self._progress["value"] = percent
        self._win.update_idletasks()

    def _start_video(self):
        if not CV2_AVAILABLE:
            return
        path = os.path.normpath(os.path.join(_ASSETS, "backvid.mp4"))
        if not os.path.exists(path):
            return
        self._cap = cv2.VideoCapture(path)
        if self._cap.isOpened():
            self._next_frame()

    def _next_frame(self):
        if not self._running or self._cap is None:
            return
        ret, frame = self._cap.read()
        if not ret:
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self._cap.read()
            if not ret:
                return

        frame = cv2.resize(frame, (self.WIDTH, self.HEIGHT))
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        dim = frame.astype("float32") * 0.35
        frame = dim.clip(0, 255).astype("uint8")
        img = Image.fromarray(frame)
        self._photo = ImageTk.PhotoImage(image=img)
        self.canvas.itemconfig(self._video_item, image=self._photo)
        self.canvas.tag_lower(self._video_item)
        self._win.after(33, self._next_frame)

    def destroy(self):
        self._running = False
        if self._cap:
            self._cap.release()
        self._win.destroy()
        self._root.deiconify()


class MainWindow:
    def __init__(self, root: tk.Tk, profile_name: str,
                 honorific: str, on_exit=None, on_command=None,
                 listener=None, speaker=None):
        self.root = root
        self.on_exit = on_exit
        self.on_command = on_command
        self.listener = listener
        self.speaker = speaker
        self.audio_manager = AudioDeviceManager()

        self.root.title("JARVIS — Центр управления")
        self.root.geometry("1060x700")
        self.root.minsize(980, 620)
        self.root.configure(bg="#070d17")
        self.root.resizable(True, True)
        self.root.protocol("WM_DELETE_WINDOW", self.hide)

        self._log_filter = "ALL"
        self._autoscroll = tk.BooleanVar(value=True)
        self._log_entries = []

        self._build_ui(profile_name, honorific)
        subscribe_log(self._on_log_received)

    def _build_ui(self, name: str, honorific: str):
        self._status_var = tk.StringVar(value="")
        container = tk.Frame(self.root, bg="#070d17")
        container.pack(fill="both", expand=True)

        # Боковая панель
        sidebar = tk.Frame(container, bg="#040912", width=180)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        tk.Label(
            sidebar, text="J.A.R.V.I.S",
            font=("Courier New", 15, "bold"),
            fg="#1a7fbf", bg="#040912"
        ).pack(padx=16, pady=(16, 2), anchor="w")

        tk.Label(
            sidebar, text="Mark VII System",
            font=("Courier New", 8),
            fg="#2a5f82", bg="#040912"
        ).pack(padx=16, pady=(0, 10), anchor="w")

        tk.Frame(sidebar, bg="#0d2035", height=1).pack(fill="x", pady=(0, 10))

        content = tk.Frame(container, bg="#070d17")
        content.pack(side="left", fill="both", expand=True)

        self._pages = {}
        self._current_page = None

        # Создаем страницы
        self._pages["home"] = self._build_home_page(content)
        self._pages["todo"] = self._build_todo_page(content)
        self._pages["commands"] = self._build_commands_page(content)
        self._pages["settings"] = self._build_settings_page(content, name, honorific)
        self._pages["logs"] = self._build_logs_page(content)

        def add_nav_btn(text, icon, page_key):
            btn = tk.Button(
                sidebar, text=f"{icon} {text}",
                font=("Courier New", 9, "bold"),
                fg="#c3d4ff", bg="#040912",
                activeforeground="#ffffff",
                activebackground="#1a7fbf",
                relief="flat", anchor="w",
                command=lambda k=page_key: self.show_page(k),
                padx=14, pady=8,
            )
            btn.pack(fill="x", pady=1)
            return btn

        self._nav_buttons = {}
        self._nav_buttons["home"] = add_nav_btn("Монитор", "🎙️", "home")
        self._nav_buttons["todo"] = add_nav_btn("Список дел", "📋", "todo")
        self._nav_buttons["commands"] = add_nav_btn("База команд", "📖", "commands")
        self._nav_buttons["settings"] = add_nav_btn("Настройки", "⚙️", "settings")
        self._nav_buttons["logs"] = add_nav_btn("Логи", "📑", "logs")

        tk.Frame(sidebar, bg="#0d2035", height=1).pack(fill="x", pady=12)

        tk.Button(
            sidebar, text="❌ Выход",
            font=("Courier New", 9, "bold"),
            fg="#ff6b6b", bg="#040912",
            activeforeground="#ffffff",
            activebackground="#a12c2c",
            relief="flat", anchor="w",
            command=self.quit,
            padx=14, pady=8,
        ).pack(fill="x", side="bottom", pady=12)

        self.show_page("home")

    # ==========================================
    # 1. СТРАНИЦА: МОНИТОР РЕЧИ (HOME)
    # ==========================================
    def _build_home_page(self, parent: tk.Frame) -> tk.Frame:
        frame = tk.Frame(parent, bg="#070d17")

        top_bar = tk.Frame(frame, bg="#070d17")
        top_bar.pack(fill="x", padx=16, pady=(12, 6))

        tk.Label(
            top_bar, text="ГОЛОСОВОЙ МОНИТОР И СТАТУС",
            font=("Courier New", 12, "bold"),
            fg="#1a7fbf", bg="#070d17"
        ).pack(side="left")

        self._home_status = tk.StringVar(value="Системы в норме. Ожидаю голосовую команду...")
        tk.Label(
            top_bar, textvariable=self._home_status,
            font=("Courier New", 9, "bold"),
            fg="#38d39f", bg="#070d17"
        ).pack(side="right")

        tk.Frame(frame, bg="#0d2035", height=1).pack(fill="x", padx=16, pady=(0, 6))

        cards_frame = tk.Frame(frame, bg="#040912", highlightbackground="#0d2035", highlightthickness=1)
        cards_frame.pack(fill="x", padx=16, pady=4)

        row1 = tk.Frame(cards_frame, bg="#040912")
        row1.pack(fill="x", padx=12, pady=(6, 3))
        tk.Label(
            row1, text="🎙️ СЛЫШИТ (микрофон):",
            font=("Courier New", 9, "bold"), fg="#ffb86c", bg="#040912", width=22, anchor="w"
        ).pack(side="left")
        self._raw_heard_var = tk.StringVar(value="—")
        tk.Label(
            row1, textvariable=self._raw_heard_var,
            font=("Courier New", 10), fg="#f1fa8c", bg="#040912", anchor="w"
        ).pack(side="left", fill="x", expand=True)

        row2 = tk.Frame(cards_frame, bg="#040912")
        row2.pack(fill="x", padx=12, pady=3)
        tk.Label(
            row2, text="⚡ КОМАНДА:",
            font=("Courier New", 9, "bold"), fg="#50fa7b", bg="#040912", width=22, anchor="w"
        ).pack(side="left")
        self._executed_cmd_var = tk.StringVar(value="—")
        tk.Label(
            row2, textvariable=self._executed_cmd_var,
            font=("Courier New", 10, "bold"), fg="#ffffff", bg="#040912", anchor="w"
        ).pack(side="left", fill="x", expand=True)

        row3 = tk.Frame(cards_frame, bg="#040912")
        row3.pack(fill="x", padx=12, pady=(3, 6))
        tk.Label(
            row3, text="💬 ОТВЕТ ДЖАРВИСА:",
            font=("Courier New", 9, "bold"), fg="#8be9fd", bg="#040912", width=22, anchor="w"
        ).pack(side="left")
        self._jarvis_reply_var = tk.StringVar(value="—")
        tk.Label(
            row3, textvariable=self._jarvis_reply_var,
            font=("Courier New", 9), fg="#8be9fd", bg="#040912", anchor="w"
        ).pack(side="left", fill="x", expand=True)

        test_panel = tk.Frame(frame, bg="#070d17")
        test_panel.pack(fill="x", padx=16, pady=(8, 4))

        tk.Label(
            test_panel, text="ТЕСТОВОЕ ВЫПОЛНЕНИЕ КОМАНДЫ:",
            font=("Courier New", 8, "bold"), fg="#4e729a", bg="#070d17"
        ).pack(anchor="w", pady=(0, 2))

        input_row = tk.Frame(test_panel, bg="#070d17")
        input_row.pack(fill="x")

        self._manual_cmd_var = tk.StringVar()
        self._cmd_entry = tk.Entry(
            input_row, textvariable=self._manual_cmd_var,
            font=("Courier New", 10), bg="#040912", fg="#c3d4ff",
            insertbackground="#1a7fbf", relief="flat",
            highlightbackground="#0d2035", highlightthickness=1
        )
        self._cmd_entry.pack(side="left", fill="x", expand=True, padx=(0, 8), ipady=4)
        self._cmd_entry.bind("<Return>", lambda e: self._on_send_manual_cmd())

        tk.Button(
            input_row, text="Выполнить",
            font=("Courier New", 9, "bold"), fg="#ffffff", bg="#1a7fbf",
            activeforeground="#ffffff", activebackground="#0f5c8a",
            relief="flat", padx=14, pady=4,
            command=self._on_send_manual_cmd
        ).pack(side="right")

        quick_frame = tk.Frame(frame, bg="#070d17")
        quick_frame.pack(fill="x", padx=16, pady=(4, 6))

        quick_cmds = [
            ("🎵 Музыка", "включи музыку"),
            ("⛅ Погода", "какая погода"),
            ("📂 Проводник", "открой проводник"),
            ("🎬 Аниме", "хочу посмотреть аниме восхождение в тени"),
            ("💲 Доллар", "курс доллара"),
            ("📋 Задачи", "список дел"),
            ("⏸️ Пауза", "пауза"),
        ]
        for label, qcmd in quick_cmds:
            b = tk.Button(
                quick_frame, text=label,
                font=("Courier New", 8), fg="#c3d4ff", bg="#0a1628",
                activeforeground="#ffffff", activebackground="#1a7fbf",
                relief="flat", padx=6, pady=3,
                command=lambda c=qcmd: self._send_quick_cmd(c)
            )
            b.pack(side="left", padx=2)

        tk.Label(
            frame, text="ЖУРНАЛ ДЕЙСТВИЙ И РАСПОЗНАВАНИЯ:",
            font=("Courier New", 8, "bold"), fg="#4e729a", bg="#070d17"
        ).pack(anchor="w", padx=16, pady=(4, 2))

        history_frame = tk.Frame(frame, bg="#040912", highlightbackground="#0d2035", highlightthickness=1)
        history_frame.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        self._history_text = tk.Text(
            history_frame, bg="#040912", fg="#1a7fbf",
            font=("Courier New", 9), relief="flat", state="disabled",
            wrap="word", padx=10, pady=6,
        )
        sb = tk.Scrollbar(history_frame, command=self._history_text.yview, bg="#040912")
        self._history_text.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self._history_text.pack(side="left", fill="both", expand=True)

        return frame

    # ==========================================
    # 2. СТРАНИЦА: СПИСОК ДЕЛ (TO-DO)
    # ==========================================
    def _build_todo_page(self, parent: tk.Frame) -> tk.Frame:
        frame = tk.Frame(parent, bg="#070d17")

        top_bar = tk.Frame(frame, bg="#070d17")
        top_bar.pack(fill="x", padx=18, pady=(12, 6))

        tk.Label(
            top_bar, text="СПИСОК ДЕЛ И НАПОМИНАНИЯ",
            font=("Courier New", 13, "bold"),
            fg="#1a7fbf", bg="#070d17"
        ).pack(side="left")

        # Панель добавления задачи
        add_panel = tk.Frame(frame, bg="#040912", highlightbackground="#0d2035", highlightthickness=1)
        add_panel.pack(fill="x", padx=18, pady=6)

        self._new_todo_var = tk.StringVar()
        entry = tk.Entry(
            add_panel, textvariable=self._new_todo_var,
            font=("Courier New", 10), bg="#070d17", fg="#c3d4ff",
            insertbackground="#1a7fbf", relief="flat",
            highlightthickness=1, highlightbackground="#0d2035"
        )
        entry.pack(side="left", fill="x", expand=True, padx=8, pady=8, ipady=3)
        entry.bind("<Return>", lambda e: self._on_add_todo())

        tk.Button(
            add_panel, text="➕ Добавить дело",
            font=("Courier New", 9, "bold"), fg="#ffffff", bg="#1a7fbf",
            activebackground="#0f5c8a", activeforeground="#ffffff",
            relief="flat", padx=12, pady=5,
            command=self._on_add_todo
        ).pack(side="left", padx=(0, 8))

        # Панель напоминания
        remind_panel = tk.Frame(frame, bg="#070d17")
        remind_panel.pack(fill="x", padx=18, pady=4)

        tk.Label(
            remind_panel, text="⏰ Напомнить через:",
            font=("Courier New", 8, "bold"), fg="#4e729a", bg="#070d17"
        ).pack(side="left")

        self._remind_min_var = tk.StringVar(value="30")
        tk.Entry(
            remind_panel, textvariable=self._remind_min_var,
            font=("Courier New", 9), bg="#040912", fg="#1a7fbf",
            width=5, relief="flat", highlightthickness=1, highlightbackground="#0d2035"
        ).pack(side="left", padx=4)

        tk.Label(remind_panel, text="минут о:", font=("Courier New", 8), fg="#4e729a", bg="#070d17").pack(side="left")

        self._remind_task_var = tk.StringVar(value="выпить таблетку")
        tk.Entry(
            remind_panel, textvariable=self._remind_task_var,
            font=("Courier New", 9), bg="#040912", fg="#c3d4ff",
            relief="flat", highlightthickness=1, highlightbackground="#0d2035"
        ).pack(side="left", fill="x", expand=True, padx=4)

        tk.Button(
            remind_panel, text="Поставить таймер",
            font=("Courier New", 8, "bold"), fg="#ffffff", bg="#0a1628",
            activebackground="#1a7fbf", activeforeground="#ffffff",
            relief="flat", padx=8, pady=2,
            command=self._on_set_gui_reminder
        ).pack(side="left", padx=4)

        # Контейнер списка задач
        list_container = tk.Frame(frame, bg="#040912", highlightbackground="#0d2035", highlightthickness=1)
        list_container.pack(fill="both", expand=True, padx=18, pady=(6, 8))

        self._todo_canvas = tk.Canvas(list_container, bg="#040912", highlightthickness=0)
        todo_sb = tk.Scrollbar(list_container, command=self._todo_canvas.yview, bg="#040912")
        self._todo_canvas.configure(yscrollcommand=todo_sb.set)

        todo_sb.pack(side="right", fill="y")
        self._todo_canvas.pack(side="left", fill="both", expand=True)

        self._todo_scroll_frame = tk.Frame(self._todo_canvas, bg="#040912")
        self._todo_scroll_frame.bind(
            "<Configure>",
            lambda e: self._todo_canvas.configure(scrollregion=self._todo_canvas.bbox("all"))
        )
        self._todo_canvas.create_window((0, 0), window=self._todo_scroll_frame, anchor="nw")

        # Нижняя панель действий
        bottom_actions = tk.Frame(frame, bg="#070d17")
        bottom_actions.pack(fill="x", padx=18, pady=(0, 10))

        tk.Button(
            bottom_actions, text="🧹 Очистить выполненные",
            font=("Courier New", 8), fg="#c3d4ff", bg="#0a1628",
            relief="flat", padx=10, pady=4,
            command=self._on_clear_done_todos
        ).pack(side="left")

        tk.Button(
            bottom_actions, text="🗑️ Удалить все дела",
            font=("Courier New", 8), fg="#ff6b6b", bg="#0a1628",
            relief="flat", padx=10, pady=4,
            command=self._on_clear_all_todos
        ).pack(side="left", padx=8)

        tk.Button(
            bottom_actions, text="🔄 Обновить",
            font=("Courier New", 8), fg="#c3d4ff", bg="#0a1628",
            relief="flat", padx=10, pady=4,
            command=self._refresh_todo_list
        ).pack(side="right")

        return frame

    def _refresh_todo_list(self):
        for widget in self._todo_scroll_frame.winfo_children():
            widget.destroy()

        todos = get_all_todos()
        if not todos:
            tk.Label(
                self._todo_scroll_frame,
                text="Список дел пуст. Добавьте задачу выше или скажите: «Джарвис, добавь в список дел...»",
                font=("Courier New", 9), fg="#4e729a", bg="#040912"
            ).pack(pady=20, padx=16)
            return

        for idx, item in enumerate(todos):
            task_text = item.get("task", "")
            is_done = item.get("done", False)

            row = tk.Frame(self._todo_scroll_frame, bg="#070d17", highlightbackground="#0d2035", highlightthickness=1)
            row.pack(fill="x", padx=8, pady=3, expand=True)

            status_icon = "✅" if is_done else "⬜"
            toggle_btn = tk.Button(
                row, text=status_icon, font=("Courier New", 10),
                bg="#070d17", fg="#50fa7b" if is_done else "#c3d4ff",
                relief="flat", padx=4, pady=2,
                command=lambda i=idx: self._on_toggle_todo(i)
            )
            toggle_btn.pack(side="left", padx=4)

            text_color = "#4e729a" if is_done else "#c3d4ff"
            task_lbl = tk.Label(
                row, text=task_text, font=("Courier New", 9, "overstrike" if is_done else "normal"),
                fg=text_color, bg="#070d17", anchor="w"
            )
            task_lbl.pack(side="left", fill="x", expand=True, padx=4)

            del_btn = tk.Button(
                row, text="✕", font=("Courier New", 9, "bold"),
                bg="#070d17", fg="#ff6b6b", activebackground="#a12c2c",
                relief="flat", padx=6, pady=2,
                command=lambda i=idx: self._on_delete_todo(i)
            )
            del_btn.pack(side="right", padx=4)

    def _on_add_todo(self):
        t = self._new_todo_var.get().strip()
        if not t:
            return
        add_todo(t)
        self._new_todo_var.set("")
        self._refresh_todo_list()

    def _on_toggle_todo(self, idx: int):
        toggle_todo_by_index(idx)
        self._refresh_todo_list()

    def _on_delete_todo(self, idx: int):
        delete_todo_by_index(idx)
        self._refresh_todo_list()

    def _on_clear_done_todos(self):
        clear_done()
        self._refresh_todo_list()

    def _on_clear_all_todos(self):
        if messagebox.askyesno("Подтверждение", "Удалить все дела из списка?"):
            clear_all()
            self._refresh_todo_list()

    def _on_set_gui_reminder(self):
        task = self._remind_task_var.get().strip() or "Напоминание"
        mins = self._remind_min_var.get().strip()
        phrase = f"напомни через {mins} минут {task}"
        messagebox.showinfo("Напоминание", reminders.set_reminder(phrase))

    # ==========================================
    # 3. СТРАНИЦА: БАЗА КОМАНД (СПРАВКА)
    # ==========================================
    def _build_commands_page(self, parent: tk.Frame) -> tk.Frame:
        frame = tk.Frame(parent, bg="#070d17")

        top_bar = tk.Frame(frame, bg="#070d17")
        top_bar.pack(fill="x", padx=18, pady=(12, 6))
        tk.Label(
            top_bar, text="ЧТО УМЕЕТ JARVIS",
            font=("Courier New", 13, "bold"), fg="#1a7fbf", bg="#070d17"
        ).pack(side="left")

        self._cmd_search_var = tk.StringVar()
        search_entry = tk.Entry(
            top_bar, textvariable=self._cmd_search_var, width=28,
            font=("Courier New", 10), bg="#040912", fg="#c3d4ff",
            insertbackground="#1a7fbf", relief="flat",
            highlightthickness=1, highlightbackground="#0d2035", highlightcolor="#1a7fbf"
        )
        search_entry.pack(side="right", ipady=3)
        tk.Label(top_bar, text="🔍 Поиск:", font=("Courier New", 9),
                 fg="#4e729a", bg="#070d17").pack(side="right", padx=6)
        self._cmd_search_var.trace_add("write", lambda *_: self._render_catalog())

        tk.Label(
            frame, text="Нажмите на любую фразу, и Джарвис выполнит её. Голосом: скажите «Джарвис», затем фразу.",
            font=("Courier New", 8), fg="#4e729a", bg="#070d17", anchor="w"
        ).pack(fill="x", padx=18)

        container = tk.Frame(frame, bg="#040912", highlightbackground="#0d2035", highlightthickness=1)
        container.pack(fill="both", expand=True, padx=18, pady=(6, 12))

        self._cmd_canvas = tk.Canvas(container, bg="#040912", highlightthickness=0)
        sb = tk.Scrollbar(container, command=self._cmd_canvas.yview, bg="#040912")
        self._cmd_canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self._cmd_canvas.pack(side="left", fill="both", expand=True)

        self._cmd_inner = tk.Frame(self._cmd_canvas, bg="#040912")
        window_id = self._cmd_canvas.create_window((0, 0), window=self._cmd_inner, anchor="nw")
        self._cmd_inner.bind(
            "<Configure>", lambda e: self._cmd_canvas.configure(scrollregion=self._cmd_canvas.bbox("all")))
        self._cmd_canvas.bind(
            "<Configure>", lambda e: self._cmd_canvas.itemconfigure(window_id, width=e.width))
        self._cmd_canvas.bind(
            "<Enter>", lambda e: self._cmd_canvas.bind_all("<MouseWheel>", self._on_cmd_wheel))
        self._cmd_canvas.bind(
            "<Leave>", lambda e: self._cmd_canvas.unbind_all("<MouseWheel>"))

        self._render_catalog()
        return frame

    def _on_cmd_wheel(self, event):
        self._cmd_canvas.yview_scroll(int(-event.delta / 120), "units")

    def _render_catalog(self):
        for child in self._cmd_inner.winfo_children():
            child.destroy()

        categories = catalog.search(self._cmd_search_var.get())
        if not categories:
            tk.Label(self._cmd_inner, text="Ничего не найдено", font=("Courier New", 10),
                     fg="#4e729a", bg="#040912").pack(pady=20)
            return

        for category in categories:
            box = tk.Frame(self._cmd_inner, bg="#070d17", highlightbackground="#0d2035", highlightthickness=1)
            box.pack(fill="x", padx=12, pady=6)
            tk.Label(box, text=category.title, font=("Courier New", 10, "bold"),
                     fg="#1a7fbf", bg="#070d17").pack(anchor="w", padx=10, pady=(6, 2))

            for item in category.items:
                tk.Label(box, text=item.description, font=("Courier New", 9),
                         fg="#c3d4ff", bg="#070d17", justify="left", anchor="w",
                         wraplength=720).pack(fill="x", padx=14, pady=(6, 1))
                for example in item.examples:
                    tk.Button(
                        box, text=f"▶  «{example}»", anchor="w", justify="left",
                        font=("Courier New", 8), fg="#7fd1ff", bg="#0a1628",
                        activebackground="#1a7fbf", activeforeground="#ffffff",
                        relief="flat", padx=8, pady=2, cursor="hand2",
                        command=lambda text=example: self._send_quick_cmd(text)
                    ).pack(fill="x", padx=22, pady=1)
            tk.Frame(box, height=6, bg="#070d17").pack()

    # ==========================================
    # 4. СТРАНИЦА: РАСШИРЕННЫЕ НАСТРОЙКИ
    # ==========================================
    def _build_settings_page(self, parent: tk.Frame,
                             name: str, honorific: str) -> tk.Frame:
        frame = tk.Frame(parent, bg="#070d17")

        top_bar = tk.Frame(frame, bg="#070d17")
        top_bar.pack(fill="x", padx=18, pady=(12, 6))

        tk.Label(
            top_bar, text="ПАРАМЕТРЫ СИСТЕМЫ JARVIS",
            font=("Courier New", 13, "bold"),
            fg="#1a7fbf", bg="#070d17"
        ).pack(side="left")

        container = tk.Frame(frame, bg="#040912", highlightbackground="#0d2035", highlightthickness=1)
        container.pack(fill="both", expand=True, padx=18, pady=4)

        canvas = tk.Canvas(container, bg="#040912", highlightthickness=0)
        sb = tk.Scrollbar(container, command=canvas.yview, bg="#040912")
        canvas.configure(yscrollcommand=sb.set)

        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        scroll_frame = tk.Frame(canvas, bg="#040912")
        scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")

        cfg = load_config()

        def make_section(title):
            sec = tk.Frame(scroll_frame, bg="#070d17", highlightbackground="#0d2035", highlightthickness=1)
            sec.pack(fill="x", padx=14, pady=6)
            tk.Label(
                sec, text=title, font=("Courier New", 10, "bold"),
                fg="#1a7fbf", bg="#070d17"
            ).pack(anchor="w", padx=12, pady=(8, 6))
            return sec

        def add_setting_row(parent_sec, label_text, widget):
            r = tk.Frame(parent_sec, bg="#070d17")
            r.pack(fill="x", padx=12, pady=4)
            tk.Label(
                r, text=label_text, font=("Courier New", 9),
                fg="#c3d4ff", bg="#070d17", width=26, anchor="w"
            ).pack(side="left")
            widget.pack(side="left", fill="x", expand=True)

        # ---------------- СЕКЦИЯ 1: ПРОФИЛЬ И ГОРОД ----------------
        sec_profile = make_section("👤 ПРОФИЛЬ И МЕСТОПОЛОЖЕНИЕ")

        self._name_var = tk.StringVar(value=cfg.get("name", name))
        name_entry = tk.Entry(
            sec_profile, textvariable=self._name_var,
            font=("Courier New", 9), bg="#040912", fg="#1a7fbf",
            relief="flat", highlightthickness=1, highlightbackground="#0d2035"
        )
        add_setting_row(sec_profile, "Имя пользователя:", name_entry)

        self._honorific_var = tk.StringVar(value=cfg.get("honorific", honorific))
        honor_entry = tk.Entry(
            sec_profile, textvariable=self._honorific_var,
            font=("Courier New", 9), bg="#040912", fg="#1a7fbf",
            relief="flat", highlightthickness=1, highlightbackground="#0d2035"
        )
        add_setting_row(sec_profile, "Обращение:", honor_entry)

        self._city_var = tk.StringVar(value=cfg.get("city", "Москва"))
        city_cb = ttk.Combobox(
            sec_profile, textvariable=self._city_var,
            values=DEFAULT_CITIES, font=("Courier New", 9)
        )
        add_setting_row(sec_profile, "Город (для погоды):", city_cb)

        # ---------------- СЕКЦИЯ 2: ИСТОЧНИКИ МЕДИА И ПОИСКА ----------------
        sec_sources = make_section("🌐 ИСТОЧНИКИ КОНТЕНТА И ПОИСКА")

        self._music_player_var = tk.StringVar(value=cfg.get("music_player", "YouTube Music"))
        music_cb = ttk.Combobox(
            sec_sources, textvariable=self._music_player_var,
            values=list(MUSIC_PLAYERS.keys()), state="readonly", font=("Courier New", 9)
        )
        add_setting_row(sec_sources, "Плеер музыки:", music_cb)

        self._movie_source_var = tk.StringVar(value=cfg.get("movie_source", "KinoGo"))
        movie_cb = ttk.Combobox(
            sec_sources, textvariable=self._movie_source_var,
            values=list(MOVIE_SOURCES.keys()), state="readonly", font=("Courier New", 9)
        )
        add_setting_row(sec_sources, "Сайт для фильмов:", movie_cb)

        self._anime_source_var = tk.StringVar(value=cfg.get("anime_source", "AnimeGO"))
        anime_cb = ttk.Combobox(
            sec_sources, textvariable=self._anime_source_var,
            values=list(ANIME_SOURCES.keys()), state="readonly", font=("Courier New", 9)
        )
        add_setting_row(sec_sources, "Сайт для аниме:", anime_cb)

        self._map_labels = {"google": "Google Карты", "yandex": "Яндекс Карты"}
        self._map_var = tk.StringVar(value=self._map_labels.get(cfg.get("map_provider", "google"), "Google Карты"))
        add_setting_row(sec_sources, "Карты и отзывы:", ttk.Combobox(
            sec_sources, textvariable=self._map_var, values=list(self._map_labels.values()),
            state="readonly", font=("Courier New", 9)))

        # ---------------- СЕКЦИЯ 3: ЗВУК И МИКРОФОН ----------------
        sec_audio = make_section("🎧 ЗВУК, МИКРОФОН И КОНТЕКСТ")

        # Список микрофонов
        mic_devices = [d for d in self.audio_manager.get_all_devices() if d['is_input']]
        self._mic_options = [f"[{d['index']}] {d['name']}" for d in mic_devices]
        current_mic_idx = cfg.get("microphone_index")
        current_mic_label = self._mic_options[0] if self._mic_options else "По умолчанию"
        for opt in self._mic_options:
            if current_mic_idx is not None and opt.startswith(f"[{current_mic_idx}]"):
                current_mic_label = opt
                break

        self._mic_var = tk.StringVar(value=current_mic_label)
        mic_cb = ttk.Combobox(
            sec_audio, textvariable=self._mic_var,
            values=self._mic_options, state="readonly", font=("Courier New", 9)
        )
        add_setting_row(sec_audio, "Микрофон:", mic_cb)

        # Громкость голоса Джарвиса (системный звук не меняется)
        vol_frame = tk.Frame(sec_audio, bg="#070d17")
        vol_frame.pack(fill="x", padx=12, pady=4)
        tk.Label(
            vol_frame, text="Громкость голоса Джарвиса:", font=("Courier New", 9),
            fg="#c3d4ff", bg="#070d17", width=26, anchor="w"
        ).pack(side="left")

        self._vol_var = tk.IntVar(value=int(cfg.get("voice_volume", 100)))
        vol_slider = ttk.Scale(
            vol_frame, from_=0, to=100, variable=self._vol_var,
            orient="horizontal", command=self._on_volume_slider_change
        )
        vol_slider.pack(side="left", fill="x", expand=True, padx=8)
        vol_slider.bind("<ButtonRelease-1>", lambda e: self._preview_voice())

        self._vol_lbl = tk.Label(
            vol_frame, text=f"{self._vol_var.get()}%", font=("Courier New", 9, "bold"),
            fg="#1a7fbf", bg="#070d17", width=5
        )
        self._vol_lbl.pack(side="left")

        # Как часто добавлять «сэр»
        chance_frame = tk.Frame(sec_audio, bg="#070d17")
        chance_frame.pack(fill="x", padx=12, pady=4)
        tk.Label(
            chance_frame, text="Как часто говорить «сэр»:", font=("Courier New", 9),
            fg="#c3d4ff", bg="#070d17", width=26, anchor="w"
        ).pack(side="left")
        self._honor_chance_var = tk.IntVar(value=round(float(cfg.get("honorific_chance", 0.25)) * 100))
        ttk.Scale(
            chance_frame, from_=0, to=100, variable=self._honor_chance_var,
            orient="horizontal", command=self._on_honor_chance_change
        ).pack(side="left", fill="x", expand=True, padx=8)
        self._honor_chance_lbl = tk.Label(
            chance_frame, text=f"{self._honor_chance_var.get()}%", font=("Courier New", 9, "bold"),
            fg="#1a7fbf", bg="#070d17", width=5
        )
        self._honor_chance_lbl.pack(side="left")

        # Таймаут ожидания контекста
        timeout_frame = tk.Frame(sec_audio, bg="#070d17")
        timeout_frame.pack(fill="x", padx=12, pady=4)
        tk.Label(
            timeout_frame, text="Таймаут контекста (сек):", font=("Courier New", 9),
            fg="#c3d4ff", bg="#070d17", width=26, anchor="w"
        ).pack(side="left")

        self._context_timeout_var = tk.DoubleVar(value=float(cfg.get("context_timeout", 5.0)))
        timeout_slider = ttk.Scale(
            timeout_frame, from_=3.0, to=12.0, variable=self._context_timeout_var,
            orient="horizontal", command=self._on_timeout_slider_change
        )
        timeout_slider.pack(side="left", fill="x", expand=True, padx=8)

        self._timeout_lbl = tk.Label(
            timeout_frame, text=f"{int(self._context_timeout_var.get())}с",
            font=("Courier New", 9, "bold"), fg="#1a7fbf", bg="#070d17", width=5
        )
        self._timeout_lbl.pack(side="left")

        # Чувствительность VAD
        vad_frame = tk.Frame(sec_audio, bg="#070d17")
        vad_frame.pack(fill="x", padx=12, pady=4)
        tk.Label(
            vad_frame, text="Чувствительность VAD:", font=("Courier New", 9),
            fg="#c3d4ff", bg="#070d17", width=26, anchor="w"
        ).pack(side="left")

        self._vad_thresh_var = tk.DoubleVar(value=float(cfg.get("vad_threshold", 0.5)))
        vad_slider = ttk.Scale(
            vad_frame, from_=0.20, to=0.80, variable=self._vad_thresh_var,
            orient="horizontal", command=self._on_vad_thresh_change
        )
        vad_slider.pack(side="left", fill="x", expand=True, padx=8)

        self._vad_lbl = tk.Label(
            vad_frame, text=f"{self._vad_thresh_var.get():.2f}",
            font=("Courier New", 9, "bold"), fg="#1a7fbf", bg="#070d17", width=5
        )
        self._vad_lbl.pack(side="left")

        # Пауза конца речи (задержка перед отправкой команды)
        pause_frame = tk.Frame(sec_audio, bg="#070d17")
        pause_frame.pack(fill="x", padx=12, pady=4)
        tk.Label(
            pause_frame, text="Пауза конца речи (мс):", font=("Courier New", 9),
            fg="#c3d4ff", bg="#070d17", width=26, anchor="w"
        ).pack(side="left")

        self._silence_ms_var = tk.IntVar(value=int(cfg.get("silence_ms", 400)))
        pause_slider = ttk.Scale(
            pause_frame, from_=200, to=800, variable=self._silence_ms_var,
            orient="horizontal", command=self._on_silence_ms_change
        )
        pause_slider.pack(side="left", fill="x", expand=True, padx=8)

        self._pause_lbl = tk.Label(
            pause_frame, text=f"{self._silence_ms_var.get()}мс",
            font=("Courier New", 9, "bold"), fg="#1a7fbf", bg="#070d17", width=5
        )
        self._pause_lbl.pack(side="left")

        # Программное усиление микрофона (Gain)
        gain_frame = tk.Frame(sec_audio, bg="#070d17")
        gain_frame.pack(fill="x", padx=12, pady=4)
        tk.Label(
            gain_frame, text="Усиление микрофона (Gain):", font=("Courier New", 9),
            fg="#c3d4ff", bg="#070d17", width=26, anchor="w"
        ).pack(side="left")

        self._mic_gain_var = tk.DoubleVar(value=float(cfg.get("mic_gain", 1.0)))
        gain_slider = ttk.Scale(
            gain_frame, from_=0.8, to=2.5, variable=self._mic_gain_var,
            orient="horizontal", command=self._on_mic_gain_change
        )
        gain_slider.pack(side="left", fill="x", expand=True, padx=8)

        self._gain_lbl = tk.Label(
            gain_frame, text=f"{self._mic_gain_var.get():.1f}x",
            font=("Courier New", 9, "bold"), fg="#1a7fbf", bg="#070d17", width=5
        )
        self._gain_lbl.pack(side="left")

        # Кнопка быстрой автокалибровки шума
        cal_bar = tk.Frame(sec_audio, bg="#070d17")
        cal_bar.pack(fill="x", padx=12, pady=6)
        self._cal_btn = tk.Button(
            cal_bar, text="🎯 Автокалибровка микрофона (2 сек в тишине)",
            font=("Courier New", 8, "bold"),
            fg="#ffffff", bg="#2a3b5c", activebackground="#3d5584",
            relief="flat", padx=10, pady=4,
            command=self._on_run_calibration
        )
        self._cal_btn.pack(side="left")

        self._cal_status_lbl = tk.Label(
            cal_bar, text="", font=("Courier New", 8),
            fg="#50fa7b", bg="#070d17"
        )
        self._cal_status_lbl.pack(side="left", padx=10)

        # Модель распознавания речи (Vosk)
        model_dirs = [d for d in os.listdir(".") if os.path.isdir(d) and (d.startswith("model") or "vosk" in d.lower())]
        if not model_dirs:
            model_dirs = ["model_small"]
        self._vosk_model_var = tk.StringVar(value=cfg.get("vosk_model", model_dirs[0]))
        model_cb = ttk.Combobox(
            sec_audio, textvariable=self._vosk_model_var,
            values=model_dirs, state="readonly", font=("Courier New", 9)
        )
        add_setting_row(sec_audio, "Модель Vosk:", model_cb)

        # Подсказка по качеству и английскому языку
        tk.Label(
            sec_audio,
            text="💡 Подсказка: для распознавания сложных английских слов и треков положите\nполную модель (vosk-model-ru-0.42) в папку проекта и выберите её выше.",
            font=("Courier New", 7), fg="#4e729a", bg="#070d17", justify="left"
        ).pack(anchor="w", padx=12, pady=(2, 6))

        # ---------------- СЕКЦИЯ: НАПОМИНАНИЯ ----------------
        sec_notify = make_section("🔔 УВЕДОМЛЕНИЯ О НАПОМИНАНИЯХ")
        tk.Label(
            sec_notify,
            text="Напоминание всегда произносится голосом. Дополнительно оно придёт сюда:",
            font=("Courier New", 8), fg="#4e729a", bg="#070d17"
        ).pack(anchor="w", padx=12)

        self._notify_labels = {"pc": "Уведомление на компьютере", "telegram": "Сообщение в Telegram",
                               "both": "Компьютер и Telegram"}
        self._notify_var = tk.StringVar(
            value=self._notify_labels.get(cfg.get("notify_channel", "pc"), self._notify_labels["pc"]))
        add_setting_row(sec_notify, "Куда присылать:", ttk.Combobox(
            sec_notify, textvariable=self._notify_var, values=list(self._notify_labels.values()),
            state="readonly", font=("Courier New", 9)))

        entry_style = dict(font=("Courier New", 9), bg="#040912", fg="#1a7fbf", relief="flat",
                           highlightthickness=1, highlightbackground="#0d2035")
        self._tg_token_var = tk.StringVar(value=cfg.get("telegram_token", ""))
        add_setting_row(sec_notify, "Токен Telegram-бота:", tk.Entry(
            sec_notify, textvariable=self._tg_token_var, show="•", **entry_style))
        self._tg_chat_var = tk.StringVar(value=cfg.get("telegram_chat_id", ""))
        add_setting_row(sec_notify, "Chat ID:", tk.Entry(
            sec_notify, textvariable=self._tg_chat_var, **entry_style))

        notify_bar = tk.Frame(sec_notify, bg="#070d17")
        notify_bar.pack(fill="x", padx=12, pady=(2, 4))
        button_style = dict(font=("Courier New", 8, "bold"), fg="#ffffff", bg="#2a3b5c",
                            activebackground="#3d5584", relief="flat", padx=10, pady=4)
        tk.Button(notify_bar, text="🔎 Найти Chat ID", command=self._on_detect_chat_id,
                  **button_style).pack(side="left")
        tk.Button(notify_bar, text="📨 Проверить уведомление", command=self._on_test_notification,
                  **button_style).pack(side="left", padx=8)
        self._notify_status_lbl = tk.Label(notify_bar, text="", font=("Courier New", 8),
                                           fg="#50fa7b", bg="#070d17")
        self._notify_status_lbl.pack(side="left", padx=6)
        tk.Label(
            sec_notify,
            text="💡 Telegram: создайте бота у @BotFather, вставьте токен, напишите боту любое\nсообщение и нажмите «Найти Chat ID».",
            font=("Courier New", 7), fg="#4e729a", bg="#070d17", justify="left"
        ).pack(anchor="w", padx=12, pady=(2, 6))

        # ---------------- СЕКЦИЯ: РАЗРАБОТКА ----------------
        sec_dev = make_section("💻 РАЗРАБОТКА")
        projects_row = tk.Frame(sec_dev, bg="#070d17")
        self._projects_root_var = tk.StringVar(value=cfg.get("projects_root", ""))
        tk.Entry(projects_row, textvariable=self._projects_root_var, **entry_style).pack(
            side="left", fill="x", expand=True)
        tk.Button(projects_row, text="Обзор…", command=self._on_browse_projects,
                  **button_style).pack(side="left", padx=(6, 0))
        add_setting_row(sec_dev, "Папка с проектами:", projects_row)

        self._ide_titles = {i: spec["title"] for i, spec in IDES.items()}
        self._ide_var = tk.StringVar(value=self._ide_titles.get(cfg.get("default_ide", "idea"), "IntelliJ IDEA"))
        add_setting_row(sec_dev, "IDE по умолчанию:", ttk.Combobox(
            sec_dev, textvariable=self._ide_var, values=list(self._ide_titles.values()),
            state="readonly", font=("Courier New", 9)))
        tk.Label(
            sec_dev,
            text="💡 Скажите: «открой проект <название папки>» или «открой <проект> в идее».",
            font=("Courier New", 7), fg="#4e729a", bg="#070d17"
        ).pack(anchor="w", padx=12, pady=(2, 6))

        # ---------------- СЕКЦИЯ 4: СИСТЕМА ----------------
        sec_sys = make_section("⚙️ СИСТЕМА И АВТОЗАПУСК")

        self._autostart_var = tk.BooleanVar(
            value=bool(cfg.get("autostart", False)) or is_autostart_enabled()
        )
        chk = tk.Checkbutton(
            sec_sys,
            text="Запускать JARVIS вместе с Windows",
            variable=self._autostart_var,
            onvalue=True, offvalue=False,
            font=("Courier New", 9),
            fg="#c3d4ff", bg="#070d17",
            activeforeground="#ffffff", activebackground="#070d17",
            selectcolor="#040912", relief="flat", highlightthickness=0
        )
        chk.pack(anchor="w", padx=12, pady=4)

        # Кнопка сохранения
        bottom_bar = tk.Frame(frame, bg="#070d17")
        bottom_bar.pack(fill="x", padx=18, pady=10)

        self._save_status_var = tk.StringVar(value="")
        tk.Label(
            bottom_bar, textvariable=self._save_status_var,
            font=("Courier New", 9, "bold"), fg="#50fa7b", bg="#070d17"
        ).pack(side="left")

        tk.Button(
            bottom_bar, text="💾 Сохранить настройки",
            font=("Courier New", 10, "bold"),
            fg="#ffffff", bg="#1a7fbf",
            activeforeground="#ffffff", activebackground="#0f5c8a",
            relief="flat", padx=18, pady=6,
            command=self._save_all_settings
        ).pack(side="right")

        return frame

    def _on_volume_slider_change(self, val):
        pct = int(float(val))
        self._vol_lbl.config(text=f"{pct}%")
        ProfileManager().current["voice_volume"] = pct   # действует сразу

    def _preview_voice(self):
        if self.speaker:
            threading.Thread(
                target=lambda: self.speaker.speak("Так звучит мой голос", soften_honorific=False),
                daemon=True).start()

    def _on_honor_chance_change(self, val):
        pct = int(float(val))
        self._honor_chance_lbl.config(text=f"{pct}%")
        ProfileManager().current["honorific_chance"] = pct / 100

    def _on_browse_projects(self):
        folder = filedialog.askdirectory(title="Папка с вашими проектами")
        if folder:
            self._projects_root_var.set(folder)

    def _on_detect_chat_id(self):
        token = self._tg_token_var.get().strip()
        if not token:
            self._notify_status_lbl.config(text="Сначала вставьте токен", fg="#ff6b6b")
            return
        chat_id, error = notifier.detect_chat_id(token)
        if chat_id:
            self._tg_chat_var.set(chat_id)
            self._notify_status_lbl.config(text=f"Найден: {chat_id}", fg="#50fa7b")
        else:
            self._notify_status_lbl.config(text=error, fg="#ff6b6b")

    def _on_test_notification(self):
        channel = next((k for k, v in self._notify_labels.items() if v == self._notify_var.get()), "pc")
        if channel in ("pc", "both"):
            notifier.notify_pc("Джарвис", "Проверка уведомлений: всё работает")
        if channel in ("telegram", "both"):
            ok, error = notifier.notify_telegram(
                "Джарвис: проверка уведомлений",
                token=self._tg_token_var.get().strip(), chat_id=self._tg_chat_var.get().strip())
            self._notify_status_lbl.config(text="Отправлено" if ok else error,
                                           fg="#50fa7b" if ok else "#ff6b6b")
        else:
            self._notify_status_lbl.config(text="Отправлено", fg="#50fa7b")

    def _on_timeout_slider_change(self, val):
        sec = int(float(val))
        self._timeout_lbl.config(text=f"{sec}с")

    def _on_vad_thresh_change(self, val):
        v = round(float(val), 2)
        self._vad_lbl.config(text=f"{v:.2f}")
        if self.listener:
            self.listener.set_vad_params(threshold=v)

    def _on_silence_ms_change(self, val):
        ms = int(float(val))
        self._pause_lbl.config(text=f"{ms}мс")
        if self.listener:
            self.listener.set_vad_params(silence_ms=ms)

    def _on_mic_gain_change(self, val):
        g = round(float(val), 1)
        self._gain_lbl.config(text=f"{g:.1f}x")
        if self.listener:
            self.listener.set_vad_params(mic_gain=g)

    def _on_run_calibration(self):
        if not self.listener:
            messagebox.showinfo("Калибровка", "Модуль прослушивания ещё инициализируется...")
            return
        self._cal_status_lbl.config(text="Замеряю шум (тишина 2 сек)...", fg="#ffd166")
        self._cal_btn.config(state="disabled")

        def _cal_thread():
            res = self.listener.calibrate(duration_sec=2.2)
            def _apply():
                self._cal_btn.config(state="normal")
                if res.get("status") == "ok":
                    rec_thresh = res["threshold"]
                    rec_gain = res["gain"]
                    self._vad_thresh_var.set(rec_thresh)
                    self._vad_lbl.config(text=f"{rec_thresh:.2f}")
                    self._mic_gain_var.set(rec_gain)
                    self._gain_lbl.config(text=f"{rec_gain:.1f}x")
                    self._cal_status_lbl.config(text=f"Готово! Шум: {res['rms']}, Порог: {rec_thresh}", fg="#50fa7b")
                else:
                    self._cal_status_lbl.config(text="Не удалось получить аудиоданные", fg="#ff6b6b")
            self.root.after(0, _apply)

        threading.Thread(target=_cal_thread, daemon=True).start()

    def _save_all_settings(self):
        cfg = load_config()
        cfg["name"] = self._name_var.get().strip()
        cfg["honorific"] = self._honorific_var.get().strip()
        cfg["city"] = self._city_var.get().strip() or "Москва"
        cfg["music_player"] = self._music_player_var.get().strip()
        cfg["movie_source"] = self._movie_source_var.get().strip()
        cfg["anime_source"] = self._anime_source_var.get().strip()
        cfg["context_timeout"] = round(float(self._context_timeout_var.get()), 1)
        cfg["vad_threshold"] = round(float(self._vad_thresh_var.get()), 2)
        cfg["silence_ms"] = int(float(self._silence_ms_var.get()))
        cfg["mic_gain"] = round(float(self._mic_gain_var.get()), 1)
        cfg["vosk_model"] = self._vosk_model_var.get().strip()
        cfg["map_provider"] = next(
            (k for k, v in self._map_labels.items() if v == self._map_var.get()), "google")
        cfg["voice_volume"] = int(self._vol_var.get())
        cfg["honorific_chance"] = round(self._honor_chance_var.get() / 100, 2)
        cfg["notify_channel"] = next(
            (k for k, v in self._notify_labels.items() if v == self._notify_var.get()), "pc")
        cfg["telegram_token"] = self._tg_token_var.get().strip()
        cfg["telegram_chat_id"] = self._tg_chat_var.get().strip()
        cfg["projects_root"] = self._projects_root_var.get().strip()
        cfg["default_ide"] = next(
            (k for k, v in self._ide_titles.items() if v == self._ide_var.get()), "idea")

        # Применяем в listener
        if self.listener:
            self.listener.set_vad_params(
                threshold=cfg["vad_threshold"],
                silence_ms=cfg["silence_ms"],
                mic_gain=cfg["mic_gain"]
            )

        # Микрофон
        mic_str = self._mic_var.get()
        if mic_str.startswith("["):
            try:
                mic_idx = int(mic_str.split("]")[0].replace("[", ""))
                cfg["microphone_index"] = mic_idx
                if self.listener:
                    self.listener.switch_device(mic_idx)
            except Exception:
                pass

        # Автостарт
        cfg["autostart"] = bool(self._autostart_var.get())
        if cfg["autostart"]:
            enable_autostart()
        else:
            disable_autostart()

        save_config(cfg)
        self._save_status_var.set("✅ Настройки успешно сохранены и применены!")
        self.root.after(3000, lambda: self._save_status_var.set(""))

    # ==========================================
    # 5. СТРАНИЦА: РАСШИРЕННЫЕ ЛОГИ
    # ==========================================
    def _build_logs_page(self, parent: tk.Frame) -> tk.Frame:
        frame = tk.Frame(parent, bg="#070d17")

        top_bar = tk.Frame(frame, bg="#070d17")
        top_bar.pack(fill="x", padx=18, pady=(12, 6))

        tk.Label(
            top_bar, text="РАСШИРЕННЫЙ ЖУРНАЛ СОБЫТИЙ",
            font=("Courier New", 13, "bold"),
            fg="#1a7fbf", bg="#070d17"
        ).pack(side="left")

        # Панель фильтров
        filter_bar = tk.Frame(frame, bg="#070d17")
        filter_bar.pack(fill="x", padx=18, pady=4)

        tk.Label(
            filter_bar, text="Фильтр:", font=("Courier New", 8, "bold"),
            fg="#4e729a", bg="#070d17"
        ).pack(side="left", padx=(0, 4))

        self._filter_buttons = {}
        filter_defs = [
            ("ALL", "Все"),
            ("VOICE", "🎙️ Речь"),
            ("NLU", "🧠 Команды"),
            ("ACTION", "⚡ Действия"),
            ("SYSTEM", "⚙️ Система"),
            ("ERROR", "⚠️ Ошибки"),
        ]

        for k, lbl in filter_defs:
            btn = tk.Button(
                filter_bar, text=lbl,
                font=("Courier New", 8),
                fg="#ffffff" if k == "ALL" else "#c3d4ff",
                bg="#1a7fbf" if k == "ALL" else "#0a1628",
                relief="flat", padx=8, pady=2,
                command=lambda fk=k: self._set_log_filter(fk)
            )
            btn.pack(side="left", padx=2)
            self._filter_buttons[k] = btn

        # Чекбокс автопрокрутки
        tk.Checkbutton(
            filter_bar, text="Автопрокрутка", variable=self._autoscroll,
            font=("Courier New", 8), fg="#c3d4ff", bg="#070d17",
            activebackground="#070d17", activeforeground="#ffffff",
            selectcolor="#040912", relief="flat"
        ).pack(side="right")

        # Окно лога
        text_frame = tk.Frame(frame, bg="#040912", highlightbackground="#0d2035", highlightthickness=1)
        text_frame.pack(fill="both", expand=True, padx=18, pady=(4, 8))

        self._log = tk.Text(
            text_frame, bg="#040912", fg="#c3d4ff",
            font=("Courier New", 9), relief="flat",
            state="disabled", wrap="word",
            padx=10, pady=8,
        )

        # Цветовые теги
        self._log.tag_config("TIME", foreground="#4e729a")
        self._log.tag_config("INFO", foreground="#8be9fd")
        self._log.tag_config("VOICE", foreground="#f1fa8c")
        self._log.tag_config("NLU", foreground="#bd93f9")
        self._log.tag_config("ACTION", foreground="#50fa7b")
        self._log.tag_config("SYSTEM", foreground="#1a7fbf")
        self._log.tag_config("ERROR", foreground="#ff5555")

        sb = tk.Scrollbar(text_frame, command=self._log.yview, bg="#040912")
        self._log.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self._log.pack(side="left", fill="both", expand=True)

        # Нижняя панель действий логов
        log_actions = tk.Frame(frame, bg="#070d17")
        log_actions.pack(fill="x", padx=18, pady=(0, 10))

        tk.Button(
            log_actions, text="🗑️ Очистить",
            font=("Courier New", 8), fg="#ff6b6b", bg="#0a1628",
            relief="flat", padx=10, pady=4,
            command=self._clear_logs_ui
        ).pack(side="left")

        tk.Button(
            log_actions, text="💾 Экспорт в файл...",
            font=("Courier New", 8), fg="#c3d4ff", bg="#0a1628",
            relief="flat", padx=10, pady=4,
            command=self._export_logs
        ).pack(side="left", padx=8)

        tk.Button(
            log_actions, text="📂 Открыть файл логов",
            font=("Courier New", 8), fg="#c3d4ff", bg="#0a1628",
            relief="flat", padx=10, pady=4,
            command=self._open_log_file
        ).pack(side="left")

        return frame

    def _set_log_filter(self, filter_key: str):
        self._log_filter = filter_key
        for k, btn in self._filter_buttons.items():
            if k == filter_key:
                btn.configure(bg="#1a7fbf", fg="#ffffff")
            else:
                btn.configure(bg="#0a1628", fg="#c3d4ff")
        self._render_filtered_logs()

    def _render_filtered_logs(self):
        self._log.configure(state="normal")
        self._log.delete("1.0", "end")

        for timestamp, level, msg in self._log_entries:
            if self._log_filter != "ALL" and level != self._log_filter:
                continue

            self._log.insert("end", f"[{timestamp}] ", "TIME")
            self._log.insert("end", f"[{level}] ", level)
            self._log.insert("end", f"{msg}\n")

        self._log.configure(state="disabled")
        if self._autoscroll.get():
            self._log.see("end")

    def _on_log_received(self, timestamp: str, level: str, msg: str):
        entry = (timestamp, level, msg)
        self._log_entries.append(entry)
        if len(self._log_entries) > 2000:
            self._log_entries.pop(0)

        def _do():
            if self._log_filter == "ALL" or level == self._log_filter:
                self._log.configure(state="normal")
                self._log.insert("end", f"[{timestamp}] ", "TIME")
                self._log.insert("end", f"[{level}] ", level)
                self._log.insert("end", f"{msg}\n")
                self._log.configure(state="disabled")
                if self._autoscroll.get():
                    self._log.see("end")

        self.root.after(0, _do)

    def _clear_logs_ui(self):
        self._log_entries.clear()
        self._log.configure(state="normal")
        self._log.delete("1.0", "end")
        self._log.configure(state="disabled")

    def _export_logs(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("Log Files", "*.log")],
            title="Экспорт логов JARVIS"
        )
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    for ts, lvl, m in self._log_entries:
                        f.write(f"[{ts}] [{lvl}] {m}\n")
                messagebox.showinfo("Экспорт", "Логи успешно сохранены!")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось сохранить: {e}")

    def _open_log_file(self):
        path = get_log_file_path()
        if os.path.exists(path):
            try:
                os.startfile(path)
            except Exception:
                subprocess.Popen(["notepad.exe", path])
        else:
            messagebox.showinfo("Логи", "Файл логов пока пуст.")

    # ==========================================
    # ОБЩИЕ МЕТОДЫ И УПРАВЛЕНИЕ
    # ==========================================
    def show_page(self, key: str):
        for k, page in self._pages.items():
            page.place_forget()

        self._pages[key].place(relx=0, rely=0, relwidth=1, relheight=1)
        self._current_page = key

        for k, btn in self._nav_buttons.items():
            if k == key:
                btn.configure(fg="#1a7fbf", bg="#0a1628")
            else:
                btn.configure(fg="#c3d4ff", bg="#040912")

        if key == "todo":
            self._refresh_todo_list()

    def _on_send_manual_cmd(self):
        cmd = self._manual_cmd_var.get().strip()
        if not cmd:
            return
        self._manual_cmd_var.set("")
        if self.on_command:
            self.on_command(cmd)

    def _send_quick_cmd(self, cmd_text: str):
        self.show_page("home")
        if self.on_command:
            self.on_command(cmd_text)

    def update_speech_info(self, raw_text: str, command: str = ""):
        def _do():
            self._raw_heard_var.set(raw_text or "—")
            self._executed_cmd_var.set(command or "—")
            t_now = datetime.datetime.now().strftime("%H:%M:%S")
            self._append_history(f"[{t_now}] 🎙️ СЛЫШАЛ: '{raw_text}'  ->  КОМАНДА: '{command}'")
        self.root.after(0, _do)

    def update_execution_info(self, response: str, intent_info: str = ""):
        def _do():
            self._jarvis_reply_var.set(response or "—")
            t_now = datetime.datetime.now().strftime("%H:%M:%S")
            self._append_history(f"[{t_now}] 💬 ОТВЕТ: {response}")
        self.root.after(0, _do)

    def _append_history(self, line: str):
        self._history_text.configure(state="normal")
        self._history_text.insert("end", f"{line}\n")
        self._history_text.configure(state="disabled")
        self._history_text.see("end")

    def log(self, message: str):
        log(message)

    def set_status(self, text: str):
        self.root.after(0, lambda: self._status_var.set(f"▸  {text}"))

    def set_home_status(self, text: str):
        if hasattr(self, "_home_status"):
            self.root.after(0, lambda: self._home_status.set(text))

    def show(self):
        self.root.after(0, self._do_show)

    def _do_show(self):
        self.root.deiconify()
        self.root.lift()
        self.root.attributes("-topmost", True)
        self.root.focus_force()
        self.root.after(800, lambda: self.root.attributes("-topmost", False))

    def hide(self):
        self.root.withdraw()

    def quit(self):
        unsubscribe_log(self._on_log_received)
        if self.on_exit:
            self.on_exit()
