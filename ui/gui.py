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


# =====================================================================
# ДИЗАЙН-СИСТЕМА (CYBER-HUD / ARC REACTOR PALETTE)
# =====================================================================
THEME = {
    "bg_root": "#080d16",        # Главный фон окна
    "bg_sidebar": "#05080f",     # Фон боковой панели
    "bg_card": "#0d1524",        # Фон карточек и панелей
    "bg_input": "#070b13",       # Фон полей ввода и терминала
    "bg_hover": "#131e33",       # Фон при наведении
    "border": "#1a2638",         # Границы блоков
    "border_focus": "#00d2ff",   # Граница в фокусе (Arc Cyan)

    "cyan": "#00d2ff",           # Главный акцент (Arc Cyan)
    "cyan_hover": "#38bdf8",     # Акцент при наведении
    "blue": "#3b82f6",           # Вторичный синий
    "emerald": "#10b981",        # Успех / Статус онлайн
    "amber": "#f59e0b",          # Предупреждение / Входящая речь
    "coral": "#ef4444",          # Ошибка / Удаление / Выход
    "purple": "#a855f7",         # NLU / Команды

    "text_main": "#f1f5f9",      # Основной текст (высокая чёткость)
    "text_sub": "#94a3b8",       # Вторичный текст
    "text_muted": "#64748b",     # Приглушённый текст / подписи
}

