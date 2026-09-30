# ==============================================================================
# 🏰 CASTLEWEB — Local Dev Suite for Windows
# Architecture: Monorepo (FastAPI + Vite/React + PostgreSQL + Redis + Nginx)
# Requires: Docker Desktop for Windows / PowerShell 5.1+
# ==============================================================================

[CmdletBinding()]
param(
    [ValidateSet("Full", "FrontendOnly", "BackendOnly", "ConfigOnly", "Migrate", "Status", "RunNative", "Help")]
    [string]$Mode = "Full",
    [switch]$FrontendOnly,
    [switch]$BackendOnly,
    [switch]$ConfigOnly,
    [switch]$Migrate,
    [switch]$Status,
    [switch]$RunNative,
    [switch]$Help
)

$ErrorActionPreference = "Stop"

# --- Directory and file paths ---
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir
$BackendDir = Join-Path $RootDir "apps\backend"
$FrontendDir = Join-Path $RootDir "apps\frontend"
$FrontendDist = Join-Path $FrontendDir "dist"
$NginxDir = Join-Path $RootDir "nginx"
$EnvFile = Join-Path $BackendDir ".env"
$DockerComposeFile = Join-Path $RootDir "docker-compose.prod.yml"
$UploadsDir = Join-Path $RootDir "uploads"
$PlaceholderSource = Join-Path $ScriptDir "placeholder.html"

function Show-Banner {
    Write-Host "   ____    _    ____ _____ _     _______        _______ ____  " -ForegroundColor Magenta
    Write-Host "  / ___|  / \  / ___|_   _| |   | ____\ \      / / ____| __ ) " -ForegroundColor Magenta
    Write-Host " | |     / _ \ \___ \ | | | |   |  _|  \ \ /\ / /|  _| |  _ \ " -ForegroundColor Magenta
    Write-Host " | |___ / ___ \ ___) || | | |___| |___  \ V  V / | |___| |_) |" -ForegroundColor Magenta
    Write-Host "  \____/_/   \_\____/ |_| |_____|_____|  \_/\_/  |_____|____/ " -ForegroundColor Magenta
    Write-Host "       Local Dev Suite - Windows Edition (Docker Desktop)" -ForegroundColor Magenta
    Write-Host "=================================================================" -ForegroundColor Magenta
}

function Log-Step([string]$message) { Write-Host "`n==> $message" -ForegroundColor Cyan }
function Log-Info([string]$message) { Write-Host "  [INFO] $message" -ForegroundColor Gray }
function Log-Success([string]$message) { Write-Host "  [+] $message" -ForegroundColor Green }
function Log-Warn([string]$message) { Write-Host "  [!] $message" -ForegroundColor Yellow }
function Log-Error([string]$message) { Write-Host "  [x] ERROR: $message" -ForegroundColor Red }

function Test-DockerEngine {
    Log-Step "Проверка готовности Docker Desktop"
    if (-not (Get-Command "docker" -ErrorAction SilentlyContinue)) {
        Log-Error "Docker не установлен в системе!"
        Write-Host "Скачайте и установите: https://www.docker.com/products/docker-desktop/" -ForegroundColor Yellow
        exit 1
    }

    $dockerOutput = & docker info 2>&1 | Out-String
    if ($LASTEXITCODE -eq 0) {
        Log-Success "Docker Desktop работает и готов к запуску."
    } else {
        Log-Error "Docker Desktop запущен, но движок контейнеров не может стартовать."
        Write-Host "`n  [!] Причина: Docker Desktop на Windows требует подсистему WSL 2." -ForegroundColor Yellow
        Write-Host "      В Windows она не установлена, поэтому Docker Desktop выдает ошибку." -ForegroundColor Yellow
        Write-Host "      Чтобы запустить Docker на Windows:" -ForegroundColor White
        Write-Host "      1. Откройте PowerShell от имени Администратора" -ForegroundColor Cyan
        Write-Host "      2. Выполните: wsl.exe --install" -ForegroundColor Cyan
        Write-Host "      3. Перезагрузите компьютер`n" -ForegroundColor Cyan
        Write-Host "  💡 Но Docker на вашем компьютере НЕ ОБЯЗАТЕЛЕН для работы прямо сейчас!" -ForegroundColor Green
        Write-Host "     * Запуск бэкенда нативно:   .\scripts\deploy.ps1 -RunNative" -ForegroundColor White
        Write-Host "     * Настройка .env файлов:     .\scripts\deploy.ps1 -ConfigOnly" -ForegroundColor White
        Write-Host "     * Боевой VDS сервер (Linux): sudo ./scripts/deploy.sh`n" -ForegroundColor White
        exit 1
    }
}

