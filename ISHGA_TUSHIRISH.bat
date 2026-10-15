@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
rem Lokal ishlab chiqish rejimi (productionda .env da DJANGO_DEBUG=False)
if not defined DJANGO_DEBUG set DJANGO_DEBUG=True
echo ================================================
echo   SAVDOYIM - Server + Telegram bot (birga)
echo ================================================
echo  Server:  http://127.0.0.1:8000
echo  Telegram bot ham shu bilan avtomatik ishga tushadi.
echo  To'xtatish: Ctrl + C
echo ================================================
set "PY=..\.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"
"%PY%" manage.py runserver 127.0.0.1:8000
pause
