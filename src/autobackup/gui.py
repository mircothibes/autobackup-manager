import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Optional, Any, cast

from autobackup.scheduler import BackupScheduler
from autobackup.db import SessionLocal
from autobackup.models import BackupJob, BackupRun
from autobackup.backup_engine import run_backup_for_job


class AutoBackupApp(tk.Tk):
    def __init__(self, scheduler: BackupScheduler):
        super().__init__()

        self.scheduler = scheduler

        self.title("AutoBackup Manager")
        self.geometry("900x520")

        self.build_layout()

    # ------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------
    def build_layout(self) -> None:
        self.build_header()
        self.build_job_list()
        self.load_jobs()

    def build_header(self) -> None:
        header = ttk.Frame(self)
        header.pack(fill="x", padx=10, pady=10)

        ttk.Label(
            header,
            text="AutoBackup Manager",
            font=("Segoe UI", 16, "bold"),
        ).pack(side="left")

        btn_frame = ttk.Frame(header)
        btn_frame.pack(side="right")

        ttk.Button(btn_frame, text="Add Job", command=self.open_add_job).pack(
            side="left",
            padx=5,
        )
        ttk.Button(btn_frame, text="Edit Job", command=self.open_edit_job).pack(
            side="left",
            padx=5,
        )
        ttk.Button(btn_frame, text="Delete Job", command=self.delete_selected_job).pack(
            side="left",
            padx=5,
        )
        ttk.Button(btn_frame, text="History", command=self.open_history_window).pack(
            side="left",
            padx=5,
        )
        ttk.Button(btn_frame, text="Run Now", command=self.run_selected_job).pack(
            side="left",
            padx=5,
        )
        ttk.Button(btn_frame, text="Refresh", command=self.load_jobs).pack(
            side="left",
            padx=5,
        )

    # ------------------------------------------------------------
    # Job List Table
    # ------------------------------------------------------------
    def build_job_list(self) -> None:
        frame = ttk.Frame(self)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        columns = (
            "id",
            "name",
            "source",
            "destination",
            "schedule",
            "interval",
            "active",
        )

        self.job_tree = ttk.Treeview(
            frame,
            columns=columns,
            show="headings",
            height=15,
        )

        headings = {
            "id": "ID",
            "name": "Name",
            "source": "Source",
            "destination": "Destination",
            "schedule": "Schedule",
            "interval": "Interval (min)",
            "active": "Active",
        }

        for col, text in headings.items():
            self.job_tree.heading(col, text=text)

        self.job_tree.column("id", width=40, anchor="center")
        self.job_tree.column("name", width=150)
        self.job_tree.column("source", width=200)
        self.job_tree.column("destination", width=200)
        self.job_tree.column("schedule", width=80, anchor="center")
        self.job_tree.column("interval", width=90, anchor="center")
        self.job_tree.column("active", width=60, anchor="center")

        self.job_tree.pack(fill="both", expand=True, side="left")

        scrollbar = ttk.Scrollbar(
            frame,
            orient="vertical",
            command=self.job_tree.yview,
        )
        scrollbar.pack(side="right", fill="y")
        self.job_tree.configure(yscrollcommand=scrollbar.set)

    # ------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------
    def browse_dir(self, variable: tk.StringVar) -> None:
        directory = filedialog.askdirectory()
        if directory:
            variable.set(directory)

    def get_selected_job_id(self) -> Optional[int]:
        selected = self.job_tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Please select a job.")
            return None

        values = self.job_tree.item(selected[0], "values")
        return int(values[0])

    # ------------------------------------------------------------
    # Load Jobs
    # ------------------------------------------------------------
    def load_jobs(self) -> None:
        for item in self.job_tree.get_children():
            self.job_tree.delete(item)

        db = SessionLocal()
        try:
            jobs = db.query(BackupJob).order_by(BackupJob.id).all()
            for job in jobs:
                active_label = "Yes" if bool(job.active) else "No"

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
                        active_label,
                    ),
                )
        finally:
            db.close()

    # ------------------------------------------------------------
    # History Window
    # ------------------------------------------------------------
    def open_history_window(self) -> None:
        job_id = self.get_selected_job_id()
        if job_id is None:
            return

        db = SessionLocal()
        try:
            job = db.query(BackupJob).filter_by(id=job_id).first()
            if job is None:
                messagebox.showerror("Error", "Job no longer exists.")
                return

            runs = (
                db.query(BackupRun)
                .filter_by(job_id=job_id)
                .order_by(BackupRun.start_time.desc())
                .all()
            )
        finally:
            db.close()

        window = tk.Toplevel(self)
        window.title(f"History - {job.name}")
        window.geometry("800x400")
        window.grab_set()

        frame = ttk.Frame(window)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        columns = (
            "id",
            "start",
            "end",
            "status",
            "message",
            "output_file",
        )

        tree = ttk.Treeview(
            frame,
            columns=columns,
            show="headings",
            height=15,
        )

        tree.heading("id", text="ID")
        tree.heading("start", text="Start time")
        tree.heading("end", text="End time")
        tree.heading("status", text="Status")
        tree.heading("message", text="Message")
        tree.heading("output_file", text="Output file")

        tree.column("id", width=40, anchor="center")
        tree.column("start", width=150, anchor="w")
        tree.column("end", width=150, anchor="w")
        tree.column("status", width=80, anchor="center")
        tree.column("message", width=250, anchor="w")
        tree.column("output_file", width=250, anchor="w")

        tree.pack(fill="both", expand=True, side="left")

        scrollbar = ttk.Scrollbar(
            frame,
            orient="vertical",
            command=tree.yview,
        )
        scrollbar.pack(side="right", fill="y")
        tree.configure(yscrollcommand=scrollbar.set)

        for run in runs:
            msg = (run.message or "")[:80]
            tree.insert(
                "",
                "end",
                values=(
                    run.id,
                    str(run.start_time) if run.start_time else "",
                    str(run.end_time) if run.end_time else "",
                    str(run.status) if run.status else "",
                    msg,
                    str(run.output_file) if run.output_file else "",
                ),
            )


    # ------------------------------------------------------------
    # Run Job
    # ------------------------------------------------------------
    def run_selected_job(self) -> None:
        job_id = self.get_selected_job_id()
        if job_id is None:
            return

        db = SessionLocal()
        try:
            job = db.query(BackupJob).filter_by(id=job_id).first()
            if not job:
                messagebox.showerror("Error", "Selected job no longer exists.")
                return

            run = run_backup_for_job(db, job)
            status = str(getattr(run, "status", ""))
            message = str(getattr(run, "message", "")) if getattr(run, "message", None) else ""

            if status == "success":
                messagebox.showinfo(
                    "Success",
                    f"Backup created:\n{getattr(run, 'output_file', '')}",
                )
            else:
                messagebox.showerror(
                    "Backup failed",
                    message or "Backup failed with unknown error.",
                ) 
        finally:
            db.close()

    # ------------------------------------------------------------
    # Add / Edit Job (Shared Window)
    # ------------------------------------------------------------
    def open_add_job(self) -> None:
        self.open_job_window(job=None)

    def open_edit_job(self) -> None:
        job_id = self.get_selected_job_id()
        if job_id is None:
            return

        db = SessionLocal()
        try:
            job = db.query(BackupJob).filter_by(id=job_id).first()
        finally:
            db.close()

        if job is None:
            messagebox.showerror("Error", "Job not found.")
            return

        self.open_job_window(job=job)

    def open_job_window(self, job: Optional[BackupJob] = None) -> None:
        is_edit = job is not None

        window = tk.Toplevel(self)
        window.title("Edit Job" if is_edit else "Add Job")
        window.geometry("500x330")
        window.grab_set()

        # Variables
        name_var = tk.StringVar(value=str(job.name) if is_edit else "")
        src_var = tk.StringVar(value=str(job.source_path) if is_edit else "")
        dst_var = tk.StringVar(value=str(job.destination_path) if is_edit else "")
        schedule_var = tk.StringVar(
            value=str(job.schedule_type) if is_edit else "manual",
        )
        interval_var = tk.StringVar(
            value=str(job.interval_minutes) 
            if is_edit and job.interval_minutes is not None else "",
        )
        active_var = tk.BooleanVar(value=bool(job.active) if is_edit else True)

        # Form
        form = ttk.Frame(window)
        form.pack(fill="both", expand=True, padx=10, pady=10)

        fields = [
            ("Name:", name_var),
            ("Source path:", src_var),
            ("Destination path:", dst_var),
        ]

        for i, (label_text, var) in enumerate(fields):
            ttk.Label(form, text=label_text).grid(row=i, column=0, sticky="w")
            entry = ttk.Entry(form, textvariable=var, width=35)
            entry.grid(row=i, column=1, sticky="we", pady=5)
            ttk.Button(
                form,
                text="Browse",
                command=lambda v=var: self.browse_dir(v),
            ).grid(row=i, column=2, padx=5)

        ttk.Label(form, text="Schedule type:").grid(row=3, column=0, sticky="w")
        schedule_box = ttk.Combobox(
            form,
            textvariable=schedule_var,
            values=["manual", "interval", "daily"],
            state="readonly",
            width=15,
        )
        schedule_box.grid(row=3, column=1, sticky="w", pady=5)

        ttk.Label(form, text="Interval (min):").grid(row=4, column=0, sticky="w")
        ttk.Entry(form, textvariable=interval_var, width=10).grid(
            row=4,
            column=1,
            sticky="w",
            pady=5,
        )

        ttk.Checkbutton(form, text="Active", variable=active_var).grid(
            row=5,
            column=1,
            sticky="w",
            pady=5,
        )

        # Save logic
        def save_job() -> None:
            name = name_var.get().strip()
            src = src_var.get().strip()
            dst = dst_var.get().strip()
            schedule = schedule_var.get()
            interval_text = interval_var.get().strip()
            interval_value: Optional[int] = None

            if not name or not src or not dst:
                messagebox.showwarning(
                    "Missing data",
                    "Name, source path and destination path are required.",
                )
                return

            if schedule == "interval":
                if not interval_text:
                    messagebox.showwarning(
                        "Missing interval",
                        "Interval minutes are required for interval schedule.",
                    )
                    return
                try:
                    interval_value = int(interval_text)
                    if interval_value <= 0:
                        raise ValueError
                except ValueError:
                    messagebox.showerror(
                        "Invalid interval",
                        "Interval must be a positive integer.",
                    )
                    return

            db = SessionLocal()
            try:
                if is_edit and job is not None:
                    job_db_any: Any = db.query(BackupJob).filter_by(id=job.id).first()
                    if job_db_any is None:
                        messagebox.showerror("Error", "Job no longer exists.")
                        return

                    job_db_any.name = name
                    job_db_any.source_path = src
                    job_db_any.destination_path = dst
                    job_db_any.schedule_type = schedule
                    job_db_any.interval_minutes = ( 
                        int(interval_value) if interval_value is not None else None)
                    job_db_any.active = bool(active_var.get())
                else:
                    job_db_any = BackupJob(
                        name=name,
                        source_path=src,
                        destination_path=dst,
                        schedule_type=schedule,
                        interval_minutes=interval_value,
                        active=active_var.get(),
                    )
                    db.add(job_db_any)

                db.commit()
                self.scheduler.reload()
                self.load_jobs()
                messagebox.showinfo("Success", "Job saved successfully.")
                window.destroy()
            finally:
                db.close()

        # Buttons
        btns = ttk.Frame(window)
        btns.pack(fill="x", padx=10, pady=10)

        ttk.Button(btns, text="Cancel", command=window.destroy).pack(
            side="right",
            padx=5,
        )
        ttk.Button(btns, text="Save", command=save_job).pack(side="right")

    # ------------------------------------------------------------
    # Delete Job
    # ------------------------------------------------------------
    def delete_selected_job(self) -> None:
        job_id = self.get_selected_job_id()
        if job_id is None:
            return

        if not messagebox.askyesno("Confirm", f"Delete job ID {job_id}?"):
            return

        db = SessionLocal()
        try:
            job = db.query(BackupJob).filter_by(id=job_id).first()
            if job is None:
                messagebox.showerror("Error", "Job no longer exists.")
                return

            db.delete(job)
            db.commit()

            self.scheduler.reload()
            self.load_jobs()
            messagebox.showinfo("Deleted", "Job removed successfully.")
        finally:
            db.close()


def run_app(scheduler: BackupScheduler) -> None:
    app = AutoBackupApp(scheduler)
    app.mainloop()