function New-RandomSecret([int]$length = 32) {
    $bytes = New-Object byte[] $length
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    $rng.GetBytes($bytes)
    return [BitConverter]::ToString($bytes).Replace("-", "").ToLower()
}

function Setup-AdminEnv {
    Log-Step "Конфигурация окружения (.env)"

    if (Test-Path $EnvFile) {
        $reconfig = Read-Host "Файл .env уже существует. Перезаписать? [y/N]"
        if ($reconfig -notmatch '^[yY]') {
            Log-Success "Используем текущий .env"
            return
        }
    }

    $DomainName = Read-Host "1. Доменное имя проекта [castleweb.ru]"
    if ([string]::IsNullOrWhiteSpace($DomainName)) { $DomainName = "castleweb.ru" }

    $TelegramBotToken = Read-Host "2. Telegram Bot Token (от @BotFather)"
    $TelegramChatId = Read-Host "3. Telegram Chat ID"
    $TelegramProxyUrl = Read-Host "4. Telegram Proxy URL [https://api.telegram.org]"
    if ([string]::IsNullOrWhiteSpace($TelegramProxyUrl)) { $TelegramProxyUrl = "https://api.telegram.org" }

    $TurnstileSecret = Read-Host "5. Turnstile Secret Key [1x0000000000000000000000000000000AA]"
    if ([string]::IsNullOrWhiteSpace($TurnstileSecret)) { $TurnstileSecret = "1x0000000000000000000000000000000AA" }

    $UseR2 = Read-Host "6. Использовать Cloudflare R2? [y/N]"
    $StorageDriver = "local"
    $R2AccountId = ""; $R2AccessKey = ""; $R2SecretKey = ""; $R2Bucket = ""; $R2PublicUrl = ""

    if ($UseR2 -match '^[yY]') {
        $StorageDriver = "r2"
        $R2AccountId = Read-Host "   Cloudflare Account ID"
        $R2AccessKey = Read-Host "   R2 Access Key"
        $R2SecretKey = Read-Host "   R2 Secret Key"
        $R2Bucket = Read-Host "   R2 Bucket Name [castleweb-storage]"
        if ([string]::IsNullOrWhiteSpace($R2Bucket)) { $R2Bucket = "castleweb-storage" }
        $R2PublicUrl = Read-Host "   R2 Public CDN URL"
    } else {
        if (-not (Test-Path $UploadsDir)) { New-Item -ItemType Directory -Path $UploadsDir -Force | Out-Null }
        Log-Info "Хранение файлов переключено на локальный каталог /uploads"
    }

    $PostgresPassword = New-RandomSecret 16
    $AppSecretKey = New-RandomSecret 32

    $TurnstileEnabled = if ($TurnstileSecret -ne "1x0000000000000000000000000000000AA" -and -not [string]::IsNullOrWhiteSpace($TurnstileSecret)) { "True" } else { "False" }

    $tgBase = $TelegramProxyUrl.TrimEnd('/')
    $telegramApiBase = if ($tgBase.EndsWith('/bot')) { $tgBase } else { "$tgBase/bot" }

    if (-not (Test-Path $BackendDir)) { New-Item -ItemType Directory -Path $BackendDir -Force | Out-Null }

    $lines = @(
        "# ==============================================================================",
        "# CASTLEWEB STUDIO - Local Development Configuration",
        "# ==============================================================================",
        "APP_ENV=development",
        "DEBUG=True",
        "ENABLE_DOCS=True",
        "DOMAIN_NAME=$DomainName",
        "ADMIN_EMAIL=admin@$DomainName",
        "SECRET_KEY=$AppSecretKey",
        "STORAGE_DRIVER=$StorageDriver",
        "UPLOAD_DIR=/uploads",
        "POSTGRES_USER=castleweb_user",
        "POSTGRES_PASSWORD=$PostgresPassword",
        "POSTGRES_DB=castleweb_db",
        "DATABASE_URL=postgresql+asyncpg://castleweb_user:${PostgresPassword}@postgres:5432/castleweb_db",
        "REDIS_URL=redis://redis:6379/0",
        "CORS_ORIGINS=http://localhost,http://localhost:3000,http://localhost:5173,https://$DomainName",
        "CLOUDFLARE_TURNSTILE_SECRET_KEY=$TurnstileSecret",
        "TURNSTILE_SECRET_KEY=$TurnstileSecret",
        "CLOUDFLARE_TURNSTILE_ENABLED=$TurnstileEnabled",
        "TELEGRAM_BOT_TOKEN=$TelegramBotToken",
        "TELEGRAM_CHAT_ID=$TelegramChatId",
        "TELEGRAM_API_BASE_URL=$telegramApiBase",
        "TELEGRAM_PROXY_URL=$TelegramProxyUrl",
        "R2_ACCOUNT_ID=$R2AccountId",
        "R2_ACCESS_KEY_ID=$R2AccessKey",
        "R2_SECRET_ACCESS_KEY=$R2SecretKey",
        "R2_BUCKET_NAME=$R2Bucket",
        "R2_PUBLIC_DOMAIN=$R2PublicUrl",
        "CLOUDFLARE_R2_ACCOUNT_ID=$R2AccountId",
        "CLOUDFLARE_R2_ACCESS_KEY_ID=$R2AccessKey",
        "CLOUDFLARE_R2_SECRET_ACCESS_KEY=$R2SecretKey",
        "CLOUDFLARE_R2_BUCKET_NAME=$R2Bucket",
        "CLOUDFLARE_R2_PUBLIC_URL=$R2PublicUrl"
    )

    [System.IO.File]::WriteAllLines($EnvFile, $lines, [System.Text.Encoding]::UTF8)
    Log-Success "Конфигурация сохранена в $EnvFile"
}

