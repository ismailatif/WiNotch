@echo off
echo ========================================================
echo        Building WinNotch Standalone Executable (.exe)
echo ========================================================
echo.

:: Ensure dependencies and PyInstaller are installed
echo [*] Checking and installing build dependencies...
python -m pip install --upgrade pip
python -m pip install pyinstaller PySide6 requests psutil
echo.

:: Build executable with PyInstaller
echo [*] Building WinNotch.exe...
pyinstaller --noconsole --onefile --clean --name "WinNotch" --icon "app.ico" island.py

echo.
if exist "dist\WinNotch.exe" (
    echo ========================================================
    echo  [SUCCESS] Build Complete!
    echo  Your executable is ready at: dist\WinNotch.exe
    echo ========================================================
) else (
    echo [ERROR] Build failed. Please check the console output above.
)

pause

