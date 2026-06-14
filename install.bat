@echo off
REM ===== AutoMic 开发环境一键安装 (建虚拟环境 + 装依赖) =====
REM 需要先装好 Python 3.10+ (https://www.python.org/downloads/ 安装时勾选 Add to PATH)
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo [1/3] 创建虚拟环境 .venv ...
python -m venv .venv
if errorlevel 1 (
  echo 创建虚拟环境失败, 请确认已安装 Python 并加入 PATH。
  pause & exit /b 1
)

echo [2/3] 升级 pip ...
call .venv\Scripts\python.exe -m pip install --upgrade pip

echo [3/3] 安装依赖 ...
call .venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
  echo 依赖安装失败。
  pause & exit /b 1
)

echo.
echo 完成! 运行托盘版:  .venv\Scripts\python.exe -m automic
echo 调试(命令行版):   .venv\Scripts\python.exe -m automic.cli
echo 打包成 exe:        build.bat
pause
