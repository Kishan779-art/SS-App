@echo off
pyinstaller --noconfirm --onefile --windowed --name "SS Construction Management System" --icon "app/assets/app_icon.ico" --add-data "app/assets;app/assets" main.py
