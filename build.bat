@echo off
REM ===== 一键打包: 先生成 AutoMic.exe, 再(若装了 Inno Setup)打出一键安装包 =====
REM 先跑过 install.bat 安装好依赖。
REM   产物1: dist\AutoMic.exe          (免安装单文件)
REM   产物2: installer\Output\AutoMic-Setup.exe (一键安装包, 需 Inno Setup)
chcp 65001 >nul
setlocal
cd /d "%~dp0"

if exist .venv\Scripts\python.exe (
  set "PY=.venv\Scripts\python.exe"
) else (
  set "PY=python"
)

echo [1/3] 生成应用图标 ...
%PY% tools\make_icon.py

echo [2/3] 打包 AutoMic.exe (首次较慢) ...
%PY% -m PyInstaller automic.spec --clean --noconfirm
if errorlevel 1 (
  echo 打包 exe 失败。
  pause & exit /b 1
)

echo [3/3] 编译一键安装包 ...
set "ISCC="
where iscc >nul 2>nul && set "ISCC=iscc"
if not defined ISCC if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%LocalAppData%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LocalAppData%\Programs\Inno Setup 6\ISCC.exe"
if not defined ISCC (
  echo 未检测到 Inno Setup, 跳过安装包。仅生成了 dist\AutoMic.exe。
  echo 安装 Inno Setup: https://jrsoftware.org/isdl.php  然后重跑本脚本。
  pause & exit /b 0
)
"%ISCC%" installer\AutoMic.iss
if errorlevel 1 (
  echo 编译安装包失败。
  pause & exit /b 1
)

echo.
echo 完成!
echo   免安装单文件: dist\AutoMic.exe
echo   一键安装包:   installer\Output\AutoMic-Setup.exe
pause
