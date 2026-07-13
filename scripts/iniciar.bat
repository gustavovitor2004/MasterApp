@echo off
chcp 65001 >nul
title MasterApp

REM This .bat lives in scripts/, so the project root (where src/ lives) is
REM one directory up.
cd /d "%~dp0.."

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Python não foi encontrado. Rode scripts\instalar.bat primeiro.
    pause
    exit /b 1
)

if not exist "src\main.py" (
    echo ERRO: src\main.py não foi encontrado. Verifique se a pasta do
    echo projeto está completa.
    pause
    exit /b 1
)

python src\main.py
if %errorlevel% neq 0 (
    echo.
    echo MasterApp encerrado com erro. Código: %errorlevel%
    pause
)
