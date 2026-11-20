@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

rem ============================================
rem  批量把 FBX / OBJ / STL / DAE 转成 GLB
rem  用法：把文件夹直接拖到本 bat 上
rem  原文件不会被修改，输出在新目录 converted\
rem ============================================

if "%~1"=="" (
  echo.
  echo   用法：把包含模型的文件夹拖到本文件上
  echo   支持：FBX / OBJ / STL / DAE / GLB / GLTF
  echo.
  pause
  exit /b 1
)

set "SRC=%~1"
if not exist "%SRC%\" (
  echo [错误] 这不是一个文件夹：%SRC%
  pause
  exit /b 1
)

rem 去掉结尾的反斜杠
if "%SRC:~-1%"=="\" set "SRC=%SRC:~0,-1%"
set "DST=%SRC%\converted"

rem ---------- 查找 Blender ----------
set "BLENDER="
for %%D in ("C:\Program Files" "D:\Program Files" "E:\Program Files" "F:\Program Files") do (
  if not defined BLENDER (
    for /d %%V in ("%%~D\Blender Foundation\Blender*") do (
      if exist "%%~V\blender.exe" set "BLENDER=%%~V\blender.exe"
    )
  )
)
if not defined BLENDER (
  for /f "delims=" %%i in ('where blender 2^>nul') do if not defined BLENDER set "BLENDER=%%i"
)

if not defined BLENDER (
  echo.
  echo [错误] 没有找到 blender.exe
  echo        请确认已安装 Blender，或把 Blender 加入 PATH
  echo.
  pause
  exit /b 1
)

echo.
echo ============================================
echo   Blender : %BLENDER%
echo   源目录  : %SRC%
echo   输出到  : %DST%
echo ============================================
echo.

rem ---------- 第一步：批量转换 ----------
"%BLENDER%" -b -P "%~dp0batch-convert.py" -- "%SRC%" "%DST%"

if errorlevel 1 (
  echo.
  echo [错误] 转换过程中出现问题，请查看上面的日志
  pause
  exit /b 1
)

rem ---------- 第二步：可选优化 ----------
set /p OPT=是否继续做优化（减面+贴图降采样）？[Y/N]:
if /i not "%OPT%"=="Y" goto :done

set "OPT_OUT=%DST%\optimized"
if not exist "%OPT_OUT%" mkdir "%OPT_OUT%"

set "TOOLS=%~dp0"
if not exist "%TOOLS%node_modules" (
  echo [提示] tools 目录缺少依赖，跳过优化
  goto :done
)

echo.
echo ---- 正在优化（最多等几分钟）----
pushd "%TOOLS%"
for %%f in ("%DST%\*.glb") do (
  echo   优化 %%~nxf
  call npx --no-install @gltf-transform/cli optimize "%%~ff" "%OPT_OUT%\%%~nf.glb" --compress false --texture-size 1024 >nul 2>&1
  if errorlevel 1 (
    echo     ✗ 失败，已保留未优化版本
  ) else (
    echo     ✓ 完成
  )
)
popd

echo.
echo 优化结果在：%OPT_OUT%

:done
echo.
echo ============================================
echo   完成
echo   转换结果：%DST%
echo   报告文件：%DST%\_report.csv
echo ============================================
echo.
pause
