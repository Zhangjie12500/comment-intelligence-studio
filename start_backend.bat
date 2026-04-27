@echo off
cd /d "%~dp0"
uvicorn backend.main:app --port 8010
pause
