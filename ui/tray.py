import os
import threading
import pystray
from PIL import Image


class TrayApp:
    def __init__(self, main_window=None, on_exit_callback=None):
        self._main_window     = main_window
        self.on_exit_callback = on_exit_callback
        self._icon            = None

    def set_main_window(self, window):
        self._main_window = window

    def start(self):
        threading.Thread(target=self._run_tray, daemon=True).start()

    def _run_tray(self):
        icon_path = "assets/logo.jpg"
        image = (
            Image.open(icon_path)
            if os.path.exists(icon_path)
            else Image.new("RGB", (64, 64), color=(26, 127, 191))
        )
        menu = pystray.Menu(
            pystray.MenuItem("Открыть",   self._on_open,    default=True),
            pystray.MenuItem("Настройки", self._on_settings),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Выход",     self._on_exit),
        )
        self._icon = pystray.Icon(
            name="JARVIS", icon=image,
            title="Джарвис — активен", menu=menu,
        )
        self._icon.run()

    def _on_open(self, icon, item):
        if self._main_window:
            self._main_window.show()

    def _on_settings(self, icon, item):
        if self._main_window:
            self._main_window.root.after(0, self._build_settings_window)

    def _build_settings_window(self):
        import tkinter as tk
        from tkinter import messagebox
        from config.setup_wizard import load_config, save_config

        win = tk.Toplevel(self._main_window.root)
        win.title("Настройки Джарвиса")
        win.geometry("400x260")
        win.resizable(False, False)
        win.configure(bg="#070d17")
        win.attributes("-topmost", True)
        win.grab_set()

        tk.Label(win, text="Настройки", font=("Courier New", 13, "bold"),
                 fg="#1a7fbf", bg="#070d17").pack(pady=15)

        config = load_config()
        frame = tk.Frame(win, bg="#070d17")
        frame.pack(padx=30, fill="x")

        tk.Label(frame, text="Имя:", fg="white", bg="#070d17",
                 font=("Courier New", 9)).grid(row=0, column=0, sticky="w", pady=8)
        name_var = tk.StringVar(value=config.get("name", ""))
        tk.Entry(frame, textvariable=name_var, width=24, bg="#040912",
                 fg="#1a7fbf", insertbackground="#1a7fbf",
                 relief="flat").grid(row=0, column=1, padx=10)

        tk.Label(frame, text="Обращение:", fg="white", bg="#070d17",
                 font=("Courier New", 9)).grid(row=1, column=0, sticky="w", pady=8)
        honor_var = tk.StringVar(value=config.get("honorific", "сэр"))
        tk.Entry(frame, textvariable=honor_var, width=24, bg="#040912",
                 fg="#1a7fbf", insertbackground="#1a7fbf",
                 relief="flat").grid(row=1, column=1, padx=10)

        def save():
            config["name"]      = name_var.get().strip()
            config["honorific"] = honor_var.get().strip()
            save_config(config)
            messagebox.showinfo("Сохранено", "Настройки обновлены!", parent=win)
            win.destroy()

        tk.Button(win, text="Сохранить", command=save,
                  bg="#0d2035", fg="white", relief="flat",
                  padx=20, pady=6, font=("Courier New", 9)).pack(pady=18)

    def _on_exit(self, icon, item):
        icon.stop()
        if self._main_window:
            self._main_window.root.after(0, self._main_window.quit)
        if self.on_exit_callback:
            self.on_exit_callback()

    def stop(self):
        if self._icon:
            self._icon.stop()