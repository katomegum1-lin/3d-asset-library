@echo off
chcp 65001 >nul
cd /d "%~dp0"

rem 优先用 pythonw（不弹黑色命令行窗口）
where pythonw >nul 2>&1
if %errorlevel%==0 (
    start "" pythonw "%~dp0asset-forge.py"
    exit /b 0
)

rem 没有 pythonw 就用 python
where python >nul 2>&1
if %errorlevel%==0 (
    python "%~dp0asset-forge.py"
    if errorlevel 1 (
        echo.
        echo [错误] 启动失败，详情见 asset-forge-error.log
        pause
    )
    exit /b 0
)

echo.
echo [错误] 没有找到 Python
echo        请安装 Python 3 并勾选 "Add Python to PATH"
echo.
pause
