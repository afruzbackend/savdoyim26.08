@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
REM ================================================
REM   SAVDOYIM - Ma'lumotlar bazasi zaxirasi (backup)
REM   Qo'lda ishga tushirish yoki Windows Task Scheduler
REM   orqali har kuni avtomatik chaqirish mumkin.
REM ================================================
set "PY=..\.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"
"%PY%" manage.py backup_db --keep 14
echo.
echo Tayyor. Zaxiralar: backups\ papkasida.
REM Task Scheduler chaqirsa oyna ochilib qolmasligi uchun pause yo'q.
