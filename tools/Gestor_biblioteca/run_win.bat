@echo off
setlocal enabledelayedexpansion

set "APP_DIR=%~dp0"
set "VENV_DIR=%APP_DIR%venv"
set "MAIN_PY=%APP_DIR%main.py"
set "REQUIREMENTS=%APP_DIR%requirements.txt"

:: ── flags ──
set "RESET_VENV=false"
for %%a in (%*) do (
    if /i "%%a"=="--reset-venv" set "RESET_VENV=true"
)

echo.
echo  === Gestor de Biblioteca - Inicio ===
echo.

:: ── 1. Buscar Python ──
set "PYTHON="
for %%p in (py python3 python) do (
    where %%p >nul 2>&1 && set "PYTHON=%%p" && goto :found_py
)
echo [ERROR] Python no encontrado. Instala Python 3.8+ desde python.org
echo        Asegurate de marcar "Add Python to PATH" durante la instalacion.
pause
exit /b 1

:found_py
echo [1/7] Python: !PYTHON!
!PYTHON! --version

:: ── 2. Validar version 3.8+ ──
!PYTHON! -c "import sys; sys.exit(0 if sys.version_info >= (3,8) else 1)"
if errorlevel 1 (
    echo [ERROR] Se requiere Python 3.8+
    pause
    exit /b 1
)
echo [2/7] Version OK

:: ── 3. Crear / resetear venv ──
if "!RESET_VENV!"=="true" (
    if exist "%VENV_DIR%" (
        echo    --reset-venv: eliminando venv existente...
        rmdir /s /q "%VENV_DIR%"
    )
)

if not exist "%VENV_DIR%" (
    echo [3/7] Creando entorno virtual...
    !PYTHON! -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [ERROR] No se pudo crear el entorno virtual
        pause
        exit /b 1
    )
    echo      Entorno virtual creado
) else (
    echo [3/7] Entorno virtual ya existe
)

:: ── 4. Activar e instalar dependencias ──
call "%VENV_DIR%\Scripts\activate.bat"

if exist "%REQUIREMENTS%" (
    echo [4/7] Instalando dependencias...
    pip install --quiet --upgrade -r "%REQUIREMENTS%"
    if errorlevel 1 (
        echo [ERROR] No se pudieron instalar las dependencias
        pause
        exit /b 1
    )
    echo      Dependencias instaladas
)

:: ── 5. Verificar mutagen ──
echo [5/7] Verificando librerias...
!PYTHON! -c "import mutagen" 2>nul
if errorlevel 1 (
    echo    mutagen no encontrado. Instalando...
    pip install mutagen
    !PYTHON! -c "import mutagen" 2>nul && echo    mutagen OK || echo    [WARN] mutagen no disponible. Audio covers no funcionaran.
) else (
    echo    mutagen OK
)

:: ── 6. Verificar sv-ttk ──
!PYTHON! -c "import sv_ttk" 2>nul
if errorlevel 1 (
    echo    sv-ttk no encontrado. Instalando...
    pip install sv-ttk
    !PYTHON! -c "import sv_ttk" 2>nul && echo    sv-ttk OK || echo    [WARN] sv-ttk no disponible. Tema moderno no disponible.
) else (
    echo    sv-ttk OK
)

:: ── 7. Ejecutar app ──
echo [7/7] Iniciando aplicacion...
echo.
!PYTHON! "%MAIN_PY%" %*

if errorlevel 1 (
    echo.
    echo [ERROR] La aplicacion termino con un error (codigo: !errorlevel!)
    pause
)
