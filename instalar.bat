@echo off
setlocal enabledelayedexpansion
title Video Downloader - Instalador
cd /d "%~dp0"

echo ================================================
echo   Video Downloader - Instalador automatico
echo ================================================
echo.

REM ------------------------------------------------------------------
REM 1) Python
REM ------------------------------------------------------------------
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [1/3] Python nao encontrado neste PC.
    where winget >nul 2>nul
    if %errorlevel% neq 0 (
        echo.
        echo ERRO: nao foi possivel instalar automaticamente ^(winget indisponivel^).
        echo Baixe e instale o Python manualmente em:
        echo   https://www.python.org/downloads/
        echo IMPORTANTE: marque a opcao "Add python.exe to PATH" durante a instalacao.
        echo Depois, rode este arquivo instalar.bat novamente.
        pause
        exit /b 1
    )
    echo       Instalando Python 3.12 via winget, aguarde...
    winget install --id Python.Python.3.12 -e --source winget --accept-package-agreements --accept-source-agreements
    echo.
    echo Python foi instalado. Feche esta janela e execute "instalar.bat"
    echo novamente para continuar ^(o Windows precisa atualizar o PATH^).
    pause
    exit /b 0
) else (
    echo [1/3] Python encontrado - OK.
)

REM ------------------------------------------------------------------
REM 2) ffmpeg (necessario para mesclar video+audio e extrair MP3)
REM ------------------------------------------------------------------
where ffmpeg >nul 2>nul
if %errorlevel% neq 0 (
    echo [2/3] ffmpeg nao encontrado neste PC.
    where winget >nul 2>nul
    if %errorlevel% neq 0 (
        echo       AVISO: winget indisponivel - instale o ffmpeg manualmente em:
        echo       https://www.gyan.dev/ffmpeg/builds/ ^(e adicione a pasta bin ao PATH^)
    ) else (
        echo       Instalando ffmpeg via winget, aguarde...
        winget install --id Gyan.FFmpeg -e --source winget --accept-package-agreements --accept-source-agreements
        echo       ffmpeg instalado. Pode ser necessario reiniciar o PC para o
        echo       PATH ser reconhecido em todos os programas.
    )
) else (
    echo [2/3] ffmpeg encontrado - OK.
)

REM ------------------------------------------------------------------
REM 3) Dependencias Python do programa
REM ------------------------------------------------------------------
echo [3/3] Instalando bibliotecas Python ^(yt-dlp, PySide6, requests^)...
python -m pip install --upgrade pip >nul 2>nul
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo ERRO ao instalar as bibliotecas. Verifique sua conexao com a internet
    echo e rode "instalar.bat" novamente.
    pause
    exit /b 1
)

echo.
echo ================================================
echo   Instalacao concluida com sucesso!
echo   Agora abra o arquivo "iniciar.bat" para usar o programa.
echo ================================================
pause
