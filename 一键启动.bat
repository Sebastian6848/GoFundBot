@echo off
setlocal

echo =========================================
echo   GoFundBot start (conda: fundbot)
echo =========================================

REM 检查 conda 是否可用
where conda >nul 2>nul
if %errorlevel% neq 0 (
  echo [ERROR] Conda was not found. Please configure Conda in the system PATH first.
  echo  You can first run this script in the Anaconda Prompt.
  pause
  exit /b 1
)

REM 启动后端 (新窗口)
start "GoFundBot Backend" cmd /k "call conda activate fundbot && python Backend\app.py"

REM 启动前端 (新窗口)
start "GoFundBot Frontend" cmd /k "cd Frontend && npm run dev"

echo [OK] The backend and frontend have been activated.
echo     backend: http://127.0.0.1:5000
echo     frontend: http://127.0.0.1:5173
pause
