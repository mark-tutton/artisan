@echo off
:: Build test version of Artisan
:: This script sets up the environment and builds a test version

setlocal enabledelayedexpansion

:: Set APPVEYOR to allow the spec file to run locally
set APPVEYOR=1

:: Use python from PATH (works with Windows Store Python launcher)
where.exe python >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found in PATH!
    echo Please ensure Python is installed and in your PATH
    exit /b 1
)

:: Get the actual Python executable path
for /f "delims=" %%i in ('python -c "import sys; print(sys.executable)" 2^>nul') do set PYTHON_EXE=%%i

if not defined PYTHON_EXE (
    echo ERROR: Could not determine Python executable path
    exit /b 1
)

:: Extract directory from full path
for %%i in ("%PYTHON_EXE%") do set PYTHON_PATH=%%~dpi
set PYTHON_PATH=%PYTHON_PATH:~0,-1%

echo Using Python at: %PYTHON_PATH%

:: Set PyQt version
set PYQT=6

:: Set Qt translations path (adjust as needed)
set QT_TRANSL=C:\Qt\6.4\msvc2019_64\translations
if not exist "%QT_TRANSL%" (
    echo WARNING: Qt translations not found at %QT_TRANSL%
    echo Some translations may be missing
)

:: Set legacy flag (False for PyQt6, True for PyQt5)
set ARTISAN_LEGACY=False

:: Set the source directory (current directory)
set ARTISAN_SRC=%~dp0
set ARTISAN_SRC=%ARTISAN_SRC:~0,-1%

:: Change to the src directory
cd /d "%~dp0"

:: Check if spec file exists
if not exist "artisan-win-test.spec" (
    echo ERROR: artisan-win-test.spec not found!
    echo Please create it by copying artisan-win.spec and modifying the NAME variable
    exit /b 1
)

:: Check if PyInstaller is installed
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo ERROR: PyInstaller not found!
    echo Please install it with: python -m pip install pyinstaller
    exit /b 1
)

:: Generate version file for test build
if exist "version-metadata.yml" (
    echo Generating version_info-win.txt...
    
    :: Try to get version from artisanlib - use temp file to avoid parsing issues
    set ARTISAN_VERSION=3.2.1
    set ARTISAN_BUILD=0
    
    python -c "import artisanlib; print(artisanlib.__version__)" >temp_version.txt 2>nul
    if exist temp_version.txt (
        for /f "usebackq delims=" %%a in ("temp_version.txt") do set ARTISAN_VERSION=%%a
        del temp_version.txt
    )
    
    python -c "import artisanlib; print(artisanlib.__build__)" >temp_build.txt 2>nul
    if exist temp_build.txt (
        for /f "usebackq delims=" %%a in ("temp_build.txt") do set ARTISAN_BUILD=%%a
        del temp_build.txt
    )
    
    :: Clean up any whitespace
    set ARTISAN_VERSION=%ARTISAN_VERSION: =%
    set ARTISAN_BUILD=%ARTISAN_BUILD: =%
    
    echo Creating version file with version %ARTISAN_VERSION%.%ARTISAN_BUILD%...
    
    :: Check if create-version-file command exists, install if needed
    where.exe create-version-file >nul 2>&1
    if errorlevel 1 (
        echo Installing pyinstaller-versionfile...
        python -m pip install pyinstaller-versionfile >nul 2>&1
    )
    
    :: Use create-version-file command (provided by pyinstaller-versionfile)
    create-version-file version-metadata.yml --outfile version_info-win.txt --version %ARTISAN_VERSION%.%ARTISAN_BUILD% 2>nul
    if errorlevel 1 (
        echo WARNING: Could not generate version file, setting version=None in spec...
        powershell -Command "(Get-Content artisan-win-test.spec) -replace \"version='version_info-win.txt'\", \"version=None\" | Set-Content artisan-win-test.spec"
    ) else (
        if not exist "version_info-win.txt" (
            echo WARNING: version_info-win.txt was not created, setting version=None in spec...
            powershell -Command "(Get-Content artisan-win-test.spec) -replace \"version='version_info-win.txt'\", \"version=None\" | Set-Content artisan-win-test.spec"
        ) else (
            echo Version file created successfully.
        )
    )
) else (
    echo WARNING: version-metadata.yml not found, setting version=None in spec...
    powershell -Command "(Get-Content artisan-win-test.spec) -replace \"version='version_info-win.txt'\", \"version=None\" | Set-Content artisan-win-test.spec"
)

echo ========================================
echo Building Artisan Test Version
echo ========================================
echo Python: %PYTHON_PATH%
echo PyQt: %PYQT%
echo Source: %ARTISAN_SRC%
echo ========================================
echo.

:: Build using the test spec file
python -m PyInstaller artisan-win-test.spec

if errorlevel 1 (
    echo.
    echo ERROR: Build failed!
    exit /b 1
)

echo.
echo ========================================
echo Build complete!
echo Test version is in: dist\artisan-test\
echo ========================================