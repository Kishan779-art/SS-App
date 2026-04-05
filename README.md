# SS Construction Management System

Desktop software for managing construction production, material inventory, and salary payments.

## Features

- Dark premium Tkinter desktop interface
- SQLite database for persistent storage
- Production entry with automatic value calculation
- Material stock-in and usage with live quantity updates
- Payments calculator based on `blocks x rate per block`
- PDF reports for production, materials, and payments
- PyInstaller build command for creating a standalone executable

## Project Structure

```text
SS App/
|-- app/
|   |-- __init__.py
|   |-- app.py
|   |-- database.py
|   |-- reports.py
|   `-- theme.py
|-- data/
|-- exports/
|-- build_exe.bat
|-- main.py
|-- README.md
`-- requirements.txt
```

## Run The Application

```powershell
pip install -r requirements.txt
python main.py
```

## Data Storage

- Application source files stay in this project folder.
- The SQLite database is stored in `data/ss_construction_runtime.db`.
- PDF exports default to the local `exports/` folder unless you choose another location.

## Build EXE

```powershell
build_exe.bat
```
