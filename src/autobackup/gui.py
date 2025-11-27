import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from autobackup.scheduler import BackupScheduler
from autobackup.db import SessionLocal
from autobackup.models import BackupJob
from autobackup.backup_engine import run_backup_for_job


class AutoBackupApp(tk.Tk):
    def __init__(self, scheduler: BackupScheduler):
        super().__init__()

        self.scheduler = scheduler

        self.title("AutoBackup Manager")
        self.geometry("800x500")

        self._build_layout()

    def _build_layout(self) -> None:
        self._build_header()
        self._build_job_list()
        self._load_jobs()

    def _build_header(self) -> None:
        header_frame = ttk.Frame(self)
        header_frame.pack(fill="x", padx=10, pady=10)

        title_label = ttk.Label(
            header_frame,
            text="AutoBackup Manager",
            font=("Segoe UI", 16, "bold"),
        )
        title_label.pack(side="left")

        buttons_frame = ttk.Frame(header_frame)
        buttons_frame.pack(side="right")

        add_button = ttk.Button(
            buttons_frame,
            text="Add Job",
            command=self._open_add_job_window,
        )
        add_button.pack(side="left", padx=(0, 5))

        run_button = ttk.Button(
            header_frame,
            text="Run Now",
            command=self._run_selected_job,
        )
        run_button.pack(side="left", padx=(5, 0))

        refresh_button = ttk.Button(
            header_frame,
            text="Refresh",
            command=self._load_jobs,
        )
        refresh_button.pack(side="left")

    def _browse_directory(self, target_var: tk.StringVar) -> None:
        directory = filedialog.askdirectory()
        if directory:
            target_var.set(directory)


    def _open_add_job_window(self) -> None:
        window = tk.Toplevel(self)
        window.title("Add Backup Job")
        window.geometry("500x300")
        window.grab_set()

        name_var = tk.StringVar()
        source_var = tk.StringVar()
        destination_var = tk.StringVar()
        schedule_var = tk.StringVar(value="manual")
        interval_var = tk.StringVar()

        form_frame = ttk.Frame(window)
        form_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Name
        ttk.Label(form_frame, text="Name:").grid(row=0, column=0, sticky="w")
        name_entry = ttk.Entry(form_frame, textvariable=name_var, width=40)
        name_entry.grid(row=0, column=1, columnspan=2, sticky="we", pady=5)

        # Source path
        ttk.Label(form_frame, text="Source path:").grid(row=1, column=0, sticky="w")
        source_entry = ttk.Entry(form_frame, textvariable=source_var, width=35)
        source_entry.grid(row=1, column=1, sticky="we", pady=5)
        source_button = ttk.Button(
            form_frame,
            text="Browse",
            command=lambda: self._browse_directory(source_var),
        )
        source_button.grid(row=1, column=2, padx=5)

        # Destination path
        ttk.Label(form_frame, text="Destination path:").grid(row=2, column=0, sticky="w")
        destination_entry = ttk.Entry(form_frame, textvariable=destination_var, width=35)
        destination_entry.grid(row=2, column=1, sticky="we", pady=5)
        destination_button = ttk.Button(
            form_frame,
            text="Browse",
            command=lambda: self._browse_directory(destination_var),
        )
        destination_button.grid(row=2, column=2, padx=5)

        # Schedule type
        ttk.Label(form_frame, text="Schedule type:").grid(row=3, column=0, sticky="w")
        schedule_combo = ttk.Combobox(
            form_frame,
            textvariable=schedule_var,
            values=["manual", "interval", "daily"],
            state="readonly",
            width=15,
        )
        schedule_combo.grid(row=3, column=1, sticky="w", pady=5)
        schedule_combo.current(0)

        # Interval minutes (used when schedule_type == "interval")
        ttk.Label(form_frame, text="Interval (minutes):").grid(row=4, column=0, sticky="w")
        interval_entry = ttk.Entry(form_frame, textvariable=interval_var, width=10)
        interval_entry.grid(row=4, column=1, sticky="w", pady=5)

        # Buttons
        buttons_frame = ttk.Frame(window)
        buttons_frame.pack(fill="x", padx=10, pady=(0, 10))

        def on_save() -> None:
            name = name_var.get().strip()
            source_path = source_var.get().strip()
            destination_path = destination_var.get().strip()
            schedule_type = schedule_var.get()
            interval_minutes = None

            if not name or not source_path or not destination_path:
                messagebox.showwarning(
                    "Missing data",
                    "Name, source path and destination path are required.",
                )
                return

            if schedule_type == "interval":
                raw_interval = interval_var.get().strip()
                if not raw_interval:
                    messagebox.showwarning(
                        "Missing interval",
                        "Interval minutes are required for interval schedule.",
                    )
                    return
                try:
                    interval_minutes = int(raw_interval)
                    if interval_minutes <= 0:
                        raise ValueError
                except ValueError:
                    messagebox.showerror(
                        "Invalid interval",
                        "Interval must be a positive integer.",
                    )
                    return

            db = SessionLocal()
            try:
                job = BackupJob(
                    name=name,
                    source_path=source_path,
                    destination_path=destination_path,
                    schedule_type=schedule_type,
                    interval_minutes=interval_minutes,
                    active=True,
                )
                db.add(job)
                db.commit()
                db.refresh(job)

                # Reload scheduler and table
                self.scheduler.reload()
                self._load_jobs()

                messagebox.showinfo(
                    "Job created",
                    f"Backup job '{job.name}' was created successfully.",
                )
                window.destroy()

            except Exception as exc:  # noqa: BLE001
                messagebox.showerror(
                    "Error",
                    f"Failed to create job:\n{exc}",
                )
            finally:
                db.close()

        save_button = ttk.Button(buttons_frame, text="Save", command=on_save)
        save_button.pack(side="right", padx=(0, 5))

        cancel_button = ttk.Button(buttons_frame, text="Cancel", command=window.destroy)
        cancel_button.pack(side="right", padx=(0, 5))

        # Focus name field
        name_entry.focus()
    

    def _run_selected_job(self) -> None:
        selected = self.job_tree.selection()
        if not selected:
            messagebox.showwarning("No job selected", "Please select a job first.")
            return

        item_id = selected[0]
        values = self.job_tree.item(item_id, "values")
        job_id = int(values[0])

        db = SessionLocal()
        try:
            job = db.query(BackupJob).filter_by(id=job_id).first()
            if not job:
                messagebox.showerror(
                    "Job not found",
                    f"Job with ID {job_id} was not found in database.",
                )
                return

            run = run_backup_for_job(db, job)

            if run.status == "success":
                messagebox.showinfo(
                    "Backup completed",
                    f"Backup created successfully.\n\nFile:\n{run.output_file}",
                )
            else:
                messagebox.showerror(
                    "Backup failed",
                    f"Backup failed.\n\nMessage:\n{run.message}",
                )

        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(
                "Error",
                f"An unexpected error occurred while running backup:\n{exc}",
            )
        finally:
            db.close()
        

    def _build_job_list(self) -> None:
        table_frame = ttk.Frame(self)
        table_frame.pack(fill="both", expand=True, padx=10, pady=10)

        columns = (
            "id",
            "name",
            "source",
            "destination",
            "schedule_type",
            "interval",
            "active",
        )

        self.job_tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            height=15,
        )

        self.job_tree.heading("id", text="ID")
        self.job_tree.heading("name", text="Name")
        self.job_tree.heading("source", text="Source")
        self.job_tree.heading("destination", text="Destination")
        self.job_tree.heading("schedule_type", text="Schedule")
        self.job_tree.heading("interval", text="Interval (min)")
        self.job_tree.heading("active", text="Active")

        self.job_tree.column("id", width=40, anchor="center")
        self.job_tree.column("name", width=150, anchor="w")
        self.job_tree.column("source", width=200, anchor="w")
        self.job_tree.column("destination", width=200, anchor="w")
        self.job_tree.column("schedule_type", width=80, anchor="center")
        self.job_tree.column("interval", width=90, anchor="center")
        self.job_tree.column("active", width=60, anchor="center")

        self.job_tree.pack(fill="both", expand=True, side="left")

        scrollbar = ttk.Scrollbar(
            table_frame,
            orient="vertical",
            command=self.job_tree.yview,
        )
        scrollbar.pack(side="right", fill="y")

        self.job_tree.configure(yscrollcommand=scrollbar.set)


    def _load_jobs(self) -> None:
        # Clear current rows
        for item in self.job_tree.get_children():
            self.job_tree.delete(item)

        db = SessionLocal()
        try:
            jobs = db.query(BackupJob).order_by(BackupJob.id).all()

            for job in jobs:
                self.job_tree.insert(
                    "",
                    "end",
                    values=(
                        job.id,
                        job.name,
                        job.source_path,
                        job.destination_path,
                        job.schedule_type,
                        job.interval_minutes or "",
                        "Yes" if job.active else "No",
                    ),
                )
        finally:
            db.close()


def run_app(scheduler: BackupScheduler) -> None:
    app = AutoBackupApp(scheduler=scheduler)
    app.mainloop()

