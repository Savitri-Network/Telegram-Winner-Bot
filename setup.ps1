# ============================================
# 🚀 Savitri Rewards Bot - Setup & Run Script
# ============================================

Write-Host "`n=== SAVITRI REWARDS BOT SETUP ===`n" -ForegroundColor Cyan

# 1️⃣ Check Docker installation
$dockerVersion = (Get-Command docker -ErrorAction SilentlyContinue)

if (-not $dockerVersion) {
    Write-Host "❌ Docker is not installed or not in PATH." -ForegroundColor Red
    Write-Host "`n➡️  Download and install Docker Desktop from:"
    Write-Host "   https://www.docker.com/products/docker-desktop`n"
    Write-Host "Then restart your computer and run this script again."
    exit 1
} else {
    Write-Host "✅ Docker detected." -ForegroundColor Green
}

# 2️⃣ Ensure Docker Desktop is running
$dockerInfo = docker info 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "🔄 Starting Docker Desktop..." -ForegroundColor Yellow
    Start-Process "Docker Desktop" -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 10
    $retry = 0
    do {
        Write-Host "⏳ Waiting for Docker to start ($retry/30)..." -ForegroundColor Yellow
        Start-Sleep -Seconds 5
        $dockerInfo = docker info 2>$null
        $retry++
    } while (($LASTEXITCODE -ne 0) -and ($retry -lt 30))

    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Docker Desktop did not start in time. Please start it manually and try again." -ForegroundColor Red
        exit 1
    }
}
Write-Host "🐳 Docker is running." -ForegroundColor Green

# 3️⃣ Check for .env file
if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Write-Host "⚙️  Creating .env file from template..." -ForegroundColor Yellow
        Copy-Item ".env.example" ".env"
        Write-Host "⚠️  Please edit the .env file and add your BOT_TOKEN and ADMINS before running again." -ForegroundColor Yellow
        exit 0
    } else {
        Write-Host "❌ No .env or .env.example file found. Please create one." -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "✅ .env file found." -ForegroundColor Green
}

# 4️⃣ Build Docker image
Write-Host "`n🏗️  Building Docker image..." -ForegroundColor Cyan
docker compose build
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Build failed. Check your Dockerfile and requirements.txt." -ForegroundColor Red
    exit 1
}

# 5️⃣ Start container
Write-Host "`n🚀 Starting SavitriRewardsBot container..." -ForegroundColor Cyan
docker compose up -d
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to start container." -ForegroundColor Red
    exit 1
}

Write-Host "`n✅ Container started successfully!" -ForegroundColor Green
Write-Host "   You can check logs anytime using:"
Write-Host "   docker compose logs -f`n" -ForegroundColor Yellow

# 6️⃣ Show short logs
Start-Sleep -Seconds 3
Write-Host "`n📜 Last 10 log lines:" -ForegroundColor Cyan
docker compose logs --tail 10

Write-Host "`n🎯 Done! The bot should now be online on Telegram." -ForegroundColor Green