FONTS = {
    "title_large": ("Segoe UI", 15, "bold"),
    "title": ("Segoe UI", 12, "bold"),
    "subtitle": ("Segoe UI", 10, "bold"),
    "body": ("Segoe UI", 9),
    "body_bold": ("Segoe UI", 9, "bold"),
    "caption": ("Segoe UI", 8),
    "caption_bold": ("Segoe UI", 8, "bold"),
    "mono": ("Consolas", 9),
    "mono_bold": ("Consolas", 9, "bold"),
    "mono_small": ("Consolas", 8),
}


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
            text="JARVIS", font=("Segoe UI", 96, "bold"),
            fill="#122438", tags="title",
        )
        self.canvas.create_text(
            self.WIDTH // 2, self.HEIGHT // 2 + 70,
            text="J . A . R . V . I . S",
            font=("Segoe UI", 13, "bold"),
            fill="#00d2ff", tags="subtitle",
        )
        self.canvas.create_text(
            self.WIDTH // 2, self.HEIGHT // 2 + 96,
            text="Just A Rather Very Intelligent System",
            font=("Segoe UI", 9),
            fill="#64748b", tags="tagline",
        )

        BOTTOM_H = 75
        bottom = tk.Frame(self._win, bg="#05080f")
        bottom.place(x=0, y=self.HEIGHT - BOTTOM_H,
                     width=self.WIDTH, height=BOTTOM_H)
        bottom.lift()

        tk.Frame(bottom, bg=THEME["border"], height=1).pack(fill="x")

        row = tk.Frame(bottom, bg="#05080f")
        row.pack(fill="x", padx=32, pady=(10, 0))

        self._status_var = tk.StringVar(value="Инициализация систем...")
        tk.Label(
            row, textvariable=self._status_var,
            font=FONTS["body_bold"], fg=THEME["cyan"], bg="#05080f",
        ).pack(side="left")

        self._pct_var = tk.StringVar(value="0%")
        tk.Label(
            row, textvariable=self._pct_var,
            font=FONTS["body_bold"], fg=THEME["text_sub"], bg="#05080f",
        ).pack(side="right")

        prog_bg = tk.Frame(bottom, bg=THEME["border"], height=4)
        prog_bg.pack(fill="x", padx=32, pady=(6, 0))
        prog_bg.pack_propagate(False)

        self._bar = tk.Frame(prog_bg, bg=THEME["cyan"], height=4, width=0)
        self._bar.place(x=0, y=0, relheight=1.0, width=0)
        self._prog_total_w = self.WIDTH - 64

    def update_progress(self, percent: int, text: str):
        if not self._running:
            return
        self._status_var.set(text)
        self._pct_var.set(f"{percent}%")
        new_w = int(self._prog_total_w * percent / 100)
        self._bar.place_configure(width=new_w)
        self._win.update_idletasks()

    def update_status(self, text: str, pct: int = 0):
        self.update_progress(pct, text)

    def _start_video(self):
        if not CV2_AVAILABLE:
            self._load_fallback_bg()
            return
        video_path = os.path.join(_ASSETS, "jarvice_splash.mp4")
        if not os.path.exists(video_path):
            self._load_fallback_bg()
            return

        try:
            self._cap = cv2.VideoCapture(video_path)
            if not self._cap.isOpened():
                self._load_fallback_bg()
                return
            self._next_frame()
        except Exception:
            self._load_fallback_bg()

    def _load_fallback_bg(self):
        img_path = os.path.join(_ASSETS, "jarvice_bg.png")
        if os.path.exists(img_path) and CV2_AVAILABLE:
            try:
                img = Image.open(img_path).resize((self.WIDTH, self.HEIGHT))
                self._photo = ImageTk.PhotoImage(img)
                self.canvas.itemconfig(self._video_item, image=self._photo)
                self.canvas.tag_lower(self._video_item)
            except Exception:
                pass

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

        self.root.title("JARVIS — Центр управления Mark VII")
        self.root.geometry("1080x720")
        self.root.minsize(980, 640)
        self.root.configure(bg=THEME["bg_root"])
        self.root.resizable(True, True)
        self.root.protocol("WM_DELETE_WINDOW", self.hide)

        self._setup_ttk_styles()

        self._log_filter = "ALL"
        self._autoscroll = tk.BooleanVar(value=True)
        self._log_entries = []

        self._build_ui(profile_name, honorific)
        subscribe_log(self._on_log_received)

    def _setup_ttk_styles(self):
        """Настройка темного стиля для выпадающих списков и слайдеров."""
        self.style = ttk.Style()
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

        # Выпадающие списки (Combobox)
        self.style.configure(
            "TCombobox",
            fieldbackground=THEME["bg_input"],
            background=THEME["bg_card"],
            foreground=THEME["text_main"],
            darkcolor=THEME["border"],
            lightcolor=THEME["border"],
            bordercolor=THEME["border"],
            arrowcolor=THEME["cyan"],
            arrowsize=12,
            padding=5,
        )
        self.style.map(
            "TCombobox",
            fieldbackground=[("readonly", THEME["bg_input"])],
            foreground=[("readonly", THEME["text_main"])],
            selectbackground=[("readonly", THEME["bg_hover"])],
            selectforeground=[("readonly", THEME["cyan"])],
        )

        # Ползунки (Scale)
        self.style.configure(
            "Horizontal.TScale",
            troughcolor=THEME["bg_input"],
            background=THEME["cyan"],
            bordercolor=THEME["border"],
            lightcolor=THEME["cyan"],
            darkcolor=THEME["cyan"],
        )

        # Скроллбары (Scrollbar)
        self.style.configure(
            "Vertical.TScrollbar",
            troughcolor=THEME["bg_root"],
            background=THEME["bg_card"],
            bordercolor=THEME["bg_root"],
            arrowcolor=THEME["text_muted"],
        )

    def _build_ui(self, name: str, honorific: str):
        self._status_var = tk.StringVar(value="")
        container = tk.Frame(self.root, bg=THEME["bg_root"])
        container.pack(fill="both", expand=True)

        # ---------------- БОКОВАЯ ПАНЕЛЬ (SIDEBAR) ----------------
        sidebar = tk.Frame(container, bg=THEME["bg_sidebar"], width=195)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        # Разделитель между панелью и контентом
        sep_side = tk.Frame(container, bg=THEME["border"], width=1)
        sep_side.pack(side="left", fill="y")

        # Логотип и статус системы
        brand_frame = tk.Frame(sidebar, bg=THEME["bg_sidebar"])
        brand_frame.pack(fill="x", padx=16, pady=(18, 12))

        tk.Label(
            brand_frame, text="J . A . R . V . I . S",
            font=FONTS["title_large"],
            fg=THEME["cyan"], bg=THEME["bg_sidebar"]
        ).pack(anchor="w")

        sub_row = tk.Frame(brand_frame, bg=THEME["bg_sidebar"])
        sub_row.pack(fill="x", pady=(2, 0))

        tk.Label(
            sub_row, text="MARK VII",
            font=FONTS["caption_bold"],
            fg=THEME["text_muted"], bg=THEME["bg_sidebar"]
        ).pack(side="left")

        tk.Label(
            sub_row, text="● ONLINE",
            font=FONTS["caption_bold"],
            fg=THEME["emerald"], bg=THEME["bg_sidebar"]
        ).pack(side="right")

        tk.Frame(sidebar, bg=THEME["border"], height=1).pack(fill="x", padx=14, pady=(0, 10))

        # Контентная область
        content = tk.Frame(container, bg=THEME["bg_root"])
        content.pack(side="left", fill="both", expand=True)

        self._pages = {}
        self._current_page = None

        # Создаем страницы
        self._pages["home"] = self._build_home_page(content)
        self._pages["todo"] = self._build_todo_page(content)
        self._pages["commands"] = self._build_commands_page(content)
        self._pages["settings"] = self._build_settings_page(content, name, honorific)
        self._pages["logs"] = self._build_logs_page(content)

        # Навигационные кнопки
        def add_nav_btn(text, icon, page_key):
            btn = tk.Button(
                sidebar, text=f"  {icon}  {text}",
                font=FONTS["body_bold"],
                fg=THEME["text_sub"], bg=THEME["bg_sidebar"],
                activeforeground=THEME["cyan"],
                activebackground=THEME["bg_hover"],
                relief="flat", anchor="w",
                cursor="hand2",
                command=lambda k=page_key: self.show_page(k),
                padx=10, pady=9,
            )
            btn.pack(fill="x", padx=10, pady=2)
            return btn

        self._nav_buttons = {}
        self._nav_buttons["home"] = add_nav_btn("Монитор", "🎙️", "home")
        self._nav_buttons["todo"] = add_nav_btn("Список дел", "📋", "todo")
        self._nav_buttons["commands"] = add_nav_btn("База команд", "📖", "commands")
        self._nav_buttons["settings"] = add_nav_btn("Настройки", "⚙️", "settings")
        self._nav_buttons["logs"] = add_nav_btn("Логи", "📑", "logs")

        # Нижняя плашка выхода
        exit_frame = tk.Frame(sidebar, bg=THEME["bg_sidebar"])
        exit_frame.pack(side="bottom", fill="x", pady=14, padx=10)

        tk.Frame(sidebar, bg=THEME["border"], height=1).pack(side="bottom", fill="x", padx=14, pady=(0, 10))

        tk.Button(
            exit_frame, text="  ✕  Выход",
            font=FONTS["body_bold"],
            fg=THEME["coral"], bg=THEME["bg_sidebar"],
            activeforeground="#ffffff",
            activebackground="#5c1d1d",
            relief="flat", anchor="w",
            cursor="hand2",
            command=self.quit,
            padx=10, pady=8,
        ).pack(fill="x")

        self.show_page("home")

    # ==========================================
    # 1. СТРАНИЦА: МОНИТОР РЕЧИ (HOME)
    # ==========================================
    def _build_home_page(self, parent: tk.Frame) -> tk.Frame:
        frame = tk.Frame(parent, bg=THEME["bg_root"])

        # Верхняя панель заголовка
        top_bar = tk.Frame(frame, bg=THEME["bg_root"])
        top_bar.pack(fill="x", padx=20, pady=(16, 8))

        tk.Label(
            top_bar, text="ГОЛОСОВОЙ МОНИТОР",
            font=FONTS["title"],
            fg=THEME["cyan"], bg=THEME["bg_root"]
        ).pack(side="left")

        self._home_status = tk.StringVar(value="Системы в норме. Ожидаю голосовую команду...")
        status_pill = tk.Frame(top_bar, bg=THEME["bg_card"], highlightbackground=THEME["border"], highlightthickness=1)
        status_pill.pack(side="right")
        tk.Label(
            status_pill, text="●",
            font=FONTS["caption_bold"],
            fg=THEME["emerald"], bg=THEME["bg_card"]
        ).pack(side="left", padx=(8, 2), pady=3)
        tk.Label(
            status_pill, textvariable=self._home_status,
            font=FONTS["caption_bold"],
            fg=THEME["text_sub"], bg=THEME["bg_card"]
        ).pack(side="left", padx=(0, 8), pady=3)

        tk.Frame(frame, bg=THEME["border"], height=1).pack(fill="x", padx=20, pady=(0, 10))

        # 3 Карточки телеметрии (СЛЫШИТ, КОМАНДА, ОТВЕТ)
        cards_container = tk.Frame(frame, bg=THEME["bg_root"])
        cards_container.pack(fill="x", padx=20, pady=(0, 8))

        def make_telemetry_card(parent_box, icon, title, text_var, val_color):
            card = tk.Frame(parent_box, bg=THEME["bg_card"], highlightbackground=THEME["border"], highlightthickness=1)
            card.pack(fill="x", pady=4)

            head_row = tk.Frame(card, bg=THEME["bg_card"])
            head_row.pack(fill="x", padx=14, pady=(8, 2))
            tk.Label(
                head_row, text=f"{icon}  {title}",
                font=FONTS["caption_bold"], fg=THEME["text_muted"], bg=THEME["bg_card"]
            ).pack(side="left")

            body_row = tk.Frame(card, bg=THEME["bg_card"])
            body_row.pack(fill="x", padx=14, pady=(0, 8))
            tk.Label(
                body_row, textvariable=text_var,
                font=FONTS["body_bold"], fg=val_color, bg=THEME["bg_card"],
                anchor="w", wraplength=760, justify="left"
            ).pack(fill="x")
            return card

        self._raw_heard_var = tk.StringVar(value="—")
        self._executed_cmd_var = tk.StringVar(value="—")
        self._jarvis_reply_var = tk.StringVar(value="—")

        make_telemetry_card(cards_container, "🎙️", "ВХОДЯЩАЯ РЕЧЬ (МИКРОФОН)", self._raw_heard_var, THEME["amber"])
        make_telemetry_card(cards_container, "⚡", "РАСПОЗНАННАЯ КОМАНДА", self._executed_cmd_var, THEME["cyan"])
        make_telemetry_card(cards_container, "💬", "ОТВЕТ ДЖАРВИСА", self._jarvis_reply_var, THEME["text_main"])

        # Панель ручного ввода команды
        test_panel = tk.Frame(frame, bg=THEME["bg_root"])
        test_panel.pack(fill="x", padx=20, pady=(6, 4))

        tk.Label(
            test_panel, text="РУЧНОЙ ВВОД КОМАНДЫ ДЛЯ ТЕСТИРОВАНИЯ:",
            font=FONTS["caption_bold"], fg=THEME["text_muted"], bg=THEME["bg_root"]
        ).pack(anchor="w", pady=(0, 4))

        input_row = tk.Frame(test_panel, bg=THEME["bg_root"])
        input_row.pack(fill="x")

        self._manual_cmd_var = tk.StringVar()
        self._cmd_entry = tk.Entry(
            input_row, textvariable=self._manual_cmd_var,
            font=FONTS["body"], bg=THEME["bg_input"], fg=THEME["text_main"],
            insertbackground=THEME["cyan"], relief="flat",
            highlightbackground=THEME["border"], highlightcolor=THEME["cyan"], highlightthickness=1
        )
        self._cmd_entry.pack(side="left", fill="x", expand=True, padx=(0, 8), ipady=6)
        self._cmd_entry.bind("<Return>", lambda e: self._on_send_manual_cmd())

        tk.Button(
            input_row, text="▶  Выполнить",
            font=FONTS["body_bold"], fg="#05080f", bg=THEME["cyan"],
            activeforeground="#05080f", activebackground=THEME["cyan_hover"],
            relief="flat", padx=16, pady=5, cursor="hand2",
            command=self._on_send_manual_cmd
        ).pack(side="right")

        # Быстрые команды (Chips)
        quick_frame = tk.Frame(frame, bg=THEME["bg_root"])
        quick_frame.pack(fill="x", padx=20, pady=(6, 8))

        quick_cmds = [
            ("🎵 Музыка", "включи музыку"),
            ("⛅ Погода", "какая сейчас погода"),
            ("📂 Проводник", "открой проводник"),
            ("🎬 Аниме", "хочу посмотреть аниме восхождение в тени"),
            ("💲 Доллар", "курс доллара"),
            ("📋 Задачи", "список дел"),
            ("⏸️ Пауза", "пауза"),
        ]
        for label, qcmd in quick_cmds:
            b = tk.Button(
                quick_frame, text=label,
                font=FONTS["caption"], fg=THEME["text_sub"], bg=THEME["bg_card"],
                activeforeground=THEME["cyan"], activebackground=THEME["bg_hover"],
                highlightbackground=THEME["border"], highlightthickness=1,
                relief="flat", padx=8, pady=4, cursor="hand2",
                command=lambda c=qcmd: self._send_quick_cmd(c)
            )
            b.pack(side="left", padx=3)

        # Консоль журнала активности
        tk.Label(
            frame, text="ЖУРНАЛ АКТИВНОСТИ:",
            font=FONTS["caption_bold"], fg=THEME["text_muted"], bg=THEME["bg_root"]
        ).pack(anchor="w", padx=20, pady=(4, 2))

        history_frame = tk.Frame(frame, bg=THEME["bg_input"], highlightbackground=THEME["border"], highlightthickness=1)
        history_frame.pack(fill="both", expand=True, padx=20, pady=(0, 14))

        self._history_text = tk.Text(
            history_frame, bg=THEME["bg_input"], fg=THEME["cyan"],
            font=FONTS["mono"], relief="flat", state="disabled",
            wrap="word", padx=12, pady=8,
        )
        sb = ttk.Scrollbar(history_frame, command=self._history_text.yview)
        self._history_text.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self._history_text.pack(side="left", fill="both", expand=True)

        return frame

    # ==========================================
    # 2. СТРАНИЦА: СПИСОК ДЕЛ (TO-DO)
    # ==========================================
    def _build_todo_page(self, parent: tk.Frame) -> tk.Frame:
        frame = tk.Frame(parent, bg=THEME["bg_root"])

        top_bar = tk.Frame(frame, bg=THEME["bg_root"])
        top_bar.pack(fill="x", padx=20, pady=(16, 8))

        tk.Label(
            top_bar, text="СПИСОК ДЕЛ И НАПОМИНАНИЯ",
            font=FONTS["title"],
            fg=THEME["cyan"], bg=THEME["bg_root"]
        ).pack(side="left")

        tk.Frame(frame, bg=THEME["border"], height=1).pack(fill="x", padx=20, pady=(0, 8))

        # Панель добавления новой задачи
        add_panel = tk.Frame(frame, bg=THEME["bg_card"], highlightbackground=THEME["border"], highlightthickness=1)
        add_panel.pack(fill="x", padx=20, pady=4)

        self._new_todo_var = tk.StringVar()
        entry = tk.Entry(
            add_panel, textvariable=self._new_todo_var,
            font=FONTS["body"], bg=THEME["bg_input"], fg=THEME["text_main"],
            insertbackground=THEME["cyan"], relief="flat",
            highlightthickness=1, highlightbackground=THEME["border"], highlightcolor=THEME["cyan"]
        )
        entry.pack(side="left", fill="x", expand=True, padx=10, pady=10, ipady=5)
        entry.bind("<Return>", lambda e: self._on_add_todo())

        tk.Button(
            add_panel, text="➕  Добавить дело",
            font=FONTS["body_bold"], fg="#05080f", bg=THEME["cyan"],
            activebackground=THEME["cyan_hover"], activeforeground="#05080f",
            relief="flat", padx=14, pady=6, cursor="hand2",
            command=self._on_add_todo
        ).pack(side="left", padx=(0, 10))

        # Панель голосового таймера
        remind_panel = tk.Frame(frame, bg=THEME["bg_card"], highlightbackground=THEME["border"], highlightthickness=1)
        remind_panel.pack(fill="x", padx=20, pady=4)

        tk.Label(
            remind_panel, text="⏰  Напомнить через:",
            font=FONTS["caption_bold"], fg=THEME["text_sub"], bg=THEME["bg_card"]
        ).pack(side="left", padx=(10, 4), pady=8)

        self._remind_min_var = tk.StringVar(value="30")
        tk.Entry(
            remind_panel, textvariable=self._remind_min_var,
            font=FONTS["body"], bg=THEME["bg_input"], fg=THEME["cyan"],
            width=5, relief="flat", highlightthickness=1, highlightbackground=THEME["border"], justify="center"
        ).pack(side="left", padx=4, ipady=3)

        tk.Label(remind_panel, text="минут о:", font=FONTS["caption"], fg=THEME["text_muted"], bg=THEME["bg_card"]).pack(side="left", padx=2)

        self._remind_task_var = tk.StringVar(value="выпить таблетку")
        tk.Entry(
            remind_panel, textvariable=self._remind_task_var,
            font=FONTS["body"], bg=THEME["bg_input"], fg=THEME["text_main"],
            relief="flat", highlightthickness=1, highlightbackground=THEME["border"], highlightcolor=THEME["cyan"]
        ).pack(side="left", fill="x", expand=True, padx=6, ipady=3)

        tk.Button(
            remind_panel, text="Поставить таймер",
            font=FONTS["caption_bold"], fg=THEME["text_main"], bg=THEME["bg_hover"],
            activebackground=THEME["cyan"], activeforeground="#05080f",
            relief="flat", padx=10, pady=5, cursor="hand2",
            command=self._on_set_gui_reminder
        ).pack(side="left", padx=(4, 10))

        # Контейнер списка задач
        list_container = tk.Frame(frame, bg=THEME["bg_input"], highlightbackground=THEME["border"], highlightthickness=1)
        list_container.pack(fill="both", expand=True, padx=20, pady=(6, 8))

        self._todo_canvas = tk.Canvas(list_container, bg=THEME["bg_input"], highlightthickness=0)
        todo_sb = ttk.Scrollbar(list_container, command=self._todo_canvas.yview)
        self._todo_canvas.configure(yscrollcommand=todo_sb.set)

        todo_sb.pack(side="right", fill="y")
        self._todo_canvas.pack(side="left", fill="both", expand=True)

        self._todo_scroll_frame = tk.Frame(self._todo_canvas, bg=THEME["bg_input"])
        self._todo_scroll_frame.bind(
            "<Configure>",
            lambda e: self._todo_canvas.configure(scrollregion=self._todo_canvas.bbox("all"))
        )
        self._todo_canvas.create_window((0, 0), window=self._todo_scroll_frame, anchor="nw")

        # Нижняя панель действий
        bottom_actions = tk.Frame(frame, bg=THEME["bg_root"])
        bottom_actions.pack(fill="x", padx=20, pady=(0, 14))

        tk.Button(
            bottom_actions, text="🧹  Очистить выполненные",
            font=FONTS["caption_bold"], fg=THEME["text_sub"], bg=THEME["bg_card"],
            relief="flat", padx=12, pady=6, cursor="hand2",
            command=self._on_clear_done_todos
        ).pack(side="left")

        tk.Button(
            bottom_actions, text="🗑️  Удалить все дела",
            font=FONTS["caption_bold"], fg=THEME["coral"], bg=THEME["bg_card"],
            relief="flat", padx=12, pady=6, cursor="hand2",
            command=self._on_clear_all_todos
        ).pack(side="left", padx=8)

        tk.Button(
            bottom_actions, text="🔄  Обновить",
            font=FONTS["caption_bold"], fg=THEME["text_sub"], bg=THEME["bg_card"],
            relief="flat", padx=12, pady=6, cursor="hand2",
            command=self._refresh_todo_list
        ).pack(side="right")

        return frame

    def _refresh_todo_list(self):
        for widget in self._todo_scroll_frame.winfo_children():
            widget.destroy()

        todos = get_all_todos()
        if not todos:
            empty_box = tk.Frame(self._todo_scroll_frame, bg=THEME["bg_input"])
            empty_box.pack(fill="x", pady=40, padx=20)
            tk.Label(
                empty_box,
                text="📋 Список дел пуст.\nДобавьте задачу выше или скажите голосом: «Джарвис, добавь в список дел...»",
                font=FONTS["body"], fg=THEME["text_muted"], bg=THEME["bg_input"], justify="center"
            ).pack()
            return

        for idx, item in enumerate(todos):
            task_text = item.get("task", "")
            is_done = item.get("done", False)

            row = tk.Frame(self._todo_scroll_frame, bg=THEME["bg_card"], highlightbackground=THEME["border"], highlightthickness=1)
            row.pack(fill="x", padx=10, pady=3, expand=True)

            status_icon = "✓" if is_done else " "
            status_fg = THEME["emerald"] if is_done else THEME["text_muted"]
            toggle_btn = tk.Button(
                row, text=status_icon, font=FONTS["body_bold"], width=3,
                bg=THEME["bg_input"], fg=status_fg,
                activebackground=THEME["bg_hover"],
                relief="flat", cursor="hand2",
                command=lambda i=idx: self._on_toggle_todo(i)
            )
            toggle_btn.pack(side="left", padx=6, pady=6)

            text_color = THEME["text_muted"] if is_done else THEME["text_main"]
            task_font = (FONTS["body"][0], FONTS["body"][1], "overstrike" if is_done else "normal")
            task_lbl = tk.Label(
                row, text=task_text, font=task_font,
                fg=text_color, bg=THEME["bg_card"], anchor="w"
            )
            task_lbl.pack(side="left", fill="x", expand=True, padx=4)

            del_btn = tk.Button(
                row, text="✕", font=FONTS["caption_bold"],
                bg=THEME["bg_card"], fg=THEME["coral"], activebackground="#5c1d1d",
                relief="flat", padx=8, pady=4, cursor="hand2",
                command=lambda i=idx: self._on_delete_todo(i)
            )
            del_btn.pack(side="right", padx=6)

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
        frame = tk.Frame(parent, bg=THEME["bg_root"])

        top_bar = tk.Frame(frame, bg=THEME["bg_root"])
        top_bar.pack(fill="x", padx=20, pady=(16, 6))

        tk.Label(
            top_bar, text="БАЗА ЗНАНИЙ И КОМАНД",
            font=FONTS["title"], fg=THEME["cyan"], bg=THEME["bg_root"]
        ).pack(side="left")

        self._cmd_search_var = tk.StringVar()
        search_entry = tk.Entry(
            top_bar, textvariable=self._cmd_search_var, width=28,
            font=FONTS["body"], bg=THEME["bg_input"], fg=THEME["text_main"],
            insertbackground=THEME["cyan"], relief="flat",
            highlightthickness=1, highlightbackground=THEME["border"], highlightcolor=THEME["cyan"]
        )
        search_entry.pack(side="right", ipady=4)
        tk.Label(top_bar, text="🔍 Поиск:", font=FONTS["caption_bold"],
                 fg=THEME["text_muted"], bg=THEME["bg_root"]).pack(side="right", padx=6)
        self._cmd_search_var.trace_add("write", lambda *_: self._render_catalog())

        tk.Label(
            frame, text="Кликните на любую команду, чтобы Джарвис выполнил её. Голосом: скажите «Джарвис», затем фразу.",
            font=FONTS["caption"], fg=THEME["text_muted"], bg=THEME["bg_root"], anchor="w"
        ).pack(fill="x", padx=20, pady=(0, 6))

        tk.Frame(frame, bg=THEME["border"], height=1).pack(fill="x", padx=20, pady=(0, 8))

        container = tk.Frame(frame, bg=THEME["bg_input"], highlightbackground=THEME["border"], highlightthickness=1)
        container.pack(fill="both", expand=True, padx=20, pady=(0, 14))

        self._cmd_canvas = tk.Canvas(container, bg=THEME["bg_input"], highlightthickness=0)
        sb = ttk.Scrollbar(container, command=self._cmd_canvas.yview)
        self._cmd_canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self._cmd_canvas.pack(side="left", fill="both", expand=True)

        self._cmd_inner = tk.Frame(self._cmd_canvas, bg=THEME["bg_input"])
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
            tk.Label(self._cmd_inner, text="По вашему запросу ничего не найдено", font=FONTS["body"],
                     fg=THEME["text_muted"], bg=THEME["bg_input"]).pack(pady=30)
            return

        for category in categories:
            box = tk.Frame(self._cmd_inner, bg=THEME["bg_card"], highlightbackground=THEME["border"], highlightthickness=1)
            box.pack(fill="x", padx=12, pady=6)

            tk.Label(box, text=category.title, font=FONTS["subtitle"],
                     fg=THEME["cyan"], bg=THEME["bg_card"]).pack(anchor="w", padx=12, pady=(10, 4))

            for item in category.items:
                tk.Label(box, text=item.description, font=FONTS["caption"],
                         fg=THEME["text_muted"], bg=THEME["bg_card"], justify="left", anchor="w",
                         wraplength=760).pack(fill="x", padx=14, pady=(4, 2))
                for example in item.examples:
                    tk.Button(
                        box, text=f"▶  «{example}»", anchor="w", justify="left",
                        font=FONTS["caption_bold"], fg=THEME["cyan_hover"], bg=THEME["bg_input"],
                        activebackground=THEME["cyan"], activeforeground="#05080f",
                        relief="flat", padx=10, pady=3, cursor="hand2",
                        command=lambda text=example: self._send_quick_cmd(text)
                    ).pack(fill="x", padx=20, pady=2)
            tk.Frame(box, height=8, bg=THEME["bg_card"]).pack()

    # ==========================================
    # 4. СТРАНИЦА: РАСШИРЕННЫЕ НАСТРОЙКИ
    # ==========================================
    def _build_settings_page(self, parent: tk.Frame,
                             name: str, honorific: str) -> tk.Frame:
        frame = tk.Frame(parent, bg=THEME["bg_root"])

        top_bar = tk.Frame(frame, bg=THEME["bg_root"])
        top_bar.pack(fill="x", padx=20, pady=(16, 8))

        tk.Label(
            top_bar, text="ПАРАМЕТРЫ СИСТЕМЫ JARVIS",
            font=FONTS["title"],
            fg=THEME["cyan"], bg=THEME["bg_root"]
        ).pack(side="left")

        tk.Frame(frame, bg=THEME["border"], height=1).pack(fill="x", padx=20, pady=(0, 6))

        container = tk.Frame(frame, bg=THEME["bg_input"], highlightbackground=THEME["border"], highlightthickness=1)
        container.pack(fill="both", expand=True, padx=20, pady=4)

        canvas = tk.Canvas(container, bg=THEME["bg_input"], highlightthickness=0)
        sb = ttk.Scrollbar(container, command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)

        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        scroll_frame = tk.Frame(canvas, bg=THEME["bg_input"])
        window_id = canvas.create_window((0, 0), window=scroll_frame, anchor="nw")

        scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.bind(
            "<Configure>",
            lambda e: canvas.itemconfigure(window_id, width=e.width)
        )
        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", lambda ev: canvas.yview_scroll(int(-ev.delta / 120), "units")))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

        cfg = load_config()

        def make_section(title):
            sec = tk.Frame(scroll_frame, bg=THEME["bg_card"], highlightbackground=THEME["border"], highlightthickness=1)
            sec.pack(fill="x", padx=14, pady=6)
            tk.Label(
                sec, text=title, font=FONTS["subtitle"],
                fg=THEME["cyan"], bg=THEME["bg_card"]
            ).pack(anchor="w", padx=14, pady=(10, 6))
            return sec

        def make_row(parent_sec, label_text):
            r = tk.Frame(parent_sec, bg=THEME["bg_card"])
            r.pack(fill="x", padx=14, pady=5)
            tk.Label(
                r, text=label_text, font=FONTS["body"],
                fg=THEME["text_sub"], bg=THEME["bg_card"], width=28, anchor="w"
            ).pack(side="left")
            return r

        entry_style = dict(font=FONTS["body"], bg=THEME["bg_input"], fg=THEME["text_main"], relief="flat",
                           highlightthickness=1, highlightbackground=THEME["border"], highlightcolor=THEME["cyan"])
        button_style = dict(font=FONTS["caption_bold"], fg=THEME["text_main"], bg=THEME["bg_hover"],
                            activebackground=THEME["cyan"], activeforeground="#05080f", relief="flat", padx=10, pady=5, cursor="hand2")

        # ---------------- СЕКЦИЯ 1: ПРОФИЛЬ И ГОРОД ----------------
        sec_profile = make_section("👤  ПРОФИЛЬ И МЕСТОПОЛОЖЕНИЕ")

        r_name = make_row(sec_profile, "Имя пользователя:")
        self._name_var = tk.StringVar(value=cfg.get("name", name))
        tk.Entry(r_name, textvariable=self._name_var, **entry_style).pack(side="left", fill="x", expand=True)

        r_hon = make_row(sec_profile, "Обращение:")
        self._honorific_var = tk.StringVar(value=cfg.get("honorific", honorific))
        tk.Entry(r_hon, textvariable=self._honorific_var, **entry_style).pack(side="left", fill="x", expand=True)

        r_city = make_row(sec_profile, "Город (для погоды):")
        self._city_var = tk.StringVar(value=cfg.get("city", "Москва"))
        ttk.Combobox(
            r_city, textvariable=self._city_var,
            values=DEFAULT_CITIES, font=FONTS["body"]
        ).pack(side="left", fill="x", expand=True)

        # ---------------- СЕКЦИЯ 2: ИСТОЧНИКИ МЕДИА И ПОИСКА ----------------
        sec_sources = make_section("🌐  ИСТОЧНИКИ КОНТЕНТА И ПОИСКА")

        r_music = make_row(sec_sources, "Плеер музыки:")
        self._music_player_var = tk.StringVar(value=cfg.get("music_player", "YouTube Music"))
        ttk.Combobox(
            r_music, textvariable=self._music_player_var,
            values=list(MUSIC_PLAYERS.keys()), state="readonly", font=FONTS["body"]
        ).pack(side="left", fill="x", expand=True)

        r_movie = make_row(sec_sources, "Сайт для фильмов:")
        self._movie_source_var = tk.StringVar(value=cfg.get("movie_source", "KinoGo"))
        ttk.Combobox(
            r_movie, textvariable=self._movie_source_var,
            values=list(MOVIE_SOURCES.keys()), state="readonly", font=FONTS["body"]
        ).pack(side="left", fill="x", expand=True)

        r_anime = make_row(sec_sources, "Сайт для аниме:")
        self._anime_source_var = tk.StringVar(value=cfg.get("anime_source", "AnimeGO"))
        ttk.Combobox(
            r_anime, textvariable=self._anime_source_var,
            values=list(ANIME_SOURCES.keys()), state="readonly", font=FONTS["body"]
        ).pack(side="left", fill="x", expand=True)

        r_map = make_row(sec_sources, "Карты и отзывы:")
        self._map_labels = {"google": "Google Карты", "yandex": "Яндекс Карты"}
        self._map_var = tk.StringVar(value=self._map_labels.get(cfg.get("map_provider", "google"), "Google Карты"))
        ttk.Combobox(
            r_map, textvariable=self._map_var, values=list(self._map_labels.values()),
            state="readonly", font=FONTS["body"]
        ).pack(side="left", fill="x", expand=True)

        # ---------------- СЕКЦИЯ 3: ЗВУК И МИКРОФОН ----------------
        sec_audio = make_section("🎧  ЗВУК, МИКРОФОН И РАСПОЗНАВАНИЕ")

        # Список микрофонов
        r_mic = make_row(sec_audio, "Микрофон:")
        mic_devices = [d for d in self.audio_manager.get_all_devices() if d['is_input']]
        self._mic_options = [f"[{d['index']}] {d['name']}" for d in mic_devices]
        current_mic_idx = cfg.get("microphone_index")
        current_mic_label = self._mic_options[0] if self._mic_options else "По умолчанию"
        for opt in self._mic_options:
            if current_mic_idx is not None and opt.startswith(f"[{current_mic_idx}]"):
                current_mic_label = opt
                break

        self._mic_var = tk.StringVar(value=current_mic_label)
        ttk.Combobox(
            r_mic, textvariable=self._mic_var,
            values=self._mic_options, state="readonly", font=FONTS["body"]
        ).pack(side="left", fill="x", expand=True)

        # Громкость голоса Джарвиса
        vol_frame = tk.Frame(sec_audio, bg=THEME["bg_card"])
        vol_frame.pack(fill="x", padx=14, pady=5)
        tk.Label(
            vol_frame, text="Громкость голоса Джарвиса:", font=FONTS["body"],
            fg=THEME["text_sub"], bg=THEME["bg_card"], width=28, anchor="w"
        ).pack(side="left")

        self._vol_var = tk.IntVar(value=int(cfg.get("voice_volume", 100)))
        vol_slider = ttk.Scale(
            vol_frame, from_=0, to=100, variable=self._vol_var,
            orient="horizontal", command=self._on_volume_slider_change
        )
        vol_slider.pack(side="left", fill="x", expand=True, padx=8)
        vol_slider.bind("<ButtonRelease-1>", lambda e: self._preview_voice())

        self._vol_lbl = tk.Label(
            vol_frame, text=f"{self._vol_var.get()}%", font=FONTS["body_bold"],
            fg=THEME["cyan"], bg=THEME["bg_card"], width=6
        )
        self._vol_lbl.pack(side="left")

        # Как часто добавлять «сэр»
        chance_frame = tk.Frame(sec_audio, bg=THEME["bg_card"])
        chance_frame.pack(fill="x", padx=14, pady=5)
        tk.Label(
            chance_frame, text="Частота обращения «сэр»:", font=FONTS["body"],
            fg=THEME["text_sub"], bg=THEME["bg_card"], width=28, anchor="w"
        ).pack(side="left")
        self._honor_chance_var = tk.IntVar(value=round(float(cfg.get("honorific_chance", 0.25)) * 100))
        ttk.Scale(
            chance_frame, from_=0, to=100, variable=self._honor_chance_var,
            orient="horizontal", command=self._on_honor_chance_change
        ).pack(side="left", fill="x", expand=True, padx=8)
        self._honor_chance_lbl = tk.Label(
            chance_frame, text=f"{self._honor_chance_var.get()}%", font=FONTS["body_bold"],
            fg=THEME["cyan"], bg=THEME["bg_card"], width=6
        )
        self._honor_chance_lbl.pack(side="left")

        # Таймаут ожидания контекста
        timeout_frame = tk.Frame(sec_audio, bg=THEME["bg_card"])
        timeout_frame.pack(fill="x", padx=14, pady=5)
        tk.Label(
            timeout_frame, text="Таймаут контекста диалога:", font=FONTS["body"],
            fg=THEME["text_sub"], bg=THEME["bg_card"], width=28, anchor="w"
        ).pack(side="left")

        self._context_timeout_var = tk.DoubleVar(value=float(cfg.get("context_timeout", 5.0)))
        timeout_slider = ttk.Scale(
            timeout_frame, from_=3.0, to=12.0, variable=self._context_timeout_var,
            orient="horizontal", command=self._on_timeout_slider_change
        )
        timeout_slider.pack(side="left", fill="x", expand=True, padx=8)

        self._timeout_lbl = tk.Label(
            timeout_frame, text=f"{int(self._context_timeout_var.get())}с",
            font=FONTS["body_bold"], fg=THEME["cyan"], bg=THEME["bg_card"], width=6
        )
        self._timeout_lbl.pack(side="left")

        # Чувствительность VAD
        vad_frame = tk.Frame(sec_audio, bg=THEME["bg_card"])
        vad_frame.pack(fill="x", padx=14, pady=5)
        tk.Label(
            vad_frame, text="Чувствительность VAD (голос):", font=FONTS["body"],
            fg=THEME["text_sub"], bg=THEME["bg_card"], width=28, anchor="w"
        ).pack(side="left")

        self._vad_thresh_var = tk.DoubleVar(value=float(cfg.get("vad_threshold", 0.5)))
        vad_slider = ttk.Scale(
            vad_frame, from_=0.20, to=0.80, variable=self._vad_thresh_var,
            orient="horizontal", command=self._on_vad_thresh_change
        )
        vad_slider.pack(side="left", fill="x", expand=True, padx=8)

        self._vad_lbl = tk.Label(
            vad_frame, text=f"{self._vad_thresh_var.get():.2f}",
            font=FONTS["body_bold"], fg=THEME["cyan"], bg=THEME["bg_card"], width=6
        )
        self._vad_lbl.pack(side="left")

        # Пауза конца речи
        pause_frame = tk.Frame(sec_audio, bg=THEME["bg_card"])
        pause_frame.pack(fill="x", padx=14, pady=5)
        tk.Label(
            pause_frame, text="Пауза конца фразы (мс):", font=FONTS["body"],
            fg=THEME["text_sub"], bg=THEME["bg_card"], width=28, anchor="w"
        ).pack(side="left")

        self._silence_ms_var = tk.IntVar(value=int(cfg.get("silence_ms", 400)))
        pause_slider = ttk.Scale(
            pause_frame, from_=200, to=800, variable=self._silence_ms_var,
            orient="horizontal", command=self._on_silence_ms_change
        )
        pause_slider.pack(side="left", fill="x", expand=True, padx=8)

        self._pause_lbl = tk.Label(
            pause_frame, text=f"{self._silence_ms_var.get()}мс",
            font=FONTS["body_bold"], fg=THEME["cyan"], bg=THEME["bg_card"], width=6
        )
        self._pause_lbl.pack(side="left")

        # Программное усиление микрофона
        gain_frame = tk.Frame(sec_audio, bg=THEME["bg_card"])
        gain_frame.pack(fill="x", padx=14, pady=5)
        tk.Label(
            gain_frame, text="Усиление микрофона (Gain):", font=FONTS["body"],
            fg=THEME["text_sub"], bg=THEME["bg_card"], width=28, anchor="w"
        ).pack(side="left")

        self._mic_gain_var = tk.DoubleVar(value=float(cfg.get("mic_gain", 1.0)))
        gain_slider = ttk.Scale(
            gain_frame, from_=0.8, to=2.5, variable=self._mic_gain_var,
            orient="horizontal", command=self._on_mic_gain_change
        )
        gain_slider.pack(side="left", fill="x", expand=True, padx=8)

        self._gain_lbl = tk.Label(
            gain_frame, text=f"{self._mic_gain_var.get():.1f}x",
            font=FONTS["body_bold"], fg=THEME["cyan"], bg=THEME["bg_card"], width=6
        )
        self._gain_lbl.pack(side="left")

        # Кнопка автокалибровки
        cal_bar = tk.Frame(sec_audio, bg=THEME["bg_card"])
        cal_bar.pack(fill="x", padx=14, pady=(4, 8))
        self._cal_btn = tk.Button(
            cal_bar, text="🎯  Автокалибровка микрофона (2 сек в тишине)",
            command=self._on_run_calibration, **button_style
        )
        self._cal_btn.pack(side="left")

        self._cal_status_lbl = tk.Label(
            cal_bar, text="", font=FONTS["caption_bold"],
            fg=THEME["emerald"], bg=THEME["bg_card"]
        )
        self._cal_status_lbl.pack(side="left", padx=10)

        # Модель Vosk
        r_vosk = make_row(sec_audio, "Модель распознавания Vosk:")
        model_dirs = [d for d in os.listdir(".") if os.path.isdir(d) and (d.startswith("model") or "vosk" in d.lower())]
        if not model_dirs:
            model_dirs = ["model_small"]
        self._vosk_model_var = tk.StringVar(value=cfg.get("vosk_model", model_dirs[0]))
        ttk.Combobox(
            r_vosk, textvariable=self._vosk_model_var,
            values=model_dirs, state="readonly", font=FONTS["body"]
        ).pack(side="left", fill="x", expand=True)

        tk.Label(
            sec_audio,
            text="💡 Подсказка: для распознавания сложных английских слов и названий положите\nполную модель (vosk-model-ru-0.42) в папку проекта и выберите её выше.",
            font=FONTS["caption"], fg=THEME["text_muted"], bg=THEME["bg_card"], justify="left"
        ).pack(anchor="w", padx=14, pady=(2, 8))

        # ---------------- СЕКЦИЯ: НАПОМИНАНИЯ ----------------
        sec_notify = make_section("🔔  УВЕДОМЛЕНИЯ О НАПОМИНАНИЯХ")
        tk.Label(
            sec_notify,
            text="Напоминание всегда произносится голосом. Дополнительно оно отправляется в выбранный канал:",
            font=FONTS["caption"], fg=THEME["text_muted"], bg=THEME["bg_card"]
        ).pack(anchor="w", padx=14, pady=(0, 4))

        r_chan = make_row(sec_notify, "Куда присылать:")
        self._notify_labels = {"pc": "Уведомление на компьютере", "telegram": "Сообщение в Telegram",
                               "both": "Компьютер и Telegram"}
        self._notify_var = tk.StringVar(
            value=self._notify_labels.get(cfg.get("notify_channel", "pc"), self._notify_labels["pc"]))
        ttk.Combobox(
            r_chan, textvariable=self._notify_var, values=list(self._notify_labels.values()),
            state="readonly", font=FONTS["body"]
        ).pack(side="left", fill="x", expand=True)

        r_token = make_row(sec_notify, "Токен Telegram-бота:")
        self._tg_token_var = tk.StringVar(value=cfg.get("telegram_token", ""))
        tk.Entry(r_token, textvariable=self._tg_token_var, show="•", **entry_style).pack(side="left", fill="x", expand=True)

        r_chat = make_row(sec_notify, "Chat ID пользователя:")
        self._tg_chat_var = tk.StringVar(value=cfg.get("telegram_chat_id", ""))
        tk.Entry(r_chat, textvariable=self._tg_chat_var, **entry_style).pack(side="left", fill="x", expand=True)

        notify_bar = tk.Frame(sec_notify, bg=THEME["bg_card"])
        notify_bar.pack(fill="x", padx=14, pady=(4, 6))
        tk.Button(notify_bar, text="🔎  Найти Chat ID", command=self._on_detect_chat_id,
                  **button_style).pack(side="left")
        tk.Button(notify_bar, text="📨  Проверить уведомление", command=self._on_test_notification,
                  **button_style).pack(side="left", padx=8)
        self._notify_status_lbl = tk.Label(notify_bar, text="", font=FONTS["caption_bold"],
                                           fg=THEME["emerald"], bg=THEME["bg_card"])
        self._notify_status_lbl.pack(side="left", padx=6)

        tk.Label(
            sec_notify,
            text="💡 Telegram: создайте бота у @BotFather, вставьте токен, отправьте боту любое\nсообщение и нажмите «Найти Chat ID».",
            font=FONTS["caption"], fg=THEME["text_muted"], bg=THEME["bg_card"], justify="left"
        ).pack(anchor="w", padx=14, pady=(2, 8))

        # ---------------- СЕКЦИЯ: РАЗРАБОТКА ----------------
        sec_dev = make_section("💻  РАЗРАБОТКА И IDE")

        r_proj = make_row(sec_dev, "Папка с проектами:")
        self._projects_root_var = tk.StringVar(value=cfg.get("projects_root", ""))
        tk.Entry(r_proj, textvariable=self._projects_root_var, **entry_style).pack(
            side="left", fill="x", expand=True)
        tk.Button(r_proj, text="Обзор…", command=self._on_browse_projects,
                  **button_style).pack(side="left", padx=(8, 0))

        r_ide = make_row(sec_dev, "IDE по умолчанию:")
        self._ide_titles = {i: spec["title"] for i, spec in IDES.items()}
        self._ide_var = tk.StringVar(value=self._ide_titles.get(cfg.get("default_ide", "idea"), "IntelliJ IDEA"))
        ttk.Combobox(
            r_ide, textvariable=self._ide_var, values=list(self._ide_titles.values()),
            state="readonly", font=FONTS["body"]
        ).pack(side="left", fill="x", expand=True)
        tk.Label(
            sec_dev,
            text="💡 Голосовая команда: «открой проект <название папки>» или «открой <проект> в идее».",
            font=FONTS["caption"], fg=THEME["text_muted"], bg=THEME["bg_card"]
        ).pack(anchor="w", padx=14, pady=(2, 8))

        # ---------------- СЕКЦИЯ 4: СИСТЕМА ----------------
        sec_sys = make_section("⚙️  СИСТЕМА И АВТОЗАПУСК")

        self._autostart_var = tk.BooleanVar(
            value=bool(cfg.get("autostart", False)) or is_autostart_enabled()
        )
        chk = tk.Checkbutton(
            sec_sys,
            text="Запускать JARVIS вместе с Windows",
            variable=self._autostart_var,
            onvalue=True, offvalue=False,
            font=FONTS["body"],
            fg=THEME["text_main"], bg=THEME["bg_card"],
            activeforeground=THEME["cyan"], activebackground=THEME["bg_card"],
            selectcolor=THEME["bg_input"], relief="flat", highlightthickness=0
        )
        chk.pack(anchor="w", padx=14, pady=6)

        # Нижняя плашка сохранения
        bottom_bar = tk.Frame(frame, bg=THEME["bg_root"])
        bottom_bar.pack(fill="x", padx=20, pady=12)

        self._save_status_var = tk.StringVar(value="")
        tk.Label(
            bottom_bar, textvariable=self._save_status_var,
            font=FONTS["body_bold"], fg=THEME["emerald"], bg=THEME["bg_root"]
        ).pack(side="left")

        tk.Button(
            bottom_bar, text="💾  Сохранить настройки",
            font=FONTS["body_bold"],
            fg="#05080f", bg=THEME["cyan"],
            activeforeground="#05080f", activebackground=THEME["cyan_hover"],
            relief="flat", padx=20, pady=8, cursor="hand2",
            command=self._save_all_settings
        ).pack(side="right")

        return frame

    def _on_volume_slider_change(self, val):
        pct = int(float(val))
        self._vol_lbl.config(text=f"{pct}%")
        ProfileManager().current["voice_volume"] = pct

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
            self._notify_status_lbl.config(text="Сначала вставьте токен", fg=THEME["coral"])
            return
        chat_id, error = notifier.detect_chat_id(token)
        if chat_id:
            self._tg_chat_var.set(chat_id)
            self._notify_status_lbl.config(text=f"Найден: {chat_id}", fg=THEME["emerald"])
        else:
            self._notify_status_lbl.config(text=error, fg=THEME["coral"])

    def _on_test_notification(self):
        channel = next((k for k, v in self._notify_labels.items() if v == self._notify_var.get()), "pc")
        if channel in ("pc", "both"):
            notifier.notify_pc("Джарвис", "Проверка уведомлений: всё работает")
        if channel in ("telegram", "both"):
            ok, error = notifier.notify_telegram(
                "Джарвис: проверка уведомлений",
                token=self._tg_token_var.get().strip(), chat_id=self._tg_chat_var.get().strip())
            self._notify_status_lbl.config(text="Отправлено" if ok else error,
                                           fg=THEME["emerald"] if ok else THEME["coral"])
        else:
            self._notify_status_lbl.config(text="Отправлено", fg=THEME["emerald"])

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
        self._cal_status_lbl.config(text="Замеряю шум (тишина 2 сек)...", fg=THEME["amber"])
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
                    self._cal_status_lbl.config(text=f"Готово! Шум: {res['rms']}, Порог: {rec_thresh}", fg=THEME["emerald"])
                else:
                    self._cal_status_lbl.config(text="Не удалось получить аудиоданные", fg=THEME["coral"])
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
        self._save_status_var.set("✅  Настройки успешно сохранены и применены!")
        self.root.after(3000, lambda: self._save_status_var.set(""))

    # ==========================================
    # 5. СТРАНИЦА: РАСШИРЕННЫЕ ЛОГИ
    # ==========================================
    def _build_logs_page(self, parent: tk.Frame) -> tk.Frame:
        frame = tk.Frame(parent, bg=THEME["bg_root"])

        top_bar = tk.Frame(frame, bg=THEME["bg_root"])
        top_bar.pack(fill="x", padx=20, pady=(16, 6))

        tk.Label(
            top_bar, text="РАСШИРЕННЫЙ ЖУРНАЛ СОБЫТИЙ",
            font=FONTS["title"],
            fg=THEME["cyan"], bg=THEME["bg_root"]
        ).pack(side="left")

        # Панель фильтров
        filter_bar = tk.Frame(frame, bg=THEME["bg_root"])
        filter_bar.pack(fill="x", padx=20, pady=4)

        tk.Label(
            filter_bar, text="Фильтр:", font=FONTS["caption_bold"],
            fg=THEME["text_muted"], bg=THEME["bg_root"]
        ).pack(side="left", padx=(0, 6))

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
                font=FONTS["caption_bold"],
                fg="#05080f" if k == "ALL" else THEME["text_sub"],
                bg=THEME["cyan"] if k == "ALL" else THEME["bg_card"],
                relief="flat", padx=10, pady=3, cursor="hand2",
                command=lambda fk=k: self._set_log_filter(fk)
            )
            btn.pack(side="left", padx=2)
            self._filter_buttons[k] = btn

        # Чекбокс автопрокрутки
        tk.Checkbutton(
            filter_bar, text="Автопрокрутка", variable=self._autoscroll,
            font=FONTS["caption"], fg=THEME["text_sub"], bg=THEME["bg_root"],
            activebackground=THEME["bg_root"], activeforeground=THEME["cyan"],
            selectcolor=THEME["bg_input"], relief="flat", highlightthickness=0
        ).pack(side="right")

        # Окно лога
        text_frame = tk.Frame(frame, bg=THEME["bg_input"], highlightbackground=THEME["border"], highlightthickness=1)
        text_frame.pack(fill="both", expand=True, padx=20, pady=(6, 8))

        self._log = tk.Text(
            text_frame, bg=THEME["bg_input"], fg=THEME["text_main"],
            font=FONTS["mono"], relief="flat",
            state="disabled", wrap="word",
            padx=12, pady=10,
        )

        # Цветовые теги
        self._log.tag_config("TIME", foreground=THEME["text_muted"])
        self._log.tag_config("INFO", foreground=THEME["cyan_hover"])
        self._log.tag_config("VOICE", foreground=THEME["amber"])
        self._log.tag_config("NLU", foreground=THEME["purple"])
        self._log.tag_config("ACTION", foreground=THEME["emerald"])
        self._log.tag_config("SYSTEM", foreground=THEME["blue"])
        self._log.tag_config("ERROR", foreground=THEME["coral"])

        sb = ttk.Scrollbar(text_frame, command=self._log.yview)
        self._log.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self._log.pack(side="left", fill="both", expand=True)

        # Нижняя панель действий логов
        log_actions = tk.Frame(frame, bg=THEME["bg_root"])
        log_actions.pack(fill="x", padx=20, pady=(0, 14))

        button_style = dict(font=FONTS["caption_bold"], fg=THEME["text_main"], bg=THEME["bg_card"],
                            activebackground=THEME["cyan"], activeforeground="#05080f", relief="flat", padx=12, pady=6, cursor="hand2")

        tk.Button(
            log_actions, text="🗑️  Очистить",
            fg=THEME["coral"], command=self._clear_logs_ui,
            font=FONTS["caption_bold"], bg=THEME["bg_card"], relief="flat", padx=12, pady=6, cursor="hand2"
        ).pack(side="left")

        tk.Button(
            log_actions, text="💾  Экспорт в файл...",
            command=self._export_logs, **button_style
        ).pack(side="left", padx=8)

        tk.Button(
            log_actions, text="📂  Открыть файл логов",
            command=self._open_log_file, **button_style
        ).pack(side="left")

        return frame

    def _set_log_filter(self, filter_key: str):
        self._log_filter = filter_key
        for k, btn in self._filter_buttons.items():
            if k == filter_key:
                btn.configure(bg=THEME["cyan"], fg="#05080f")
            else:
                btn.configure(bg=THEME["bg_card"], fg=THEME["text_sub"])
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

        # Подсветка активной кнопки на боковой панели
        for k, btn in self._nav_buttons.items():
            if k == key:
                btn.configure(fg=THEME["cyan"], bg=THEME["bg_hover"])
            else:
                btn.configure(fg=THEME["text_sub"], bg=THEME["bg_sidebar"])

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
