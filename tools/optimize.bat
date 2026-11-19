@echo off
chcp 65001 >nul
setlocal

if "%~1"=="" (
  echo.
  echo 用法：把 .glb 文件直接拖到这个 bat 上
  echo       或在命令行执行：optimize.bat 模型.glb
  echo.
  pause
  exit /b 1
)

set "SRC=%~1"
set "DST=%~dpn1.opt.glb"

echo ============================================
echo  源文件：%SRC%
echo  输出：  %DST%
echo ============================================
echo.

echo [1/2] 优化中（去重 / 精简 / 贴图降采样）...
REM 注意：必须用 --compress false。
REM 实测 XR-FRAME 不支持 KHR_draco_mesh_compression 和 EXT_meshopt_compression，
REM 加了这两个压缩的 GLB 在小程序里会加载失败（黑屏）。
call npx --yes @gltf-transform/cli optimize "%SRC%" "%DST%" --compress false --texture-size 1024

if errorlevel 1 (
  echo.
  echo [失败] 优化出错了，把上面的报错发给我。
  pause
  exit /b 1
)

echo.
echo [2/2] 完成
for %%F in ("%SRC%") do echo   优化前：%%~zF 字节
for %%F in ("%DST%") do echo   优化后：%%~zF 字节
echo.
echo 提示：把 .opt.glb 上传到 COS，然后更新 assets/models.json 里的 url
echo.
pause
