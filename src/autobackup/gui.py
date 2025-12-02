import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Optional, Any

import os
import sys
import subprocess

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

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
        ttk.Button(btn_frame, text="Dashboard", command=self.open_dashboard_window).pack(
            side="left",
            padx=5,
        )
        ttk.Button(btn_frame, text="Open Folder", command=self.open_destination_folder).pack(
            side="left", 
            padx=5
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
            run_any: Any = run

            message_text = str(getattr(run_any, "message", "") or "")[:80]
            start_val = getattr(run_any, "start_time", None)
            end_val = getattr(run_any, "end_time", None)
            status_val = getattr(run_any, "status", "")
            output_val = getattr(run_any, "output_file", "")

            tree.insert(
                "",
                "end",
                values=(
                    run_any.id,
                    str(start_val) if start_val is not None else "",
                    str(end_val) if end_val is not None else "",
                    str(status_val) if status_val else "",
                    message_text,
                    str(output_val) if output_val else "",
                ),
            )

    # ------------------------------------------------------------
    # Open Dashboard Window
    # ------------------------------------------------------------
    def open_dashboard_window(self) -> None:
        db = SessionLocal()
        try:
            runs = db.query(BackupRun).all()
        finally:
            db.close()

        if not runs:
            messagebox.showinfo(
                "Dashboard",
                "No backup runs available to build the dashboard yet.",
            )
            return

        # Collect statistics
        total_runs = len(runs)
        success_count = 0
        failure_count = 0
        date_counts: dict[str, int] = {}
        total_duration_secs = 0.0
        duration_count = 0

        for run in runs:
            run_any: Any = run  

            status_val = str(getattr(run_any, "status", "") or "")
            if status_val == "success":
                success_count += 1
            else:
                failure_count += 1

            start_val = getattr(run_any, "start_time", None)
            end_val = getattr(run_any, "end_time", None)

            if start_val is not None:
                date_key = str(start_val.date())
            elif end_val is not None:
                date_key = str(end_val.date())
            else:
                date_key = None

            if date_key is not None:
                date_counts[date_key] = date_counts.get(date_key, 0) + 1

            if start_val is not None and end_val is not None:
                delta = end_val - start_val
                total_duration_secs += delta.total_seconds()
                duration_count += 1

        avg_duration = (
            total_duration_secs / duration_count if duration_count > 0 else 0.0
        )

        dates = sorted(date_counts.keys())
        counts = [date_counts[d] for d in dates]

        window = tk.Toplevel(self)
        window.title("Backup Dashboard")
        window.geometry("900x520")
        window.grab_set()

        # Top KPIs
        kpi_frame = ttk.Frame(window)
        kpi_frame.pack(fill="x", padx=10, pady=10)

        ttk.Label(kpi_frame, text=f"Total runs: {total_runs}").pack(side="left", padx=10)
        ttk.Label(kpi_frame, text=f"Success: {success_count}").pack(side="left", padx=10)
        ttk.Label(kpi_frame, text=f"Failure: {failure_count}").pack(side="left", padx=10)
        ttk.Label(kpi_frame, text=f"Avg duration: {avg_duration:.1f}s").pack(side="left", padx=10)

        # If we have no dated info, show a simple message
        if not dates:
            ttk.Label(
                window,
                text="No dated backup runs to display charts yet.",
            ).pack(padx=10, pady=10)
            return

        # Matplotlib figure with two charts
        fig = Figure(figsize=(8, 4), dpi=100)
        ax1 = fig.add_subplot(1, 2, 1)
        ax2 = fig.add_subplot(1, 2, 2)

        # Bar chart: backups per day
        ax1.bar(dates, counts)
        ax1.set_title("Backups per day")
        ax1.set_xlabel("Date")
        ax1.set_ylabel("Number of backups")
        ax1.tick_params(axis="x", rotation=45)

        # Pie chart: success vs failure
        if success_count + failure_count > 0:
            ax2.pie(
                [success_count, failure_count],
                labels=["Success", "Failure"],
                autopct="%d",
            )
            ax2.set_title("Backup status")
        else:
            ax2.text(
                0.5,
                0.5,
                "No runs",
                ha="center",
                va="center",
                fontsize=12,
            )

        canvas = FigureCanvasTkAgg(fig, master=window)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)


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
    # Open destination Folder
    # ------------------------------------------------------------
    def open_destination_folder(self) -> None:
        """Open a viewer window for the destination folder of the selected job."""

        job_id = self.get_selected_job_id()
        if job_id is None:
            return

        db = SessionLocal()
        try:
            job = db.query(BackupJob).filter_by(id=job_id).first()
            if job is None:
                messagebox.showerror("Error", "Selected job does not exist anymore.")
                return

            destination = str(job.destination_path or "").strip()
        finally:
            db.close()

        if not destination:
            messagebox.showwarning(
                "No destination",
                "This job does not have a destination path configured.",
            )
            return

        if not os.path.isdir(destination):
            messagebox.showerror(
                "Folder not found",
                f"Destination path does not exist:\n{destination}",
            )
            return

        self._show_destination_viewer(destination)

    def _show_destination_viewer(self, destination: str) -> None:
        """Show a simple folder viewer window for the given destination path."""
        window = tk.Toplevel(self)
        window.title(f"Destination folder")
        window.geometry("600x400")
        window.grab_set()

        # Path label
        path_label = ttk.Label(window, text=destination)
        path_label.pack(fill="x", padx=10, pady=(10, 5))

        # List of files / folders
        list_frame = ttk.Frame(window)
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)

        listbox = tk.Listbox(list_frame)
        listbox.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=listbox.yview)
        scrollbar.pack(side="right", fill="y")
        listbox.configure(yscrollcommand=scrollbar.set)

        try:
            entries = sorted(os.listdir(destination))
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Error", f"Could not list folder contents:\n{exc}")
            window.destroy()
            return

        if not entries:
            listbox.insert("end", "<empty folder>")
        else:
            for name in entries:
                listbox.insert("end", name)

        # Buttons at the bottom
        btn_frame = ttk.Frame(window)
        btn_frame.pack(fill="x", padx=10, pady=(5, 10))

        open_btn = ttk.Button(
            btn_frame,
            text="Open in system file manager",
            command=lambda: self._open_in_system_file_manager(destination),
        )
        open_btn.pack(side="left")

        close_btn = ttk.Button(btn_frame, text="Close", command=window.destroy)
        close_btn.pack(side="right")

    def _open_in_system_file_manager(self, destination: str) -> None:
        """Try to open destination in the OS file manager (if available)."""
        try:
            if sys.platform.startswith("linux"):
                subprocess.Popen(
                    ["xdg-open", destination],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            elif sys.platform == "win32":
                os.startfile(destination)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(
                    ["open", destination],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            else:
                messagebox.showinfo(
                    "Destination folder",
                    f"Destination path:\n{destination}",
                )
        except Exception as exc:  # noqa: BLE001
            messagebox.showinfo(
                "Destination folder",
                f"Could not open system file manager.\n\nPath:\n{destination}\n\nError:\n{exc}",
            )
    
  

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

