import json
import os
import tkinter as tk
from tkinter import ttk, messagebox


CONFIG_PATH = "config/user_config.json"


def is_first_run() -> bool:
    return not os.path.exists(CONFIG_PATH)


def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(config: dict):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


class SetupWizard:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Джарвис — первая настройка")
        self.root.geometry("450x480")
        self.root.resizable(False, False)

        self.name_var = tk.StringVar()
        self.honorific_var = tk.StringVar(value="sir")
        self.drives_var = tk.StringVar()

        self._build_ui()

    def _build_ui(self):
        tk.Label(
            self.root,
            text="Добро пожаловать в Джарвис!",
            font=("Arial", 14, "bold"),
        ).pack(pady=15)

        # Имя
        tk.Label(
            self.root,
            text="Как вас зовут?",
            font=("Arial", 10),
        ).pack(anchor="w", padx=30, pady=(10, 5))
        self.name_entry = tk.Entry(
            self.root,
            textvariable=self.name_var,
            width=30,
            font=("Arial", 10),
        )
        self.name_entry.pack(padx=30, pady=(0, 10))

        tk.Label(
            self.root,
            text="Как к вам обращаться?",
            font=("Arial", 10),
        ).pack(anchor="w", padx=30, pady=(10, 5))

        honor_frame = tk.Frame(self.root)
        honor_frame.pack(anchor="w", padx=30, pady=(5, 10))

        tk.Radiobutton(
            honor_frame,
            text="Сэр",
            variable=self.honorific_var,
            value="sir",
        ).pack(anchor="w")
        tk.Radiobutton(
            honor_frame,
            text="Мадам",
            variable=self.honorific_var,
            value="madam",
        ).pack(anchor="w")
        tk.Radiobutton(
            honor_frame,
            text="Свое обращение:",
            variable=self.honorific_var,
            value="custom",
        ).pack(anchor="w")

        self.custom_entry = tk.Entry(
            honor_frame,
            width=20,
            font=("Arial", 10),
            state="disabled",
        )
        self.custom_entry.pack(anchor="w", padx=(20, 0), pady=(5, 0))

        self.honorific_var.trace("w", self._on_honorific_change)

        tk.Label(
            self.root,
            text="Дополнительные диски (через запятую, без :) ?",
            font=("Arial", 10),
        ).pack(anchor="w", padx=30, pady=(15, 5))
        tk.Label(
            self.root,
            text="Пример: D, E, F",
            font=("Arial", 8),
        ).pack(anchor="w", padx=30)

        self.drives_entry = tk.Entry(
            self.root,
            textvariable=self.drives_var,
            width=30,
            font=("Arial", 10),
        )
        self.drives_entry.pack(padx=30, pady=(5, 10))

        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=20)

        tk.Button(
            btn_frame,
            text="Завершить настройку",
            command=self._finish_setup,
            bg="lightblue",
            font=("Arial", 10),
            width=15,
        ).pack(side="left", padx=5)

        tk.Button(
            btn_frame,
            text="Отмена",
            command=self.root.quit,
            font=("Arial", 10),
            width=10,
        ).pack(side="left", padx=5)

    def _on_honorific_change(self, *args):
        if self.honorific_var.get() == "custom":
            self.custom_entry.config(state="normal")
        else:
            self.custom_entry.config(state="disabled")

    def _parse_drives(self, drives_input: str) -> list:
        extra_drives = []
        if not drives_input.strip():
            return extra_drives

        for drive in drives_input.split(","):
            drive = drive.strip().upper().replace(":", "").replace("/", "")
            if drive:
                extra_drives.append(f"{drive}:/")
        return extra_drives

    def _finish_setup(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showwarning("Ошибка", "Введите имя.")
            return

        honor_choice = self.honorific_var.get()
        if honor_choice == "custom":
            custom_honor = self.custom_entry.get().strip()
            if not custom_honor:
                messagebox.showwarning("Ошибка", "Введите своё обращение.")
                return
            honorific = custom_honor
        elif honor_choice == "madam":
            honorific = "мадам"
        else:  # sir
            honorific = "сэр"

        voice = "en-GB-SoniaNeural" if honorific in ["мадам", "госпожа"] else "en-GB-RyanNeural"
        pitch = "+0Hz" if voice == "en-GB-SoniaNeural" else "-10Hz"

        drives_input = self.drives_var.get()
        extra_drives = self._parse_drives(drives_input)

        config = {
            "name": name,
            "honorific": honorific,
            "voice": voice,
            "speed": "-5%",
            "pitch": pitch,
            "extra_drives": extra_drives,
        }

        save_config(config)
        messagebox.showinfo("Готово", f"Добро пожаловать, {name}!")
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def run_setup() -> dict:
    if not is_first_run():
        return load_config()

    SetupWizard().run()
    return load_config()