function Setup-NginxLocalConfig {
    Log-Step "Конфигурация Nginx для локальной разработки"
    $confDir = Join-Path $NginxDir "conf.d"
    if (-not (Test-Path $confDir)) { New-Item -ItemType Directory -Path $confDir -Force | Out-Null }
    
    # Гарантируем наличие путей для монтирования томов certbot на Windows
    if (-not (Test-Path "C:\etc\letsencrypt")) { New-Item -ItemType Directory -Path "C:\etc\letsencrypt" -Force | Out-Null }
    if (-not (Test-Path "C:\var\www\certbot")) { New-Item -ItemType Directory -Path "C:\var\www\certbot" -Force | Out-Null }

    $localConf = Join-Path $confDir "default.conf"
    $nginxContent = @"
upstream backend_upstream {
    server backend:8000;
    keepalive 32;
}

server {
    listen 80;
    server_name localhost 127.0.0.1 _;

    client_max_body_size 50M;

    # Frontend SPA static
    location / {
        root /var/www/castleweb/frontend;
        index index.html;
        try_files `$uri `$uri/ /index.html;
    }

    # Hashed assets
    location /assets/ {
        root /var/www/castleweb/frontend;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Backend API & Swagger Proxy
    location ~ ^/(api|docs|redoc|openapi.json) {
        proxy_pass http://backend_upstream;
        proxy_http_version 1.1;
        proxy_set_header Upgrade `$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host `$host;
        proxy_set_header X-Real-IP `$remote_addr;
        proxy_set_header X-Forwarded-For `$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto `$scheme;
    }

    # Uploads
    location /uploads/ {
        alias /app/uploads/;
        expires 30d;
    }
}
"@
    [System.IO.File]::WriteAllText($localConf, $nginxContent, [System.Text.Encoding]::UTF8)
    Log-Success "Локальная конфигурация Nginx настроена на HTTP порт 80 (без требования Let's Encrypt на Windows)."
}

function Build-Frontend {
    Log-Step "Сборка фронтенда"
    if (-not (Test-Path $FrontendDist)) { New-Item -ItemType Directory -Path $FrontendDist -Force | Out-Null }

    $PackageJson = Join-Path $FrontendDir "package.json"
    if (Test-Path $PackageJson) {
        if (Get-Command "npm" -ErrorAction SilentlyContinue) {
            Log-Info "Обнаружен локальный Node.js/npm. Выполняем сборку напрямую..."
            Push-Location $FrontendDir
            try {
                & npm run build
                if ($LASTEXITCODE -eq 0) {
                    Log-Success "Фронтенд скомпилирован в apps/frontend/dist"
                } else {
                    Log-Warn "Сборка через локальный npm вернула ошибку, пробуем Docker..."
                    $dockerPath = $FrontendDir.Replace("\", "/")
                    & docker run --rm -v "${dockerPath}:/app" -w /app node:22-alpine sh -c "npm install --include=optional && npm run build"
                }
            } finally {
                Pop-Location
            }
        } else {
            $dockerPath = $FrontendDir.Replace("\", "/")
            & docker run --rm -v "${dockerPath}:/app" -w /app node:22-alpine sh -c "npm install --include=optional && npm run build"
            Log-Success "Фронтенд скомпилирован через Docker в apps/frontend/dist"
        }
    } else {
        $targetFile = Join-Path $FrontendDist "index.html"
        if (Test-Path $PlaceholderSource) {
            Copy-Item -Path $PlaceholderSource -Destination $targetFile -Force
        } else {
            [System.IO.File]::WriteAllText($targetFile, "<h1>CASTLEWEB Local Dev Active</h1>", [System.Text.Encoding]::UTF8)
        }
        Log-Success "Создана локальная заглушка: $targetFile"
    }
}

function Launch-Containers {
    Log-Step "Запуск контейнеров и миграций базы данных"
    Setup-NginxLocalConfig

    docker compose -f $DockerComposeFile up -d --build

    Log-Info "Ожидание старта бэкенда и базы данных (до 30 сек)..."
    $ready = $false
    for ($i = 1; $i -le 30; $i++) {
        try {
            $resp = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/health" -UseBasicParsing -TimeoutSec 1 -ErrorAction SilentlyContinue
            if ($resp.StatusCode -eq 200) {
                $ready = $true
                break
            }
        } catch { }
        Start-Sleep -Seconds 1
    }

    if ($ready) {
        Log-Success "Бэкенд успешно отвечает на /api/v1/health!"
    } else {
        Log-Warn "Бэкенд еще запускается (проверьте docker compose logs backend)."
    }

    Log-Info "Применение миграций Alembic..."
    try {
        docker compose -f $DockerComposeFile exec -T backend alembic upgrade head
        Log-Success "Миграции базы данных успешно выполнены!"
    } catch {
        Log-Warn "Alembic завершил выполнение с предупреждением."
    }

    Write-Host "`n=================================================================" -ForegroundColor Green
    Write-Host "   Стек успешно запущен в Docker Desktop на Windows!           " -ForegroundColor Green
    Write-Host "=================================================================" -ForegroundColor Green
    Write-Host "  * Сайт / Фронт:       http://localhost/" -ForegroundColor White
    Write-Host "  * Swagger API:        http://localhost:8000/docs" -ForegroundColor White
    Write-Host "  * Healthcheck:        http://localhost:8000/api/v1/health" -ForegroundColor White
    Write-Host "=================================================================`n" -ForegroundColor Green
}

# --- Router ---
if ($FrontendOnly) { $Mode = "FrontendOnly" }
if ($BackendOnly)  { $Mode = "BackendOnly" }
if ($ConfigOnly)   { $Mode = "ConfigOnly" }
if ($Migrate)      { $Mode = "Migrate" }
if ($Status)       { $Mode = "Status" }
if ($RunNative)    { $Mode = "RunNative" }
if ($Help)         { $Mode = "Help" }

switch ($Mode) {
    "RunNative" {
        Show-Banner
        Log-Step "Запуск бэкенда нативно на Windows (без Docker)"
        $venvPython = Join-Path $RootDir "apps\backend\.venv\Scripts\python.exe"
        if (Test-Path $venvPython) {
            Write-Host "`n  * Swagger API: http://127.0.0.1:8000/docs" -ForegroundColor Green
            Write-Host "  * Healthcheck: http://127.0.0.1:8000/api/v1/health" -ForegroundColor Green
            Write-Host "  * Нажмите Ctrl+C для остановки сервера`n" -ForegroundColor Yellow
            & $venvPython -m uvicorn app.main:app --app-dir (Join-Path $RootDir "apps\backend") --reload --port 8000
        } else {
            Log-Error "Виртуальное окружение не найдено в apps\backend\.venv!"
        }
    }
    "FrontendOnly" {
        Show-Banner
        Build-Frontend
        docker compose -f $DockerComposeFile exec -T nginx nginx -s reload
    }
    "BackendOnly" {
        Show-Banner
        docker compose -f $DockerComposeFile build backend
        docker compose -f $DockerComposeFile up -d --no-deps backend
        docker compose -f $DockerComposeFile exec -T backend alembic upgrade head
    }
    "Migrate" {
        docker compose -f $DockerComposeFile exec -T backend alembic upgrade head
    }
    "ConfigOnly" {
        Show-Banner
        Setup-AdminEnv
    }
    "Status" {
        Show-Banner
        docker compose -f $DockerComposeFile ps
    }
    "Full" {
        Show-Banner
        Test-DockerEngine
        Setup-AdminEnv
        Build-Frontend
        Launch-Containers
    }
    Default {
        Write-Host "Команды: .\scripts\deploy.ps1 [-Full | -RunNative | -ConfigOnly | -FrontendOnly | -BackendOnly | -Migrate | -Status]"
    }
}
