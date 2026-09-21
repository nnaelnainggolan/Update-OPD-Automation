@echo off
cd /d "%~dp0"
".venv\Scripts\python.exe" multi_project.py --login --projects projects_2_verified.json
pause
