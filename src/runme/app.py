from __future__ import annotations

import platform
import queue
import shlex
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from datetime import datetime
from dataclasses import replace
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk
from typing import Callable, Dict, Optional, Tuple

from .models import Category, Command
from .storage import Storage


BG = "#111315"
PANEL = "#181b1f"
CARD = "#20252b"
CARD_ALT = "#252b32"
TEXT = "#f5f7fa"
MUTED = "#94a3b8"
ACCENT = "#6ee7b7"
ACCENT_DARK = "#1f5f52"
BORDER = "#2b3138"
DANGER = "#f97373"
ICON_BG = "#eef3f8"
ICON_FG = "#16202b"
ICON_DISABLED_BG = "#4b5563"
ICON_DISABLED_FG = "#cbd5e1"
CLICK_CURSOR = "pointinghand" if platform.system() == "Darwin" else "hand2"


def icon_path() -> Path:
    if getattr(sys, "_MEIPASS", None):
        return Path(sys._MEIPASS) / "runme" / "data" / "icon.png"
    return Path(__file__).resolve().parent / "data" / "icon.png"


class OutputManager:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.contents: Dict[str, str] = {}
        self.windows: Dict[str, tk.Toplevel] = {}
        self.text_widgets: Dict[str, tk.Text] = {}

    def set_output(self, command: Command, content: str) -> None:
        self.contents[command.id] = content
        text_widget = self.text_widgets.get(command.id)
        if text_widget is not None and text_widget.winfo_exists():
            self._write_text(text_widget, content)

    def show(self, command: Command) -> None:
        window = self.windows.get(command.id)
        if window is None or not window.winfo_exists():
            window = self._create_window(command)
        text_widget = self.text_widgets[command.id]
        if command.open_in_terminal:
            launched = command.last_run_at or "never"
            content = f"This command opens in a separate terminal window.\nLast launched: {launched}\n"
        else:
            content = self.contents.get(command.id, "(no output yet)\n")
        self._write_text(text_widget, content)
        window.deiconify()
        window.lift()

    def _create_window(self, command: Command) -> tk.Toplevel:
        window = tk.Toplevel(self.root)
        window.title(f"{command.name} Output")
        window.geometry("860x460")
        window.configure(bg=BG)
        window.transient(self.root)
        window.protocol("WM_DELETE_WINDOW", window.withdraw)

        text = tk.Text(
            window,
            bg="#0c0f12",
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            font=("Menlo", 12),
            padx=16,
            pady=16,
        )
        text.pack(fill="both", expand=True)
        text.configure(state="disabled")

        self.windows[command.id] = window
        self.text_widgets[command.id] = text
        return window

    def _write_text(self, text_widget: tk.Text, content: str) -> None:
        text_widget.configure(state="normal")
        text_widget.delete("1.0", "end")
        text_widget.insert("1.0", content)
        text_widget.see("end")
        text_widget.configure(state="disabled")


