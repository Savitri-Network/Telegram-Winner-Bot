@echo off
setlocal ENABLEDELAYEDEXPANSION
title Savitri Rewards Bot - Docker Setup

echo.
echo ================================
echo  Savitri Rewards Bot - SETUP
echo ================================
echo.

:: 1) Check Docker in PATH
where docker >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Docker is not installed or not in PATH.
  echo Download Docker Desktop here: https://www.docker.com/products/docker-desktop
  echo After installing, restart Windows and run this script again.
  pause
  exit /b 1
) else (
  echo [OK] Docker detected.
)

:: 2) Ensure Docker Desktop is running
echo.
echo Checking Docker daemon...
docker info >nul 2>nul
if errorlevel 1 (
  echo [INFO] Starting Docker Desktop...
  :: Try default install path
  start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
  :: Wait loop up to ~150s
  set /a tries=0
  :wait_docker
  set /a tries+=1
  if !tries! GTR 30 (
    echo [ERROR] Docker Desktop did not start in time. Please start it manually and re-run.
    pause
    exit /b 1
  )
  echo Waiting for Docker to be ready... (!tries!/30)
  timeout /t 5 >nul
  docker info >nul 2>nul && goto docker_ready
  goto wait_docker
) else (
  goto docker_ready
)

:docker_ready
echo [OK] Docker is running.

:: 3) Ensure .env exists
if not exist ".env" (
  if exist ".env.example" (
    echo [INFO] .env not found. Creating from .env.example ...
    copy /Y ".env.example" ".env" >nul
    echo [ACTION REQUIRED] Open .env and fill BOT_TOKEN and ADMINS before continuing.
    pause
  ) else (
    echo [ERROR] .env not found and .env.example missing. Please create a .env file.
    pause
    exit /b 1
  )
) else (
  echo [OK] .env file found.
)

:: 4) Build image
echo.
echo [BUILD] docker compose build
docker compose build
if errorlevel 1 (
  echo [ERROR] Build failed. Check Dockerfile and requirements.txt.
  pause
  exit /b 1
)

:: 5) Start container
echo.
echo [UP] docker compose up -d
docker compose up -d
if errorlevel 1 (
  echo [ERROR] Failed to start container.
  pause
  exit /b 1
)

echo.
echo [OK] Container started successfully.
echo You can view logs with: docker compose logs -f
echo.

:: 6) Show last logs
echo [LOGS] Last 10 lines:
docker compose logs --tail 10

echo.
echo Done. The bot should now be online on Telegram.
pause
exit /b 0
