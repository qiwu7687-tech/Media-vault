@echo off
SET PYTHONIOENCODING=utf-8

where python >/dev/null 2>/dev/null && (
    python "%~dp0scripts\mediavault.py" auto %*
    exit /b
)
where python3 >/dev/null 2>/dev/null && (
    python3 "%~dp0scripts\mediavault.py" auto %*
    exit /b
)

echo [错误] 未找到 Python，请先安装 Python 3.9+
echo 下载地址：https://www.python.org/downloads/
pause
