@echo off
title Ransomware Detection App
set "RELEASE=%~dp0my_fyp frontend\build\windows\x64\runner\Release"
set "EXE=%RELEASE%\my_fyp.exe"
set "DATA=%RELEASE%\data"

if not exist "%EXE%" (
  echo App not built. Running fix script...
  powershell -ExecutionPolicy Bypass -File "%~dp0FIX_AND_LAUNCH_APP.ps1"
  exit /b 0
)

if not exist "%DATA%\app.so" (
  echo Fixing missing app files...
  powershell -ExecutionPolicy Bypass -File "%~dp0FIX_AND_LAUNCH_APP.ps1"
  exit /b 0
)

cd /d "%RELEASE%"
start "" "%EXE%"
