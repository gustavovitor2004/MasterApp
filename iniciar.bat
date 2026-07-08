@echo off
title Video Downloader
cd /d "%~dp0"

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Python nao foi encontrado. Rode "instalar.bat" primeiro.
    pause
    exit /b 1
)

python main.py
if %errorlevel% neq 0 (
    echo.
    echo O programa fechou com um erro ^(mensagem acima, se houver^).
    echo Se for a primeira vez usando, rode "instalar.bat" primeiro.
    pause
)
