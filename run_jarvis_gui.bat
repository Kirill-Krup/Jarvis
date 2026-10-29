@echo off
title JARVIS Control Center
chcp 65001 > nul
cd /d "%~dp0"
echo ========================================================
echo               ЗАПУСК СИСТЕМЫ JARVIS GUI
echo ========================================================
python main.py --gui
pause
