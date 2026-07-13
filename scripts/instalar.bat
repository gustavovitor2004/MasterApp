@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
title MasterApp — Instalação

REM This .bat lives in scripts/, so the project root (where requirements.txt
REM and config.json live) is one directory up.
cd /d "%~dp0.."

echo ================================================
echo   MasterApp - Instalador
echo ================================================
echo.

REM ------------------------------------------------------------------
REM 1) Python 3.10+
REM ------------------------------------------------------------------
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [1/6] Python nao encontrado neste PC.
    echo       Abrindo a pagina de download do Python...
    start "" "https://www.python.org/downloads/"
    echo.
    echo Instale o Python 3.10 ou superior ^(marque "Add python.exe to PATH"
    echo durante a instalacao^) e rode este instalador novamente.
    pause
    exit /b 1
)

set "PY_OK="
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set "PY_VERSION=%%v"
for /f "tokens=1,2 delims=." %%a in ("!PY_VERSION!") do (
    set "PY_MAJOR=%%a"
    set "PY_MINOR=%%b"
)
if !PY_MAJOR! gtr 3 set "PY_OK=1"
if !PY_MAJOR! equ 3 if !PY_MINOR! geq 10 set "PY_OK=1"

if not defined PY_OK (
    echo [1/6] Python !PY_VERSION! encontrado, mas o MasterApp precisa do
    echo       Python 3.10 ou superior.
    echo       Abrindo a pagina de download do Python...
    start "" "https://www.python.org/downloads/"
    pause
    exit /b 1
)
echo [1/6] Python !PY_VERSION! encontrado - OK.

REM ------------------------------------------------------------------
REM 2) pip
REM ------------------------------------------------------------------
python -m pip --version >nul 2>nul
if %errorlevel% neq 0 (
    echo [2/6] pip nao encontrado - tentando instalar via ensurepip...
    python -m ensurepip --upgrade
    if !errorlevel! neq 0 (
        echo ERRO: nao foi possivel instalar o pip automaticamente.
        pause
        exit /b 1
    )
)
echo [2/6] pip disponivel - OK.

REM ------------------------------------------------------------------
REM 3) Atualizar o pip silenciosamente
REM ------------------------------------------------------------------
echo [3/6] Atualizando o pip...
python -m pip install --upgrade pip >nul 2>nul

REM ------------------------------------------------------------------
REM 4) Dependencias do requirements.txt (caminho relativo a raiz do
REM    projeto, ja que subimos um nivel no inicio deste script)
REM ------------------------------------------------------------------
echo [4/6] Instalando bibliotecas Python ^(pode levar alguns minutos^)...
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo ERRO ao instalar as bibliotecas. Verifique sua conexao com a
    echo internet e rode "scripts\instalar.bat" novamente.
    pause
    exit /b 1
)

REM ------------------------------------------------------------------
REM 5) ffmpeg
REM ------------------------------------------------------------------
set "FFMPEG_STATUS=ATENÇÃO: não encontrado"
where ffmpeg >nul 2>nul
if %errorlevel% equ 0 (
    set "FFMPEG_STATUS=encontrado"
) else (
    echo [5/6] AVISO: ffmpeg nao encontrado no PATH.
    echo       Baixe em: https://ffmpeg.org/download.html
)

REM ------------------------------------------------------------------
REM 6) tesseract
REM ------------------------------------------------------------------
set "TESSERACT_STATUS=ATENÇÃO: não encontrado"
where tesseract >nul 2>nul
if %errorlevel% equ 0 (
    set "TESSERACT_STATUS=encontrado"
) else (
    echo [6/6] AVISO: tesseract nao encontrado no PATH.
    echo       Baixe em: https://github.com/UB-Mannheim/tesseract/wiki
)

REM ------------------------------------------------------------------
REM Poppler - not part of the strict step list above, but checked the same
REM way since the Documentos tab's PDF features (digitalizar PDF, PDF ->
REM imagem) need it just as much as ffmpeg/tesseract.
REM ------------------------------------------------------------------
set "POPPLER_STATUS=ATENÇÃO: não encontrado"
where pdftoppm >nul 2>nul
if %errorlevel% equ 0 (
    set "POPPLER_STATUS=encontrado"
) else (
    echo       AVISO: poppler nao encontrado no PATH ^(necessario para
    echo       digitalizar PDF e converter PDF -^> imagem^).
    echo       Baixe em: https://github.com/oschwartz10612/poppler-windows/releases
)

echo.
echo ================================================
echo   ✓ Dependências Python instaladas
echo   ✓ ffmpeg: !FFMPEG_STATUS!
echo   ✓ tesseract: !TESSERACT_STATUS!
echo   ✓ poppler: !POPPLER_STATUS!
echo.
echo   Execute scripts\iniciar.bat para iniciar o MasterApp.
echo ================================================
pause
