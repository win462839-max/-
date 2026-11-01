@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo  推送到 GitHub（首次会弹出浏览器让你登录）
echo ============================================
echo.
set /p REPO=粘贴仓库地址(https://github.com/用户名/仓库名.git):

if "%REPO%"=="" (
  echo 未输入地址，已取消。
  pause
  exit /b
)

git remote remove origin >nul 2>&1
git remote add origin "%REPO%"
git branch -M main

echo.
echo 正在推送... 若弹出浏览器窗口，请完成登录授权。
git push -u origin main

if errorlevel 1 (
  echo.
  echo 推送失败。常见原因：
  echo   1. 仓库地址填写有误
  echo   2. 浏览器登录未完成
  echo   3. 仓库不是空的（请在创建时不要勾选 README/.gitignore）
) else (
  echo.
  echo 推送成功！
  echo 最后一步：打开仓库 Settings - Pages - Source，选择 GitHub Actions
  echo 几分钟后即可通过在线链接访问看板。
)
pause
