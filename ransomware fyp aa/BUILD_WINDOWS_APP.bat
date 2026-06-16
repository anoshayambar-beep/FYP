@echo off
title Build Windows App
cd /d "%~dp0my_fyp frontend"
echo.
echo Building Windows app (first time may take 5-15 minutes)...
echo.
call flutter pub get
call flutter build windows
if errorlevel 1 (
  echo.
  echo BUILD FAILED. See errors above.
  pause
  exit /b 1
)
echo.
echo BUILD SUCCESS!
echo App location:
echo %cd%\build\windows\x64\runner\Release\my_fyp.exe
echo.
pause
