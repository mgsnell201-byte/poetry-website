@echo off
cd /d "%~dp0"
python scripts\publish_poetry.py
echo.
pause
