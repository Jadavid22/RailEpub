@echo off
title Instalador de Dependencias - RailEpub
color 0A

echo ===================================================
echo       INSTALADOR DE DEPENDENCIAS - RAILEPUB
echo ===================================================
echo.

:: Verificar si existe la carpeta .venv, si no, crear el entorno virtual
if not exist ".venv" (
    echo [!] No se encontro el entorno virtual. Creando .venv...
    python -m venv .venv
    echo [v] Entorno virtual creado exitosamente.
    echo.
)

:: Activar el entorno virtual
echo [*] Activando entorno virtual (.venv)...
call .venv\Scripts\activate.bat

:: Actualizar pip
echo [*] Actualizando pip...
python -m pip install --upgrade pip

echo.
echo [*] Instalando librerias requeridas...
pip install ebooklib opencv-python numpy Pillow manga-ocr tqdm janome

echo.
echo ===================================================
echo [v] ¡Todas las dependencias se instalaron con exito!
echo ===================================================
echo.
pause