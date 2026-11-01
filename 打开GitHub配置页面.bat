@echo off
chcp 65001 >nul
echo ========================================
echo   中东情报工作台 - GitHub 配置向导
echo ========================================
echo.
echo 步骤 1：浏览器会自动打开 GitHub 仓库
echo.
echo 步骤 2：点击 "Add file" -^> "Create new file"
echo.
echo 步骤 3：文件名输入（注意前面的点号）：
echo   .github/workflows/collect.yml
echo.
echo 步骤 4：把下面 collect.yml 文件里的内容全部复制粘贴进去
echo.
echo 步骤 5：点击 "Commit new file"
echo.
echo 步骤 6：Settings -^> Secrets -^> 添加 3 个 Secret
echo   ME_FIRMS    = fc3143c9900d1ff4cacb09d247bd5a51
echo   ME_EIA      = dqb8Rkm8QzzbP76kfkc7GHjHkhGmCLWTfcNCPqPm
echo   ME_AISSTREAM = 09f72bf19ce5231f19ef5fb3eaa30d5d4fcf73e4
echo.
echo 步骤 7：Settings -^> Pages -^> Source 选 "GitHub Actions"
echo.
echo ========================================
echo   按任意键打开 GitHub 仓库页面...
echo ========================================
pause >nul
start https://github.com/win462839-max/-
