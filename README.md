# 🗂️ AutoBackup Manager

AutoBackup Manager is a desktop application built with **Python**, **Tkinter**, and **PostgreSQL** that allows users to create automated backup jobs, run them manually, track execution history, visualize results on dashboards, and inspect backup folders through an integrated file explorer.

The goal of this project is to provide a clean, GUI-based backup automation tool designed for learning purposes and real-world usage.

---

## 🚀 Features

### ✅ Backup Jobs
- Create, edit, delete backup jobs  
- Define:
  - source folder  
  - destination folder  
  - schedule type  
  - interval (minutes)  
  - job activation (enable/disable)

### ✅ Manual Backup Execution
- Run any job immediately
- Validation of paths (missing folders, permissions)
- ZIP archive creation with timestamp naming
- Detailed logging for success and error cases

### ✅ Backup History
- Shows all past executions:
  - run ID  
  - job ID  
  - status (success / error)  
  - start time  
  - end time  
  - message preview  
- “View details” window with full log and output file path

### ✅ Dashboard / Analytics
- Bar chart: **Backups per day**
- Pie chart: **Success vs Failure**
- Summary statistics:
  - total runs  
  - success  
  - failure  
  - average duration  

### ✅ Destination Folder Viewer
- Internal Tkinter window to list folder contents
- Scrollable file viewer  
- Option to open with:
  - system file manager (xdg-open, open, explorer.exe)  
  - fallback for terminal file managers  
- Graceful error handling when the path doesn't exist

### ✅ Clean Project Architecture
- `backup_engine.py` — core backup logic  
- `scheduler.py` — scheduling system (manual mode ready, auto mode coming soon)  
- `gui.py` — graphical interface (Tkinter)  
- `models.py` — SQLAlchemy ORM models  
- `db.py` — database session handling  

---

## 🧱 Tech Stack

- **Python 3.12**
- **Tkinter** (GUI)
- **PostgreSQL + SQLAlchemy**  
- **matplotlib** (dashboard charts)
- **Docker & Docker Compose** (database container)
- **Pyright** for static type checking

---

## 📦 Installation

1. Clone the repository
```bash
git clone https://github.com/your-user/autobackup-manager.git
cd autobackup-manager
``` 

2. Create and activate a virtual environment
```bash
python -m venv .venv
source .venv/bin/activate  # Linux / macOS
.venv\Scripts\activate     # Windows
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Start PostgreSQL via Docker
```bash
docker compose up -d db
```

5. Run the application
```bash
python -m autobackup.main
```

---

## File Structure
```bash
autobackup-manager/
│
├── src/
│   └── autobackup/
│       ├── gui.py
│       ├── main.py
│       ├── db.py
│       ├── models.py
│       ├── scheduler.py
│       ├── backup_engine.py
│       ├── config.py
│
├── requirements.txt
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

---

## 🧪 Type Checking (Pyright)

Run:
```bash
npx pyright
```

Result after improvements:

- 0 errors, 0 warnings, 0 informations

---

## 🧱 Building the Windows executable (PyInstaller)

The project can be packaged as a standalone **Windows executable (.exe)** using PyInstaller.

> Requirements:
> - Python 3.12+ installed on Windows (`py` launcher available)
> - PostgreSQL running and accessible with the same credentials as in `.env`

### 1. Clone or copy the project to Windows

Example path:

```text
C:\Users\mirco\dev\autobackup-manager
```
- Make sure the following files exist in the project root:
- pyproject.toml
- requirements.txt
- .env
- src\autobackup\main.py (application entry point)

### 2. Create and activate a virtual environment
```
cd C:\Users\mirco\dev\autobackup-manager

py -m venv .venv
.\.venv\Scripts\activate
```

### 3. Install dependencies
```
pip install -r requirements.txt
pip install pyinstaller
```

### 4. Build the executable with PyInstaller
```
pyinstaller --name AutoBackupManager --onefile --windowed src\autobackup\main.py
```
This will generate the following structure:
```
dist\
  AutoBackupManager.exe   # Windows executable
build\
  ...                     # PyInstaller build artifacts (can be ignored)
```

### 5. Running the executable
From the project root:
```
cd C:\Users\mirco\dev\autobackup-manager
.\dist\AutoBackupManager.exe
```
The application will:
- Read configuration from .env (database, environment, etc.)
- Connect to PostgreSQL
- Start the background scheduler
- Open the Tkinter GUI (AutoBackup Manager)

---

## 📝 Roadmap
Implemented ✔️

- GUI CRUD for backup jobs
- Manual job execution
- History + details viewer
- Dashboard with charts
- Internal folder viewer
- Path validation & error handling
- Pyright-clean codebase

Coming soon 🚧

- Automatic scheduler (run jobs in background)
- System tray integration
- Email notifications
- Export logs to CSV
- Windows installer (.exe)

---

## 🤝 Contributing

Pull requests are welcome!
For major changes, please open an issue to discuss what you'd like to change.

---

## 📜 License

MIT License — feel free to use this project for learning or production.

---

## 🧑‍💻 Author
Marcos Vinicius Thibes Kemer
