@echo off
setlocal enabledelayedexpansion
title Video Downloader - Instalador
cd /d "%~dp0"

echo ================================================
echo   Video Downloader - Instalador automatico
echo ================================================
echo.

REM ------------------------------------------------------------------
REM 0) Localizar o winget de forma robusta.
REM    "where winget" pode falhar mesmo com o winget instalado e
REM    funcionando: o Explorer as vezes fica horas/dias rodando com uma
REM    copia em cache do PATH de antes do winget ter sido registrado, e
REM    todo .bat aberto por duplo clique herda esse PATH desatualizado.
REM    Por isso, se "where" falhar, tentamos o caminho fixo padrao do
REM    winget diretamente, sem depender do PATH.
REM ------------------------------------------------------------------
set "WINGET_CMD="
where winget >nul 2>nul
if %errorlevel% equ 0 (
    set "WINGET_CMD=winget"
) else if exist "%LOCALAPPDATA%\Microsoft\WindowsApps\winget.exe" (
    set "WINGET_CMD=%LOCALAPPDATA%\Microsoft\WindowsApps\winget.exe"
)

REM ------------------------------------------------------------------
REM 1) Python
REM ------------------------------------------------------------------
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [1/5] Python nao encontrado neste PC.
    if not defined WINGET_CMD (
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
    "%WINGET_CMD%" install --id Python.Python.3.12 -e --source winget --accept-package-agreements --accept-source-agreements
    echo.
    echo Python foi instalado. Feche esta janela e execute "instalar.bat"
    echo novamente para continuar ^(o Windows precisa atualizar o PATH^).
    pause
    exit /b 0
) else (
    echo [1/5] Python encontrado - OK.
)

REM ------------------------------------------------------------------
REM 2) ffmpeg (necessario para mesclar video+audio, extrair MP3 e para
REM    a conversao de midia da aba "Converter Arquivos")
REM ------------------------------------------------------------------
set "PRECISA_REINICIAR="
where ffmpeg >nul 2>nul
if %errorlevel% neq 0 (
    echo [2/5] ffmpeg nao encontrado neste PC.
    if not defined WINGET_CMD (
        echo       AVISO: winget indisponivel - instale o ffmpeg manualmente em:
        echo       https://www.gyan.dev/ffmpeg/builds/ ^(e adicione a pasta bin ao PATH^)
    ) else (
        echo       Instalando ffmpeg via winget, aguarde...
        "%WINGET_CMD%" install --id Gyan.FFmpeg -e --source winget --accept-package-agreements --accept-source-agreements
        set "PRECISA_REINICIAR=1"
    )
) else (
    echo [2/5] ffmpeg encontrado - OK.
)

REM ------------------------------------------------------------------
REM 3) Tesseract OCR (necessario para a aba Documentos -> Digitalizar)
REM ------------------------------------------------------------------
set "TESSERACT_OK="
where tesseract >nul 2>nul
if %errorlevel% equ 0 set "TESSERACT_OK=1"
if exist "%ProgramFiles%\Tesseract-OCR\tesseract.exe" set "TESSERACT_OK=1"
if defined TESSERACT_OK (
    echo [3/5] Tesseract OCR encontrado - OK.
) else (
    echo [3/5] Tesseract OCR nao encontrado neste PC.
    if not defined WINGET_CMD (
        echo       AVISO: winget indisponivel - instale o Tesseract manualmente em:
        echo       https://github.com/UB-Mannheim/tesseract/wiki
    ) else (
        echo       Instalando Tesseract OCR via winget, aguarde...
        "%WINGET_CMD%" install --id UB-Mannheim.TesseractOCR -e --source winget --accept-package-agreements --accept-source-agreements
        echo       Tesseract instalado - o app ja detecta o caminho padrao
        echo       automaticamente, sem precisar reiniciar.
    )
)

REM ------------------------------------------------------------------
REM 4) Poppler (necessario para operacoes com PDF na aba Documentos:
REM    digitalizar PDF, converter PDF -> imagem)
REM ------------------------------------------------------------------
where pdftoppm >nul 2>nul
if %errorlevel% neq 0 (
    echo [4/5] Poppler nao encontrado neste PC.
    if not defined WINGET_CMD (
        echo       AVISO: winget indisponivel - instale o Poppler manualmente em:
        echo       https://github.com/oschwartz10612/poppler-windows/releases
        echo       ^(extraia o .zip e adicione a pasta Library\bin ao PATH^)
    ) else (
        echo       Instalando Poppler via winget, aguarde...
        "%WINGET_CMD%" install --id oschwartz10612.Poppler -e --source winget --accept-package-agreements --accept-source-agreements
        set "PRECISA_REINICIAR=1"
    )
) else (
    echo [4/5] Poppler encontrado - OK.
)

REM ------------------------------------------------------------------
REM 5) Dependencias Python do programa
REM ------------------------------------------------------------------
echo [5/5] Instalando bibliotecas Python ^(yt-dlp, PySide6, OCR, conversao de documentos...^)...
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
echo   Instalacao concluida!
echo   Agora abra o arquivo "iniciar.bat" para usar o programa.
echo ================================================
if defined PRECISA_REINICIAR (
    echo.
    echo IMPORTANTE: o ffmpeg e/ou o Poppler acabaram de ser instalados.
    echo Reinicie o computador ^(ou pelo menos saia e entre de novo na sua
    echo conta^) antes de usar o programa, para o Windows atualizar o PATH.
)
echo.
echo Observacao: a conversao de DOCX para PDF precisa do Microsoft Word
echo ou do LibreOffice ^(gratuito: https://www.libreoffice.org/download^)
echo instalado - nao e instalado automaticamente por ser bem grande.
echo ================================================
pause
