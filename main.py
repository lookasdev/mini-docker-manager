import threading
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from docker_cli import (
    DockerCommandError,
    get_container_logs,
    inspect_container,
    list_containers,
    list_images,
    list_stats,
    pull_image,
    remove_container,
    remove_image,
    restart_container,
    run_container,
    start_container,
    stop_container,
)


class DockerManagerApp:
    REFRESH_INTERVAL_MS = 5000

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Mini Docker Manager")
        self.root.geometry("1280x720")
        self.root.minsize(1200, 720)

        self.auto_refresh = tk.BooleanVar(value=True)
        self.refresh_seconds = tk.IntVar(value=5)
        self.total_text = tk.StringVar(value="Total: 0")
        self.running_text = tk.StringVar(value="Running: 0")
        self.stopped_text = tk.StringVar(value="Stopped: 0")
        self.containers: list[dict] = []
        self.images: list[dict] = []
        self.stats: dict[str, dict] = {}
        self.images_window: tk.Toplevel | None = None
        self.images_table: ttk.Treeview | None = None
        self._after_job: str | None = None
        self._refresh_in_progress = False
        self._closing = False

        self._build_ui()
        self.refresh_data(notify_errors=False)
        self._schedule_refresh()

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(2, weight=1)
        self.root.rowconfigure(3, weight=1)

        header = ttk.Frame(self.root, padding=(12, 12, 12, 8))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)

        controls = ttk.Frame(header)
        controls.grid(row=0, column=0, sticky="ew")
        for index in range(4):
            controls.columnconfigure(index, weight=1)

        refresh_group = ttk.LabelFrame(controls, text="Refresh", style="Toolbar.TLabelframe")
        refresh_group.grid(row=0, column=0, padx=(0, 8), sticky="ew")
        ttk.Button(refresh_group, text="Refresh", style="Accent.TButton", command=self.refresh_data).grid(
            row=0, column=0, padx=6, pady=6, sticky="ew"
        )
        ttk.Checkbutton(refresh_group, text="Auto", variable=self.auto_refresh, command=self._toggle_auto_refresh).grid(
            row=0, column=1, padx=(0, 4)
        )
        refresh_spinbox = ttk.Spinbox(
            refresh_group,
            from_=1,
            to=60,
            width=4,
            textvariable=self.refresh_seconds,
            justify="center",
            command=self._on_refresh_seconds_change,
        )
        refresh_spinbox.grid(row=0, column=2, padx=(0, 4))
        refresh_spinbox.bind("<FocusOut>", self._on_refresh_seconds_change)
        refresh_spinbox.bind("<Return>", self._on_refresh_seconds_change)
        ttk.Label(refresh_group, text="sec").grid(row=0, column=3, padx=(0, 6))
        refresh_group.columnconfigure(0, weight=1)

        container_group = ttk.LabelFrame(controls, text="Containere", style="Toolbar.TLabelframe")
        container_group.grid(row=0, column=1, padx=(0, 8), sticky="ew")
        ttk.Button(container_group, text="Start", style="Success.TButton", command=self.start_selected).grid(
            row=0, column=0, padx=(6, 4), pady=6, sticky="ew"
        )
        ttk.Button(container_group, text="Restart", style="Primary.TButton", command=self.restart_selected).grid(
            row=0, column=1, padx=4, pady=6, sticky="ew"
        )
        ttk.Button(container_group, text="Stop", style="Danger.TButton", command=self.stop_selected).grid(
            row=0, column=2, padx=4, pady=6, sticky="ew"
        )
        
        ttk.Button(container_group, text="Remove", style="Danger.TButton", command=self.remove_selected_container).grid(
            row=0, column=3, padx=(4, 6), pady=6, sticky="ew"
        )
        for index in range(4):
            container_group.columnconfigure(index, weight=1)

        info_group = ttk.LabelFrame(controls, text="Detalii", style="Toolbar.TLabelframe")
        info_group.grid(row=0, column=2, padx=(0, 8), sticky="ew")
        ttk.Button(info_group, text="Logs", style="Primary.TButton", command=self.show_logs).grid(
            row=0, column=0, padx=(6, 4), pady=6, sticky="ew"
        )
        ttk.Button(info_group, text="Inspect", style="Primary.TButton", command=self.show_inspect).grid(
            row=0, column=1, padx=(4, 6), pady=6, sticky="ew"
        )
        for index in range(2):
            info_group.columnconfigure(index, weight=1)

        images_group = ttk.LabelFrame(controls, text="Imagini", style="Toolbar.TLabelframe")
        images_group.grid(row=0, column=3, sticky="ew")
        ttk.Button(images_group, text="Images", style="Primary.TButton", command=self.open_images_window).grid(
            row=0, column=0, padx=6, pady=6, sticky="ew"
        )
        images_group.columnconfigure(0, weight=1)

        summary = ttk.Frame(self.root, padding=(12, 0, 12, 10))
        summary.grid(row=1, column=0)

        summary_inner = ttk.Frame(summary)
        summary_inner.grid(row=0, column=0)

        ttk.Label(summary_inner, textvariable=self.total_text, anchor="center", relief="ridge", padding=(14, 5)).grid(
            row=0, column=0, padx=(0, 6)
        )
        ttk.Label(summary_inner, textvariable=self.running_text, anchor="center", relief="ridge", padding=(14, 5)).grid(
            row=0, column=1, padx=(0, 6)
        )
        ttk.Label(summary_inner, textvariable=self.stopped_text, anchor="center", relief="ridge", padding=(14, 5)).grid(
            row=0, column=2
        )

        containers_frame = ttk.LabelFrame(self.root, text="Containere Docker", padding=12)
        containers_frame.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 12))
        containers_frame.columnconfigure(0, weight=1)
        containers_frame.rowconfigure(0, weight=1)

        container_columns = ("id", "name", "image", "command", "ports", "status", "state")
        self.container_table = ttk.Treeview(containers_frame, columns=container_columns, show="headings", height=12)
        self.container_table.grid(row=0, column=0, sticky="nsew")
        self.container_table.bind("<<TreeviewSelect>>", self._on_container_select)

        headings = {
            "id": ("ID", 120),
            "name": ("Nume", 150),
            "image": ("Imagine", 180),
            "command": ("Command", 220),
            "ports": ("Ports", 160),
            "status": ("Status", 220),
            "state": ("State", 90),
        }
        for column, (label, width) in headings.items():
            self.container_table.heading(column, text=label)
            self.container_table.column(column, width=width, anchor="w")

        container_scroll = ttk.Scrollbar(containers_frame, orient="vertical", command=self.container_table.yview)
        container_scroll.grid(row=0, column=1, sticky="ns")
        self.container_table.configure(yscrollcommand=container_scroll.set)

        stats_frame = ttk.LabelFrame(self.root, text="Monitorizare resurse", padding=12)
        stats_frame.grid(row=3, column=0, sticky="nsew", padx=12, pady=(0, 12))
        stats_frame.columnconfigure(0, weight=1)
        stats_frame.rowconfigure(0, weight=1)

        stats_columns = ("id", "name", "cpu", "memory", "net_io", "block_io", "pids")
        self.stats_table = ttk.Treeview(
            stats_frame,
            columns=stats_columns,
            show="headings",
            height=10,
            selectmode="none",
            takefocus=False,
        )
        self.stats_table.grid(row=0, column=0, sticky="nsew")
        self.stats_table.bind("<<TreeviewSelect>>", self._clear_stats_selection)

        stats_headings = {
            "id": ("ID", 120),
            "name": ("Container", 180),
            "cpu": ("CPU", 90),
            "memory": ("Memorie folosita", 140),
            "net_io": ("Network I/O", 170),
            "block_io": ("Block I/O", 150),
            "pids": ("PIDs", 80),
        }
        for column, (label, width) in stats_headings.items():
            self.stats_table.heading(column, text=label)
            self.stats_table.column(column, width=width, anchor="w")

        stats_scroll = ttk.Scrollbar(stats_frame, orient="vertical", command=self.stats_table.yview)
        stats_scroll.grid(row=0, column=1, sticky="ns")
        self.stats_table.configure(yscrollcommand=stats_scroll.set)

    def refresh_data(self, notify_errors: bool = True) -> None:
        if self._refresh_in_progress:
            return

        self._refresh_in_progress = True

        threading.Thread(target=self._refresh_worker, args=(notify_errors,), daemon=True).start()

    def _refresh_worker(self, notify_errors: bool) -> None:
        try:
            containers = list_containers()
            stats = list_stats()
        except DockerCommandError as error:
            self._dispatch_refresh_result([], {}, notify_errors, error)
            return

        self._dispatch_refresh_result(containers, stats, notify_errors, None)

    def _dispatch_refresh_result(
        self,
        containers: list[dict],
        stats: dict[str, dict],
        notify_errors: bool,
        error: DockerCommandError | None,
    ) -> None:
        if self._closing:
            return

        try:
            self.root.after(0, self._apply_refresh_result, containers, stats, notify_errors, error)
        except tk.TclError:
            return

    def _apply_refresh_result(
        self,
        containers: list[dict],
        stats: dict[str, dict],
        notify_errors: bool,
        error: DockerCommandError | None,
    ) -> None:
        self._refresh_in_progress = False

        if error is not None:
            self.containers = []
            self.stats = {}
            self._populate_container_table([])
            self._populate_stats_table({})
            self._update_summary()
            if notify_errors:
                self._show_error(str(error))
            return

        self.containers = containers
        self.stats = stats
        self._populate_container_table(self.containers)
        self._populate_stats_table(self.stats)
        self._update_summary()

    def start_selected(self) -> None:
        container = self._require_selected_container("Start")
        if not container:
            return

        try:
            start_container(container["id"])
        except DockerCommandError as error:
            self._show_error(f"Start esuat pentru {container['name']}: {error}")
            return

        self.refresh_data(notify_errors=False)

    def stop_selected(self) -> None:
        container = self._require_selected_container("Stop")
        if not container:
            return

        try:
            stop_container(container["id"])
        except DockerCommandError as error:
            self._show_error(f"Stop esuat pentru {container['name']}: {error}")
            return

        self.refresh_data(notify_errors=False)

    def remove_selected_container(self) -> None:
        container = self._require_selected_container("Remove")
        if not container:
            return

        confirmed = messagebox.askyesno(
            "Confirmare stergere",
            f"Vrei sa stergi fortat containerul {container['name']}?",
            parent=self.root,
        )
        if not confirmed:
            return

        try:
            remove_container(container["id"])
        except DockerCommandError as error:
            self._show_error(f"stergere esuata pentru {container['name']}: {error}")
            return

        self.refresh_data(notify_errors=False)

    def restart_selected(self) -> None:
        container = self._require_selected_container("Restart")
        if not container:
            return

        try:
            restart_container(container["id"])
        except DockerCommandError as error:
            self._show_error(f"Restart esuat pentru {container['name']}: {error}")
            return

        self.refresh_data(notify_errors=False)

    def show_logs(self) -> None:
        container = self._require_selected_container("Logs")
        if not container:
            return

        try:
            output = get_container_logs(container["id"])
        except DockerCommandError as error:
            self._show_error(f"Logs indisponibile pentru {container['name']}: {error}")
            return

        self._show_output_window(f"Logs: {container['name']}", output or "Containerul nu are logs disponibile.")

    def show_inspect(self) -> None:
        container = self._require_selected_container("Inspect")
        if not container:
            return

        try:
            output = inspect_container(container["id"])
        except DockerCommandError as error:
            self._show_error(f"Inspect esuat pentru {container['name']}: {error}")
            return

        self._show_output_window(f"Inspect: {container['name']}", output)

    def open_images_window(self) -> None:
        if self.images_window is not None and self.images_window.winfo_exists():
            self.images_window.focus_force()
            self._refresh_images()
            return

        self.images_window = tk.Toplevel(self.root)
        self.images_window.title("Imagini Docker")
        self.images_window.geometry("820x420")
        self.images_window.minsize(760, 360)
        self.images_window.columnconfigure(0, weight=1)
        self.images_window.rowconfigure(1, weight=1)
        self.images_window.protocol("WM_DELETE_WINDOW", self._close_images_window)

        toolbar = ttk.Frame(self.images_window, padding=(12, 12, 12, 8))
        toolbar.grid(row=0, column=0, sticky="ew")
        toolbar.columnconfigure(0, weight=1)

        buttons = ttk.Frame(toolbar)
        buttons.grid(row=0, column=0, sticky="ew")
        for index in range(2):
            buttons.columnconfigure(index, weight=1)

        image_refresh_group = ttk.LabelFrame(buttons, text="Refresh", style="Toolbar.TLabelframe")
        image_refresh_group.grid(row=0, column=0, padx=(0, 8), sticky="ew")
        ttk.Button(image_refresh_group, text="Refresh", style="Accent.TButton", command=self._refresh_images).grid(
            row=0, column=0, padx=6, pady=6, sticky="ew"
        )
        image_refresh_group.columnconfigure(0, weight=1)

        image_actions_group = ttk.LabelFrame(buttons, text="Actiuni", style="Toolbar.TLabelframe")
        image_actions_group.grid(row=0, column=1, sticky="ew")
        ttk.Button(image_actions_group, text="Run", style="Success.TButton", command=self.run_container_dialog).grid(
            row=0, column=0, padx=4, pady=6, sticky="ew"
        )
        ttk.Button(image_actions_group, text="Pull", style="Primary.TButton", command=self.pull_image_dialog).grid(
            row=0, column=1, padx=(6, 4), pady=6, sticky="ew"
        )
        
        ttk.Button(image_actions_group, text="Remove", style="Danger.TButton", command=self.remove_selected_image).grid(
            row=0, column=2, padx=(4, 6), pady=6, sticky="ew"
        )
        for index in range(3):
            image_actions_group.columnconfigure(index, weight=1)

        frame = ttk.Frame(self.images_window, padding=(12, 0, 12, 12))
        frame.grid(row=1, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        image_columns = ("repository", "tag", "id", "size", "created")
        self.images_table = ttk.Treeview(frame, columns=image_columns, show="headings", height=10)
        self.images_table.grid(row=0, column=0, sticky="nsew")

        headers = {
            "repository": ("Repository", 210),
            "tag": ("Tag", 90),
            "id": ("ID", 140),
            "size": ("Size", 100),
            "created": ("Created", 140),
        }
        for column, (label, width) in headers.items():
            self.images_table.heading(column, text=label)
            self.images_table.column(column, width=width, anchor="w")

        scroll = ttk.Scrollbar(frame, orient="vertical", command=self.images_table.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.images_table.configure(yscrollcommand=scroll.set)

        self._refresh_images()

    def pull_image_dialog(self) -> None:
        image_name = simpledialog.askstring("Docker pull", "Imagine Docker de descarcat:", parent=self.images_window or self.root)
        if not image_name:
            return

        try:
            output = pull_image(image_name.strip())
        except DockerCommandError as error:
            self._show_error(f"Pull esuat pentru {image_name}: {error}", parent=self.images_window)
            return

        self._refresh_images()
        self._show_output_window(f"Pull: {image_name}", output or f"Imagine descarcata: {image_name}")

    def run_container_dialog(self) -> None:
        default_image = self._selected_image_ref()
        image_name = simpledialog.askstring(
            "Docker run",
            "Imagine de pornit:",
            initialvalue=default_image,
            parent=self.images_window or self.root,
        )
        if not image_name:
            return

        container_name = simpledialog.askstring(
            "Docker run",
            "Nume container (optional):",
            parent=self.images_window or self.root,
        )
        if container_name is None:
            return

        port_mapping = simpledialog.askstring(
            "Docker run",
            "Mapare porturi host:container (optional, ex. 8080:80):",
            parent=self.images_window or self.root,
        )
        if port_mapping is None:
            return

        program_name = simpledialog.askstring(
            "Docker run",
            "Program din container (optional, ex. /bin/bash):",
            parent=self.images_window or self.root,
        )
        if program_name is None:
            return

        command_text = simpledialog.askstring(
            "Docker run",
            "Comanda pentru -c (optional):",
            parent=self.images_window or self.root,
        )
        if command_text is None:
            return

        try:
            container_id = run_container(
                image_name.strip(),
                (container_name or "").strip(),
                (port_mapping or "").strip(),
                (program_name or "").strip(),
                (command_text or "").strip(),
            )
        except DockerCommandError as error:
            self._show_error(f"Run esuat pentru {image_name}: {error}", parent=self.images_window)
            return

        self.refresh_data(notify_errors=False)
        self._show_output_window("Docker run", f"Container nou creat cu ID:\n\n{container_id}")

    def remove_selected_image(self) -> None:
        image = self._get_selected_image()
        if not image:
            self._show_warning("Selecteaza o imagine pentru Remove Image.", parent=self.images_window)
            return

        confirmed = messagebox.askyesno(
            "Confirmare stergere imagine",
            f"Vrei sa stergi imaginea {image['ref']}?",
            parent=self.images_window or self.root,
        )
        if not confirmed:
            return

        try:
            remove_image(image["id"])
        except DockerCommandError as error:
            self._show_error(f"stergere imagine esuata pentru {image['ref']}: {error}", parent=self.images_window)
            return

        self._refresh_images()

    def _refresh_images(self) -> None:
        try:
            self.images = list_images()
        except DockerCommandError as error:
            self._show_error(f"Eroare imagini Docker: {error}", parent=self.images_window)
            if self.images_table is not None:
                self.images_table.delete(*self.images_table.get_children())
            return

        if self.images_table is not None:
            self.images_table.delete(*self.images_table.get_children())
            for image in self.images:
                self.images_table.insert(
                    "",
                    "end",
                    iid=image["id"],
                    values=(image["repository"], image["tag"], image["id"], image["size"], image["created"]),
                )

    def _get_refresh_interval_ms(self) -> int:
        try:
            seconds = int(self.refresh_seconds.get())
        except (tk.TclError, ValueError):
            seconds = 5

        seconds = max(1, min(seconds, 60))
        if self.refresh_seconds.get() != seconds:
            self.refresh_seconds.set(seconds)
        return seconds * 1000

    def _on_refresh_seconds_change(self, _event: object | None = None) -> None:
        if self.auto_refresh.get():
            self._schedule_refresh()

    def _get_selected_image(self) -> dict | None:
        if self.images_table is None:
            return None

        selection = self.images_table.selection()
        selected_id = selection[0] if selection else None
        for image in self.images:
            if image["id"] == selected_id:
                return image
        return None

    def _selected_image_ref(self) -> str:
        image = self._get_selected_image()
        return image["ref"] if image else ""

    def _close_images_window(self) -> None:
        if self.images_window is not None:
            self.images_window.destroy()
        self.images_window = None
        self.images_table = None

    def _populate_container_table(self, containers: list[dict]) -> None:
        selected_id = self._selected_container_id()
        self.container_table.delete(*self.container_table.get_children())

        for container in containers:
            self.container_table.insert(
                "",
                "end",
                iid=container["id"],
                values=(
                    container["id"],
                    container["name"],
                    container["image"],
                    container["command"],
                    container["ports"],
                    container["status"],
                    container["state"],
                ),
            )

        if selected_id and self.container_table.exists(selected_id):
            self.container_table.selection_set(selected_id)
            self.container_table.focus(selected_id)

    def _populate_stats_table(self, stats: dict[str, dict]) -> None:
        self.stats_table.delete(*self.stats_table.get_children())

        for container_id, row in stats.items():
            self.stats_table.insert(
                "",
                "end",
                iid=container_id,
                values=(
                    row["id"],
                    row["name"],
                    row["cpu"],
                    row["memory"],
                    row["net_io"],
                    row["block_io"],
                    row["pids"],
                ),
            )

    def _get_selected_container(self) -> dict | None:
        selected_id = self._selected_container_id()
        for container in self.containers:
            if container["id"] == selected_id:
                return container
        return None

    def _selected_container_id(self) -> str | None:
        selection = self.container_table.selection()
        return selection[0] if selection else None

    def _require_selected_container(self, action_name: str) -> dict | None:
        container = self._get_selected_container()
        if container is None:
            self._show_warning(f"Selecteaza un container pentru {action_name}.")
        return container

    def _on_container_select(self, _event: object) -> None:
        return

    def _clear_stats_selection(self, _event: object) -> None:
        selection = self.stats_table.selection()
        if selection:
            self.stats_table.selection_remove(selection)

    def _update_summary(self) -> None:
        running = sum(1 for container in self.containers if container["state"].lower() == "running")
        stopped = max(len(self.containers) - running, 0)
        self.total_text.set(f"Total: {len(self.containers)}")
        self.running_text.set(f"Running: {running}")
        self.stopped_text.set(f"Stopped: {stopped}")

    def _show_warning(self, message: str, parent: tk.Misc | None = None) -> None:
        messagebox.showwarning("Atentie", message, parent=parent or self.root)

    def _show_error(self, message: str, parent: tk.Misc | None = None) -> None:
        messagebox.showerror("Eroare", message, parent=parent or self.root)

    def _show_output_window(self, title: str, content: str) -> None:
        window = tk.Toplevel(self.root)
        window.title(title)
        window.geometry("860x500")

        frame = ttk.Frame(window, padding=12)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        text = tk.Text(frame, wrap="word", font=("Consolas", 10), padx=10, pady=10)
        text.grid(row=0, column=0, sticky="nsew")
        text.insert("1.0", content)
        text.configure(state="disabled")

        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        text.configure(yscrollcommand=scrollbar.set)

    def _toggle_auto_refresh(self) -> None:
        if self.auto_refresh.get():
            self._schedule_refresh()
        elif self._after_job is not None:
            self.root.after_cancel(self._after_job)
            self._after_job = None

    def _schedule_refresh(self) -> None:
        if self._after_job is not None:
            self.root.after_cancel(self._after_job)

        if self.auto_refresh.get():
            self._after_job = self.root.after(self._get_refresh_interval_ms(), self._auto_refresh)

    def _auto_refresh(self) -> None:
        self.refresh_data(notify_errors=False)
        self._schedule_refresh()

    def close(self) -> None:
        self._closing = True
        if self._after_job is not None:
            self.root.after_cancel(self._after_job)
            self._after_job = None
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure("TButton", padding=5)
    style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))
    style.configure("TLabelframe", padding=8)
    style.configure("Toolbar.TLabelframe", padding=6)
    style.configure("Primary.TButton", background="#d7e3fc", foreground="#1f3a5f")
    style.map("Primary.TButton", background=[("active", "#c7d7f8")])
    style.configure("Accent.TButton", background="#d8f3dc", foreground="#1b4332")
    style.map("Accent.TButton", background=[("active", "#c3ebc9")])
    style.configure("Success.TButton", background="#cfe7d8", foreground="#183a2a")
    style.map("Success.TButton", background=[("active", "#bddac9")])
    style.configure("Neutral.TButton", background="#e8ecef", foreground="#344054")
    style.map("Neutral.TButton", background=[("active", "#dde3e8")])
    style.configure("Danger.TButton", background="#f8d7da", foreground="#7a1f2a")
    style.map("Danger.TButton", background=[("active", "#f2c4c8")])
    app = DockerManagerApp(root)
    root.protocol("WM_DELETE_WINDOW", app.close)
    root.mainloop()


if __name__ == "__main__":
    main()