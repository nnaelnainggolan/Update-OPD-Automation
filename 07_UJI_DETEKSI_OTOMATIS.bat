@echo off
cd /d "%~dp0"
".venv\Scripts\python.exe" multi_project.py --login --projects projects_auto_test.json
pause
