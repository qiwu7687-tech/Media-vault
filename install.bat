@echo off
chcp 65001 >nul
echo ==========================================
echo   Cinema Manager 一键安装
echo ==========================================
echo.

REM Find Python
set PYTHON=
where python >nul 2>nul && set PYTHON=python
where python3 >nul 2>nul && set PYTHON=python3
if "%PYTHON%"=="" (
    echo [错误] 未找到 Python，请先安装 Python 3.8+
    echo 下载地址：https://www.python.org/downloads/
    pause
    exit /b 1
)
echo [√] 找到 %PYTHON%

echo.
echo [1/2] 安装依赖...
%PYTHON% -m pip install -r "%~dp0requirements.txt"
if %errorlevel% neq 0 (
    echo [错误] 依赖安装失败，请检查网络连接
    pause
    exit /b 1
)

echo.
echo [2/2] 运行配置向导...
%PYTHON% "%~dp0scripts\setup.py"

echo.
echo ==========================================
echo   安装完成！
echo.
echo   使用方式：
echo     cinema.bat 电影名
echo     %PYTHON% scripts\cinema.py auto 电影名
echo ==========================================
pause