class CommandRunner:
    def __init__(
        self,
        root: tk.Tk,
        output_manager: OutputManager,
        on_status: Callable[[str, str], None],
    ) -> None:
        self.root = root
        self.output_manager = output_manager
        self.on_status = on_status
        self.output_queue: "queue.Queue[Tuple[str, object]]" = queue.Queue()
        self.root.after(100, self._flush_queue)

    def run(self, command: Command) -> None:
        self.on_status(command.id, "Running...", schedule_reset=False)
        target = self._run_in_terminal if command.open_in_terminal else self._run_embedded
        thread = threading.Thread(target=target, args=(command,), daemon=True)
        thread.start()

    def _run_embedded(self, command: Command) -> None:
        script_path = Path(command.script_path)
        cwd = Path(command.working_directory).expanduser() if command.working_directory else Path.home()
        try:
            process = subprocess.Popen(
                ["bash", str(script_path)],
                cwd=str(cwd),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            output, _ = process.communicate()
            code = process.returncode or 0
            status = f"Finished {command.last_run_at}" if code == 0 else f"Failed ({code})"
            header = f"Started: {command.last_run_at}\nCompleted: {timestamp_now()}\n\n"
            content = header + (output or "(no output)\n")
        except Exception as exc:
            status = "Failed"
            content = f"Started: {command.last_run_at}\nFailed: {timestamp_now()}\n\n{exc}\n"

        self.output_queue.put((command.id, status))
        self.output_queue.put(("output", (command, content)))

    def _run_in_terminal(self, command: Command) -> None:
        script_path = Path(command.script_path)
        cwd = Path(command.working_directory).expanduser() if command.working_directory else Path.home()
        system = platform.system()
        try:
            if system == "Darwin":
                terminal_command = (
                    f'cd {shlex.quote(str(cwd))}; '
                    f'bash {shlex.quote(str(script_path))}; '
                    'exec $SHELL'
                )
                subprocess.Popen(
                    [
                        "osascript",
                        "-e",
                        'tell application "Terminal" to activate',
                        "-e",
                        f'tell application "Terminal" to do script "{terminal_command}"',
                    ],
                    start_new_session=True,
                )
                self.output_queue.put((command.id, f"Opened {command.last_run_at}"))
                return

            linux_options = [
                ["x-terminal-emulator", "-e", f"bash -lc 'cd {shlex.quote(str(cwd))}; bash {shlex.quote(str(script_path))}; exec $SHELL'"],
                ["gnome-terminal", "--", "bash", "-lc", f"cd {shlex.quote(str(cwd))}; bash {shlex.quote(str(script_path))}; exec $SHELL"],
                ["konsole", "-e", "bash", "-lc", f"cd {shlex.quote(str(cwd))}; bash {shlex.quote(str(script_path))}; exec $SHELL"],
                ["xfce4-terminal", "-e", f"bash -lc 'cd {shlex.quote(str(cwd))}; bash {shlex.quote(str(script_path))}; exec $SHELL'"],
                ["xterm", "-e", f"bash -lc 'cd {shlex.quote(str(cwd))}; bash {shlex.quote(str(script_path))}; exec $SHELL'"],
            ]
            for candidate in linux_options:
                if shutil.which(candidate[0]):
                    subprocess.Popen(candidate, start_new_session=True)
                    self.output_queue.put((command.id, f"Opened {command.last_run_at}"))
                    return
            raise RuntimeError("No supported terminal emulator found")
        except Exception as exc:
            self.output_queue.put((command.id, "Failed"))
            self.output_queue.put(("output", (command, f"{exc}\n")))

    def _flush_queue(self) -> None:
        while True:
            try:
                key, value = self.output_queue.get_nowait()
            except queue.Empty:
                break
            if key == "output":
                command, content = value
                self.output_manager.set_output(command, content)
            else:
                self.on_status(str(key), str(value), schedule_reset=True)
        self.root.after(100, self._flush_queue)


def timestamp_now() -> str:
    now = datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S.") + f"{int(now.microsecond / 1000):03d}"


class CommandEditor(tk.Toplevel):
    def __init__(
        self,
        master: tk.Tk,
        storage: Storage,
        category: Category,
        command: Optional[Command],
        on_save: Callable[[Category, Command, str], None],
    ) -> None:
        super().__init__(master)
        self.storage = storage
        self.category = category
        self.command = command
        self.on_save = on_save
        self.title("Edit Command" if command else "Add Command")
        self.geometry("860x680")
        self.configure(bg=BG)
        self.transient(master)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        header = tk.Frame(self, bg=BG)
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(24, 12))

        tk.Label(header, text="Command", bg=BG, fg=TEXT, font=("Helvetica", 22, "bold")).pack(anchor="w")
        tk.Label(
            header,
            text="Edit the shell script, choose a working directory, and decide whether it should open in a new terminal.",
            bg=BG,
            fg=MUTED,
            font=("Helvetica", 11),
        ).pack(anchor="w", pady=(6, 0))

        form = tk.Frame(self, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        form.grid(row=1, column=0, sticky="nsew", padx=24, pady=(0, 24))
        form.columnconfigure(0, weight=1)
        form.rowconfigure(7, weight=1)

        self.name_var = tk.StringVar(value=command.name if command else "")
        self.cwd_var = tk.StringVar(value=command.working_directory if command else str(Path.home()))
        self.open_in_terminal_var = tk.BooleanVar(value=command.open_in_terminal if command else False)

        self._field(form, "Name", 0)
        name_entry = ttk.Entry(form, textvariable=self.name_var)
        name_entry.grid(row=1, column=0, sticky="ew", padx=18)

        self._field(form, "Working Directory", 2)
        ttk.Entry(form, textvariable=self.cwd_var).grid(row=3, column=0, sticky="ew", padx=18)

        self.terminal_toggle = tk.Checkbutton(
            form,
            text="Open in a new terminal window when run",
            variable=self.open_in_terminal_var,
            indicatoron=False,
            anchor="w",
            selectcolor=ACCENT_DARK,
            bg=CARD_ALT,
            fg=TEXT,
            activebackground="#313841",
            activeforeground=TEXT,
            relief="flat",
            padx=12,
            pady=10,
            cursor=CLICK_CURSOR,
            font=("Helvetica", 11),
        )
        self.terminal_toggle.grid(row=4, column=0, sticky="ew", padx=18, pady=(18, 8))

        self._field(form, "Shell Script", 5)
        self.script_text = tk.Text(
            form,
            bg="#0c0f12",
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            font=("Menlo", 12),
            padx=14,
            pady=14,
        )
        self.script_text.grid(row=7, column=0, sticky="nsew", padx=18, pady=(0, 18))
        initial_script = storage.read_script(command.script_path) if command else "#!/usr/bin/env bash\n\n"
        self.script_text.insert("1.0", initial_script)

        footer = tk.Frame(form, bg=PANEL)
        footer.grid(row=8, column=0, sticky="ew", padx=18, pady=(0, 18))

        cancel_button = ttk.Button(footer, text="Cancel", command=self.destroy)
        cancel_button.pack(side="right")
        cancel_button.configure(cursor=CLICK_CURSOR)

        save_button = ttk.Button(footer, text="Save", command=self._save)
        save_button.pack(side="right", padx=(0, 12))
        save_button.configure(cursor=CLICK_CURSOR)
        name_entry.focus_set()

    def _field(self, parent: tk.Widget, label: str, row: int) -> None:
        tk.Label(parent, text=label, bg=PANEL, fg=MUTED, font=("Helvetica", 10, "bold")).grid(
            row=row,
            column=0,
            sticky="w",
            padx=18,
            pady=(18, 8),
        )

    def _save(self) -> None:
        name = self.name_var.get().strip()
        cwd = self.cwd_var.get().strip()
        script = self.script_text.get("1.0", "end").rstrip() + "\n"
        if not name:
            messagebox.showerror("Missing name", "Command name is required.")
            return
        if not cwd:
            messagebox.showerror("Missing directory", "Working directory is required.")
            return

        if self.command:
            command = replace(
                self.command,
                name=name,
                working_directory=cwd,
                open_in_terminal=self.open_in_terminal_var.get(),
            )
            self.storage.update_script(command.script_path, script)
        else:
            command = Command.create(name=name, working_directory=cwd, script_path="")
            command.script_path = self.storage.create_script(command.id, script)
            command.open_in_terminal = self.open_in_terminal_var.get()

        self.on_save(self.category, command, script)
        self.destroy()


class RunMeApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("RunMe")
        self.root.geometry("1280x820")
        self.root.configure(bg=BG)
        self.icon_image: Optional[tk.PhotoImage] = None

        self.storage = Storage()
        self.state = self.storage.load()
        self.status_vars: Dict[str, tk.StringVar] = {}
        self.last_run_vars: Dict[str, tk.StringVar] = {}
        self.status_reset_jobs: Dict[str, str] = {}
        self.card_columns = 1
        self.card_width = 260

        self._configure_style()
        self._configure_icon()
        self.output_manager = OutputManager(root)
        self.runner = CommandRunner(root, self.output_manager, self._set_status)

        self._build_shell()
        self.render()

    def _configure_style(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background=BG)
        style.configure("TLabel", background=BG, foreground=TEXT)
        style.configure("TButton", background=ACCENT_DARK, foreground=TEXT, borderwidth=0, padding=10)
        style.map("TButton", background=[("active", "#2a7c6b")])
        style.configure("Secondary.TButton", background=CARD_ALT, foreground=TEXT)
        style.map("Secondary.TButton", background=[("active", "#313841")])
        style.configure("Danger.TButton", background="#6f2c2c", foreground=TEXT)
        style.map("Danger.TButton", background=[("active", "#8f3b3b")])
        style.configure("TEntry", fieldbackground="#0c0f12", foreground=TEXT, bordercolor=BORDER)
        style.configure("TCheckbutton", background=PANEL, foreground=TEXT)

    def _configure_icon(self) -> None:
        path = icon_path()
        if not path.exists():
            return
        try:
            self.icon_image = tk.PhotoImage(file=str(path))
            self.root.iconphoto(True, self.icon_image)
        except tk.TclError:
            pass

    def _build_shell(self) -> None:
        top = tk.Frame(self.root, bg=BG)
        top.pack(fill="x", padx=24, pady=(20, 12))

        tk.Label(top, text="RunMe", bg=BG, fg=TEXT, font=("Helvetica", 28, "bold")).pack(anchor="w")
        tk.Label(
            top,
            text="Launch saved shell scripts without opening a terminal first.",
            bg=BG,
            fg=MUTED,
            font=("Helvetica", 12),
        ).pack(anchor="w", pady=(6, 0))

        actions = tk.Frame(self.root, bg=BG)
        actions.pack(fill="x", padx=24, pady=(0, 12))

        create_button = ttk.Button(actions, text="Create Category", command=self.create_category)
        create_button.pack(side="left")
        create_button.configure(cursor=CLICK_CURSOR)

        container = tk.Frame(self.root, bg=BG)
        container.pack(fill="both", expand=True, padx=24, pady=(0, 24))

        self.canvas = tk.Canvas(container, bg=BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        self.scroll_frame = tk.Frame(self.canvas, bg=BG)

        self.scroll_frame.bind(
            "<Configure>",
            lambda _: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )

        self.canvas_window = self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.root.bind_all("<MouseWheel>", self._on_mousewheel, add="+")
        self.root.bind_all("<Button-4>", self._on_linux_scroll_up, add="+")
        self.root.bind_all("<Button-5>", self._on_linux_scroll_down, add="+")

    def render(self) -> None:
        for child in self.scroll_frame.winfo_children():
            child.destroy()
        self.status_vars = {}
        self.last_run_vars = {}
        self._update_card_metrics()

        if not self.state.categories:
            empty = tk.Frame(self.scroll_frame, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
            empty.pack(fill="x", pady=12)
            tk.Label(
                empty,
                text="No categories yet. Create one to start adding commands.",
                bg=PANEL,
                fg=MUTED,
                font=("Helvetica", 12),
                padx=20,
                pady=20,
            ).pack(anchor="w")
            return

        for category in self.state.categories:
            self._render_category(category)

    def _render_category(self, category: Category) -> None:
        section = tk.Frame(self.scroll_frame, bg=BG)
        section.pack(fill="x", pady=18)

        header = tk.Frame(section, bg=BG)
        header.pack(fill="x", pady=(0, 14))

        tk.Label(header, text=category.name, bg=BG, fg=TEXT, font=("Helvetica", 20, "bold")).pack(side="left")
        line = tk.Frame(header, bg=BORDER, height=1)
        line.pack(side="left", fill="x", expand=True, padx=16, pady=(15, 0))
        add_button = ttk.Button(
            header,
            text="Add Command",
            command=lambda cat=category: self.open_editor(cat, None),
            style="Secondary.TButton",
        )
        add_button.pack(side="right")
        add_button.configure(cursor=CLICK_CURSOR)

        cards = tk.Frame(section, bg=BG)
        cards.pack(fill="x")

        if not category.commands:
            empty = tk.Frame(cards, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
            empty.pack(fill="x")
            tk.Label(
                empty,
                text="No commands in this category yet.",
                bg=PANEL,
                fg=MUTED,
                font=("Helvetica", 11),
                padx=18,
                pady=18,
            ).pack(anchor="w")
            return

        columns = self.card_columns
        for column in range(columns):
            cards.grid_columnconfigure(column, weight=1, uniform=f"category-{category.id}")

        for index, command in enumerate(category.commands):
            card = tk.Frame(
                cards,
                bg=CARD if index % 2 == 0 else CARD_ALT,
                highlightbackground=BORDER,
                highlightthickness=1,
                width=self.card_width,
                height=136,
            )
            row = index // columns
            column = index % columns
            padx = (0, 16) if column < columns - 1 else (0, 0)
            pady = (0, 16) if row == 0 else (16, 0)
            card.grid(row=row, column=column, padx=padx, pady=pady, sticky="nsew")
            card.grid_propagate(False)
            self._render_command_card(card, category, command)

    def _render_command_card(self, parent: tk.Frame, category: Category, command: Command) -> None:
        top = tk.Frame(parent, bg=parent["bg"])
        top.pack(fill="x", padx=14, pady=(14, 8))

        play = tk.Button(
            top,
            text="▶",
            bg=ACCENT,
            fg="#06261d",
            font=("Helvetica", 16, "bold"),
            relief="flat",
            width=3,
            height=1,
            command=lambda cmd=command: self.run_command(cmd),
            cursor=CLICK_CURSOR,
            activebackground="#90f3cd",
            activeforeground="#06261d",
        )
        play.pack(side="left")

        text_block = tk.Frame(top, bg=parent["bg"])
        text_block.pack(side="left", fill="x", expand=True, padx=(10, 0))

        tk.Label(text_block, text=command.name, bg=parent["bg"], fg=TEXT, font=("Helvetica", 13, "bold")).pack(anchor="w")
        tk.Label(
            text_block,
            text=Path(command.working_directory).expanduser(),
            bg=parent["bg"],
            fg=MUTED,
            font=("Helvetica", 9),
            wraplength=max(120, self.card_width - 92),
            anchor="w",
            justify="left",
        ).pack(anchor="w", pady=(4, 0))

        meta = tk.Frame(parent, bg=parent["bg"])
        meta.pack(fill="x", padx=14, pady=(0, 10))

        status_var = tk.StringVar(value="Idle")
        self.status_vars[command.id] = status_var
        tk.Label(meta, textvariable=status_var, bg=parent["bg"], fg=ACCENT, font=("Helvetica", 10)).pack(side="left")
        terminal_label = "Terminal" if command.open_in_terminal else "Inline"
        tk.Label(meta, text=terminal_label, bg=parent["bg"], fg=MUTED, font=("Helvetica", 9)).pack(side="right")

        last_run_var = tk.StringVar(value=self._format_last_run(command))
        self.last_run_vars[command.id] = last_run_var
        tk.Label(parent, textvariable=last_run_var, bg=parent["bg"], fg=MUTED, font=("Helvetica", 9)).pack(
            anchor="w",
            padx=14,
            pady=(0, 10),
        )

        actions = tk.Frame(parent, bg=parent["bg"])
        actions.pack(fill="x", padx=12, pady=(0, 14))

        self._icon_button(actions, "✎", lambda cat=category, cmd=command: self.open_editor(cat, cmd), "Edit").pack(
            side="left", padx=3
        )
        self._icon_button(actions, "⧉", lambda cat=category, cmd=command: self.clone_command(cat, cmd), "Clone").pack(
            side="left", padx=3
        )
        self._icon_button(
            actions,
            "⌁",
            lambda cmd=command: self.output_manager.show(cmd),
            "Output",
            disabled=command.open_in_terminal,
        ).pack(side="left", padx=3)
        self._icon_button(
            actions,
            "✕",
            lambda cat=category, cmd=command: self.delete_command(cat, cmd),
            "Delete",
            danger=True,
        ).pack(side="right", padx=3)

    def _icon_button(
        self,
        parent: tk.Frame,
        symbol: str,
        command: Callable[[], None],
        label: str,
        danger: bool = False,
        disabled: bool = False,
    ) -> tk.Button:
        background = "#f5d0d0" if danger else ICON_BG
        foreground = "#7f1d1d" if danger else ICON_FG
        active = "#ef4444" if danger else "#d7e2ec"
        state = "disabled" if disabled else "normal"
        if disabled:
            background = ICON_DISABLED_BG
            foreground = ICON_DISABLED_FG
            active = ICON_DISABLED_BG
        return tk.Button(
            parent,
            text=symbol,
            command=command,
            bg=background,
            activebackground=active,
            fg=foreground,
            activeforeground=foreground,
            relief="solid",
            bd=1,
            state=state,
            width=2,
            height=1,
            cursor=CLICK_CURSOR,
            font=("Helvetica", 12, "bold"),
            padx=10,
            pady=7,
        )

    def _on_canvas_configure(self, event: tk.Event) -> None:
        self.canvas.itemconfigure(self.canvas_window, width=event.width)
        self._update_card_metrics(event.width)

    def _is_in_scroll_area(self, widget: tk.Widget) -> bool:
        current: Optional[tk.Widget] = widget
        while current is not None:
            if current is self.canvas or current is self.scroll_frame:
                return True
            current = current.master
        return False

    def _on_mousewheel(self, event: tk.Event) -> str:
        widget_under_pointer = self.root.winfo_containing(event.x_root, event.y_root)
        if widget_under_pointer is None or not self._is_in_scroll_area(widget_under_pointer):
            return ""
        if platform.system() == "Darwin":
            delta = -int(event.delta)
            if delta == 0:
                delta = -1 if event.delta > 0 else 1
        else:
            delta = -int(event.delta / 120) if event.delta else 0
            if delta == 0 and event.delta:
                delta = -1 if event.delta > 0 else 1
        if delta:
            self.canvas.yview_scroll(delta, "units")
        return "break"

    def _on_linux_scroll_up(self, event: tk.Event) -> str:
        widget_under_pointer = self.root.winfo_containing(event.x_root, event.y_root)
        if widget_under_pointer is None or not self._is_in_scroll_area(widget_under_pointer):
            return ""
        self.canvas.yview_scroll(-1, "units")
        return "break"

    def _on_linux_scroll_down(self, event: tk.Event) -> str:
        widget_under_pointer = self.root.winfo_containing(event.x_root, event.y_root)
        if widget_under_pointer is None or not self._is_in_scroll_area(widget_under_pointer):
            return ""
        self.canvas.yview_scroll(1, "units")
        return "break"

    def _update_card_metrics(self, canvas_width: Optional[int] = None) -> None:
        width = canvas_width if canvas_width is not None else self.canvas.winfo_width()
        if width <= 1:
            width = max(960, self.root.winfo_width() - 48)
        available_width = max(320, width - 24)
        self.card_columns = max(1, min(5, (available_width + 16) // 256))
        self.card_width = max(220, int((available_width - (16 * (self.card_columns - 1))) / self.card_columns))

    def create_category(self) -> None:
        name = simpledialog.askstring("Create Category", "Category name:", parent=self.root)
        if not name:
            return
        self.state.categories.append(Category.create(name.strip()))
        self._persist_and_render()

    def open_editor(self, category: Category, command: Optional[Command]) -> None:
        CommandEditor(self.root, self.storage, category, command, self.save_command)

    def save_command(self, category: Category, command: Command, _: str) -> None:
        existing = next((index for index, item in enumerate(category.commands) if item.id == command.id), None)
        if existing is None:
            category.commands.append(command)
        else:
            category.commands[existing] = command
        self._persist_and_render()

    def clone_command(self, category: Category, source: Command) -> None:
        clone = Command.create(
            name=f"{source.name} Copy",
            working_directory=source.working_directory,
            script_path="",
        )
        clone.open_in_terminal = source.open_in_terminal
        clone.script_path = self.storage.clone_script(source.script_path, clone.id)
        category.commands.append(clone)
        self._persist_and_render()

    def delete_command(self, category: Category, command: Command) -> None:
        confirmed = messagebox.askyesno("Delete Command", f"Delete '{command.name}'?")
        if not confirmed:
            return
        category.commands = [item for item in category.commands if item.id != command.id]
        self.storage.delete_script(command.script_path)
        self._persist_and_render()

    def run_command(self, command: Command) -> None:
        try:
            command.last_run_at = timestamp_now()
            self.storage.save(self.state)
            self._set_last_run(command.id, self._format_last_run(command))
            self.runner.run(command)
        except Exception as exc:
            self._set_status(command.id, "Failed", schedule_reset=True)
            self.output_manager.set_output(command, f"Started: {command.last_run_at}\nFailed: {timestamp_now()}\n\n{exc}\n")
            self.output_manager.show(command)

    def _persist_and_render(self) -> None:
        self.storage.save(self.state)
        self.render()

    def _set_status(self, command_id: str, status: str, schedule_reset: bool = False) -> None:
        status_var = self.status_vars.get(command_id)
        if status_var is not None:
            status_var.set(status)
        existing_job = self.status_reset_jobs.pop(command_id, None)
        if existing_job is not None:
            self.root.after_cancel(existing_job)
        if schedule_reset:
            self.status_reset_jobs[command_id] = self.root.after(3500, lambda: self._reset_status(command_id))

    def _reset_status(self, command_id: str) -> None:
        self.status_reset_jobs.pop(command_id, None)
        status_var = self.status_vars.get(command_id)
        if status_var is not None:
            status_var.set("Idle")

    def _set_last_run(self, command_id: str, value: str) -> None:
        last_run_var = self.last_run_vars.get(command_id)
        if last_run_var is not None:
            last_run_var.set(value)

    def _format_last_run(self, command: Command) -> str:
        return f"Last run: {command.last_run_at}" if command.last_run_at else "Last run: never"


def main() -> None:
    root = tk.Tk()
    app = RunMeApp(root)
    root.minsize(980, 680)
    root.mainloop()


if __name__ == "__main__":
    main()
