@echo off
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0local-ci.ps1" %*
