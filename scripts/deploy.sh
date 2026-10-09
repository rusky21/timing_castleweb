#!/usr/bin/env bash
# ==============================================================================
# 🏰 CASTLEWEB — Production Deployment Suite
# Target OS: Ubuntu 22.04 / 24.04 / 26.04 LTS (x86_64 / arm64)
# Architecture: Monorepo (FastAPI + Vite/React + PostgreSQL + Redis + Nginx)
# ==============================================================================

set -euo pipefail

# --- Color palette ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# --- Directory & File Paths ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKEND_DIR="${ROOT_DIR}/apps/backend"
FRONTEND_DIR="${ROOT_DIR}/apps/frontend"
FRONTEND_DIST="${FRONTEND_DIR}/dist"
NGINX_DIR="${ROOT_DIR}/nginx"
ENV_FILE="${BACKEND_DIR}/.env"
PARSER_ENV_FILE="${ROOT_DIR}/apps/parser/.env"
DOCKER_COMPOSE_FILE="${ROOT_DIR}/docker-compose.prod.yml"
UPLOADS_DIR="${ROOT_DIR}/uploads"

log_banner() {
    echo -e "${PURPLE}${BOLD}"
    cat <<'BANNER'
   ____    _    ____ _____ _     _______        _______ ____  
  / ___|  / \  / ___|_   _| |   | ____\ \      / / ____| __ ) 
 | |     / _ \ \___ \ | | | |   |  _|  \ \ /\ / /|  _| |  _ \ 
 | |___ / ___ \ ___) || | | |___| |___  \ V  V / | |___| |_) |
  \____/_/   \_\____/ |_| |_____|_____|  \_/\_/  |_____|____/ 
BANNER
    echo -e "       Production Deployment Suite • Ubuntu Edition${NC}"
    echo -e "${CYAN}=================================================================${NC}\n"
}

log_step() { echo -e "\n${BOLD}${CYAN}==>${NC} ${BOLD}$1${NC}"; }
log_info() { echo -e "  ${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "  ${GREEN}[✓]${NC} $1"; }
log_warn() { echo -e "  ${YELLOW}[!]${NC} $1"; }
log_error() { echo -e "  ${RED}[✗] ERROR:${NC} $1" >&2; }

check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "Этот этап требует прав суперпользователя (root)."
        echo -e "Пожалуйста, запустите скрипт через: ${BOLD}sudo $0 $@${NC}"
        exit 1
    fi
}

setup_admin_env() {
    log_step "Блок 0: Конфигурация переменных окружения и секретов (.env)"

    if [ -f "$ENV_FILE" ]; then
        log_info "Обнаружен существующий файл: $ENV_FILE"
        read -r -p "Хотите перезаписать конфигурацию заново? [y/N]: " RECONFIGURE
        if [[ ! "$RECONFIGURE" =~ ^([yY][eE][sS]|[yY])$ ]]; then
            log_success "Используем существующий файл конфигурации."
            return 0
        fi
    fi

    echo -e "\n${YELLOW}=== Мастер начальной настройки CASTLEWEB ===${NC}"
    echo -e "Введите параметры продакшн-сервера. Нажмите [Enter] для значений по умолчанию.\n"

    read -r -p "1. Доменное имя проекта [castleweb.ru]: " DOMAIN_NAME
    DOMAIN_NAME="${DOMAIN_NAME:-castleweb.ru}"

    read -r -p "2. Email администратора (для Let's Encrypt SSL) [admin@${DOMAIN_NAME}]: " ADMIN_EMAIL
    ADMIN_EMAIL="${ADMIN_EMAIL:-admin@${DOMAIN_NAME}}"

    echo -e "\n${CYAN}--- Telegram Headless CRM ---${NC}"
    while true; do
        read -r -p "3. Telegram Bot Token (от @BotFather): " TELEGRAM_BOT_TOKEN
        [ -n "$TELEGRAM_BOT_TOKEN" ] && break
        log_warn "Токен бота обязателен для работы CRM! Попробуйте снова."
    done

    while true; do
        read -r -p "4. Telegram Chat ID (ID закрытого чата инженеров): " TELEGRAM_CHAT_ID
        [ -n "$TELEGRAM_CHAT_ID" ] && break
        log_warn "Chat ID обязателен для получения заявок! Попробуйте снова."
    done

    read -r -p "5. Telegram Proxy URL (Cloudflare Worker или прямой) [https://api.telegram.org]: " TELEGRAM_PROXY_URL
    TELEGRAM_PROXY_URL="${TELEGRAM_PROXY_URL:-https://api.telegram.org}"

    echo -e "\n${CYAN}--- Безопасность и Защита от спама ---${NC}"
    read -r -p "6. Cloudflare Turnstile Secret Key [1x0000000000000000000000000000000AA]: " TURNSTILE_SECRET_KEY
    TURNSTILE_SECRET_KEY="${TURNSTILE_SECRET_KEY:-1x0000000000000000000000000000000AA}"

    DEFAULT_DB_PASS=$(openssl rand -base64 18 | tr -dc 'a-zA-Z0-9' | head -c 24)
    read -r -p "7. Пароль PostgreSQL [Сгенерирован автоматически]: " POSTGRES_PASSWORD
    POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-$DEFAULT_DB_PASS}"

    DEFAULT_REDIS_PASS=$(openssl rand -base64 12 | tr -dc 'a-zA-Z0-9' | head -c 16)
    read -r -p "8. Пароль Redis [Сгенерирован автоматически]: " REDIS_PASSWORD
    REDIS_PASSWORD="${REDIS_PASSWORD:-$DEFAULT_REDIS_PASS}"

    DEFAULT_SECRET_KEY=$(openssl rand -hex 32)
    read -r -p "9. Секретный ключ приложения (SECRET_KEY) [Сгенерирован автоматически]: " SECRET_KEY
    SECRET_KEY="${SECRET_KEY:-$DEFAULT_SECRET_KEY}"

    # Auto-generate Telegram Webhook secret and Parser internal secret
    TELEGRAM_WEBHOOK_SECRET=$(openssl rand -hex 32)
    INTERNAL_API_SECRET=$(openssl rand -hex 24)

    echo -e "\n${CYAN}--- Хранилище файлов портфолио и ТЗ клиентов ---${NC}"
    read -r -p "Использовать облачное хранилище Cloudflare R2? (требует карту) [y/N]: " USE_R2
    R2_ACCOUNT_ID=""
    R2_ACCESS_KEY=""
    R2_SECRET_KEY=""
    R2_BUCKET=""
    R2_PUBLIC_URL=""
    STORAGE_DRIVER="local"

    if [[ "$USE_R2" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        STORAGE_DRIVER="r2"
        read -r -p "  - Cloudflare Account ID: " R2_ACCOUNT_ID
        read -r -p "  - R2 Access Key ID: " R2_ACCESS_KEY
        read -r -p "  - R2 Secret Access Key: " R2_SECRET_KEY
        read -r -p "  - R2 Bucket Name [castleweb-storage]: " R2_BUCKET
        R2_BUCKET="${R2_BUCKET:-castleweb-storage}"
        read -r -p "  - R2 Public CDN URL (https://cdn.castleweb.ru): " R2_PUBLIC_URL
    else
        log_info "Файлы будут надежно сохраняться локально на VDS в каталоге uploads/."
        mkdir -p "$UPLOADS_DIR"
        chmod 775 "$UPLOADS_DIR"
    fi

    # Turnstile auto-enable
    CLOUDFLARE_TURNSTILE_ENABLED="False"
    if [ -n "$TURNSTILE_SECRET_KEY" ] && [ "$TURNSTILE_SECRET_KEY" != "1x0000000000000000000000000000000AA" ]; then
        CLOUDFLARE_TURNSTILE_ENABLED="True"
    fi

    # Telegram API URL normalization (ensure /bot suffix for backend)
    TG_BASE="${TELEGRAM_PROXY_URL%/}"
    if [[ "$TG_BASE" == */bot ]]; then
        TELEGRAM_API_BASE_URL="${TG_BASE}"
    else
        TELEGRAM_API_BASE_URL="${TG_BASE}/bot"
    fi

    mkdir -p "$BACKEND_DIR"
    (
        umask 077
        cat > "$ENV_FILE" <<EOF
# ==============================================================================
# CASTLEWEB STUDIO — Production Environment Configuration
# Generated on: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
# ==============================================================================

APP_ENV=production
DEBUG=False
ENABLE_DOCS=True
DOMAIN_NAME=${DOMAIN_NAME}
ADMIN_EMAIL=${ADMIN_EMAIL}
SECRET_KEY=${SECRET_KEY}

# Storage Mode
STORAGE_DRIVER=${STORAGE_DRIVER}
UPLOAD_DIR=/app/uploads

# Database & Cache
POSTGRES_USER=castleweb_user
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
POSTGRES_DB=castleweb_db
DATABASE_URL=postgresql+asyncpg://castleweb_user:${POSTGRES_PASSWORD}@postgres:5432/castleweb_db
REDIS_PASSWORD=${REDIS_PASSWORD}
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0

# Security & CORS
CORS_ORIGINS=https://${DOMAIN_NAME},https://www.${DOMAIN_NAME}
CLOUDFLARE_TURNSTILE_SECRET_KEY=${TURNSTILE_SECRET_KEY}
TURNSTILE_SECRET_KEY=${TURNSTILE_SECRET_KEY}
CLOUDFLARE_TURNSTILE_ENABLED=${CLOUDFLARE_TURNSTILE_ENABLED}

# Telegram Headless CRM
TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID}
TELEGRAM_API_BASE_URL=${TELEGRAM_API_BASE_URL}
TELEGRAM_PROXY_URL=${TELEGRAM_PROXY_URL}
TELEGRAM_WEBHOOK_SECRET=${TELEGRAM_WEBHOOK_SECRET}

# Cloudflare R2 / S3 Storage
R2_ACCOUNT_ID=${R2_ACCOUNT_ID}
R2_ACCESS_KEY_ID=${R2_ACCESS_KEY}
R2_SECRET_ACCESS_KEY=${R2_SECRET_KEY}
R2_BUCKET_NAME=${R2_BUCKET}
R2_PUBLIC_DOMAIN=${R2_PUBLIC_URL}
CLOUDFLARE_R2_ACCOUNT_ID=${R2_ACCOUNT_ID}
CLOUDFLARE_R2_ACCESS_KEY_ID=${R2_ACCESS_KEY}
CLOUDFLARE_R2_SECRET_ACCESS_KEY=${R2_SECRET_KEY}
CLOUDFLARE_R2_BUCKET_NAME=${R2_BUCKET}
CLOUDFLARE_R2_PUBLIC_URL=${R2_PUBLIC_URL}

# LeadHunter Pro Integration
PARSER_INTERNAL_URL=http://leadhunter:8000
INTERNAL_API_SECRET=${INTERNAL_API_SECRET}
PARSER_PUBLIC_URL=https://leads.${DOMAIN_NAME}
EOF
    )
    chmod 600 "$ENV_FILE"
    log_success "Файл конфигурации бэкенда создан: $ENV_FILE"

    # Создаем/синхронизируем конфигурацию парсера
    mkdir -p "${ROOT_DIR}/apps/parser"
    (
        umask 077
        cat > "$PARSER_ENV_FILE" <<EOF
# ====================================================================
# LeadHunter Pro & Yandex Maps Parser Configuration (.env)
# Generated on: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
# ====================================================================

TELEGRAM_BOT_TOKEN=${PARSER_BOT_TOKEN:-8867814063:AAHzkxMrybGKQpOECSu-ZPLo4wJNX_0N1Vg}
TELEGRAM_API_SERVER=${TELEGRAM_PROXY_URL:-https://jolly-haze-c6cf.eprof6682-3e3.workers.dev}
# TELEGRAM_PROXY=

OUTREACH_BOT_TOKEN=${OUTREACH_BOT_TOKEN:-}
ADMIN_TELEGRAM_IDS="1878543896,${TELEGRAM_CHAT_ID}"
MANAGER_TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID}
DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY:-}

HOST=0.0.0.0
PORT=8000

SECRET_KEY=${SECRET_KEY}
INTERNAL_API_SECRET=${INTERNAL_API_SECRET}
PARSER_PUBLIC_URL=https://leads.${DOMAIN_NAME}
COOKIE_SECURE=false

INITIAL_ADMIN_EMAIL=admin@lead.pro
INITIAL_ADMIN_PASSWORD=AdminPass123!_ChangeMe
EOF
    )
    chmod 600 "$PARSER_ENV_FILE"
    log_success "Файл конфигурации парсера синхронизирован: $PARSER_ENV_FILE"
}


load_env() {
    if [ -f "$ENV_FILE" ]; then
        set -a
        source "$ENV_FILE"
        set +a
    else
        log_error "Файл $ENV_FILE не найден!"
        exit 1
    fi
}

setup_os_ubuntu() {
    log_step "Блок 1: Подготовка и безопасность ОС Ubuntu"
    export DEBIAN_FRONTEND=noninteractive

    if [ -f /etc/needrestart/needrestart.conf ]; then
        sed -i "s/#\$nrconf{restart} = 'i';/\$nrconf{restart} = 'a';/g" /etc/needrestart/needrestart.conf 2>/dev/null || true
    fi

    log_info "Обновление системных пакетов..."
    apt-get update -y -q
    apt-get upgrade -y -q

    # Настройка Swap (2 ГБ)
    if ! swapon --show | grep -q "swap"; then
        log_info "Выделение Swap-файла 2 ГБ для стабильности OOM..."
        fallocate -l 2G /swapfile 2>/dev/null || dd if=/dev/zero of=/swapfile bs=1M count=2048
        chmod 600 /swapfile
        mkswap /swapfile >/dev/null
        swapon /swapfile
        grep -q '/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
        sysctl -w vm.swappiness=10 >/dev/null
        echo 'vm.swappiness=10' > /etc/sysctl.d/99-swap.conf
        log_success "Swap 2 ГБ подключен."
    fi

    # Защита от PMTUD Black Hole и зависаний TCP при передаче файлов >16KB через Cloudflare
    sysctl -w net.ipv4.tcp_mtu_probing=1 >/dev/null 2>&1 || true
    echo 'net.ipv4.tcp_mtu_probing=1' > /etc/sysctl.d/99-mtu.conf 2>/dev/null || true

    log_info "Установка базовых утилит (curl, git, ufw, fail2ban, jq, openssl, cron)..."
    apt-get install -y -q --no-install-recommends \
        curl git ufw fail2ban jq openssl ca-certificates gnupg lsb-release cron

    # Настройка брандмауэра
    ufw default deny incoming
    ufw default allow outgoing
    ufw allow 22/tcp comment 'SSH'
    ufw allow 80/tcp comment 'HTTP'
    ufw allow 443/tcp comment 'HTTPS'
    ufw --force enable
    log_success "UFW настроен (порты 22, 80, 443 открыты, БД изолированы)."

    systemctl enable --now fail2ban >/dev/null 2>&1 || true
    systemctl enable --now cron >/dev/null 2>&1 || true
}

setup_docker() {
    log_step "Блок 2: Настройка Docker Engine и Docker Daemon"
    if ! command -v docker >/dev/null 2>&1; then
        log_info "Установка Docker через официальный скрипт..."
        curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
        sh /tmp/get-docker.sh
        rm -f /tmp/get-docker.sh
    fi

    # Ротация логов Docker, чтобы не переполнялся NVMe диск
    mkdir -p /etc/docker
    if [ ! -f /etc/docker/daemon.json ]; then
        log_info "Настройка автоматической ротации логов Docker (max-size 10m)..."
        cat > /etc/docker/daemon.json <<'EOF'
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
EOF
    fi

    systemctl enable --now docker
    systemctl restart docker
    log_success "Docker Engine настроен."
}

build_frontend() {
    log_step "Блок 3: Сборка фронтенда в контейнере Node.js"
    mkdir -p "${FRONTEND_DIST}"

    if [ -f "${FRONTEND_DIR}/package.json" ]; then
        log_info "Запуск сборки в node:22-alpine..."
        BUILD_CMD="npm install --include=optional && npm run build"
        if [ -f "${FRONTEND_DIR}/package-lock.json" ]; then
            BUILD_CMD="npm ci && npm run build"
        fi
        docker run --rm \
            -v "${FRONTEND_DIR}":/app \
            -w /app \
            -e VITE_API_URL="https://${DOMAIN_NAME}" \
            node:22-alpine \
            sh -c "$BUILD_CMD"
        log_success "Фронтенд собран в apps/frontend/dist!"
    else
        log_warn "Фронтенд еще не готов. Создана страница-заглушка."
        if [ -f "${SCRIPT_DIR}/placeholder.html" ]; then
            cp "${SCRIPT_DIR}/placeholder.html" "${FRONTEND_DIST}/index.html"
        else
            echo "<!DOCTYPE html><html><body style='font-family:sans-serif;text-align:center;padding:50px'><h1>CASTLEWEB System Active</h1><p>Frontend is currently updating.</p></body></html>" > "${FRONTEND_DIST}/index.html"
        fi
    fi
}

setup_nginx_config() {
    log_step "Блок 4: Конфигурация Nginx и диапазонов Cloudflare"
    mkdir -p "${NGINX_DIR}/conf.d"

    # Cloudflare Real IP (с защитой от сбоя сети)
    CLOUDFLARE_CONF="${NGINX_DIR}/conf.d/cloudflare_real_ip.conf"
    CF_IPS_V4=$(curl -sf https://www.cloudflare.com/ips-v4 || true)
    CF_IPS_V6=$(curl -sf https://www.cloudflare.com/ips-v6 || true)

    if [ -n "$CF_IPS_V4" ]; then
        {
            echo "# Cloudflare Real IP Range"
            for ip in $CF_IPS_V4 $CF_IPS_V6; do
                echo "set_real_ip_from $ip;"
            done
            echo "real_ip_header CF-Connecting-IP;"
        } > "${CLOUDFLARE_CONF}"
        log_success "Cloudflare Real IP адреса успешно синхронизированы."
    else
        log_warn "Сеть Cloudflare недоступна, применен резервный заголовок."
        echo "real_ip_header X-Forwarded-For;" > "${CLOUDFLARE_CONF}"
    fi

    DEFAULT_TEMPLATE="${NGINX_DIR}/conf.d/default.conf.template"
    DEFAULT_CONF="${NGINX_DIR}/conf.d/default.conf"
    if [ -f "$DEFAULT_TEMPLATE" ]; then
        sed "s|__DOMAIN__|${DOMAIN_NAME}|g" "$DEFAULT_TEMPLATE" > "$DEFAULT_CONF"
        log_success "Конфигурация Nginx сгенерирована из шаблона для ${DOMAIN_NAME}."
    elif [ -f "$DEFAULT_CONF" ]; then
        sed -i "s|/etc/letsencrypt/live/[^/]*/|/etc/letsencrypt/live/${DOMAIN_NAME}/|g" "$DEFAULT_CONF" || true
        sed -i "s|__DOMAIN__|${DOMAIN_NAME}|g" "$DEFAULT_CONF" || true
    fi
}

setup_ssl_and_cron() {
    log_step "Блок 5: Настройка SSL и автопродления"
    CERT_DIR="/etc/letsencrypt/live/${DOMAIN_NAME}"
    mkdir -p "${CERT_DIR}"

    if [ ! -f "${CERT_DIR}/fullchain.pem" ]; then
        log_info "Создание временного самоподписанного сертификата для первого старта..."
        openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
            -keyout "${CERT_DIR}/privkey.pem" \
            -out "${CERT_DIR}/fullchain.pem" \
            -subj "/CN=${DOMAIN_NAME}" >/dev/null 2>&1

        docker compose -f "$DOCKER_COMPOSE_FILE" up -d nginx

        log_info "Запрос Let's Encrypt через Certbot..."
        # Удаляем самоподписанные заглушки перед запросом, чтобы Certbot не создал директорию ${DOMAIN_NAME}-0001
        rm -rf "${CERT_DIR}"

        docker compose -f "$DOCKER_COMPOSE_FILE" run --rm certbot certonly \
            --webroot -w /var/www/certbot \
            --cert-name "${DOMAIN_NAME}" \
            -d "${DOMAIN_NAME}" \
            -d "leads.${DOMAIN_NAME}" \
            --email "${ADMIN_EMAIL}" \
            --agree-tos --no-eff-email --keep-until-expiring || \
        docker compose -f "$DOCKER_COMPOSE_FILE" run --rm certbot certonly \
            --webroot -w /var/www/certbot \
            --cert-name "${DOMAIN_NAME}" \
            -d "${DOMAIN_NAME}" \
            --email "${ADMIN_EMAIL}" \
            --agree-tos --no-eff-email --keep-until-expiring || {
                log_warn "DNS еще не обновился. Восстанавливаем временный сертификат (Cloudflare SSL активен)..."
                mkdir -p "${CERT_DIR}"
                openssl req -x509 -nodes -newkey rsa:2048 -days 30 \
                    -keyout "${CERT_DIR}/privkey.pem" \
                    -out "${CERT_DIR}/fullchain.pem" \
                    -subj "/CN=${DOMAIN_NAME}" >/dev/null 2>&1
            }
        docker compose -f "$DOCKER_COMPOSE_FILE" exec -T nginx nginx -s reload >/dev/null 2>&1 || true
    fi

    # Автоматический Cron для продления Let's Encrypt каждые 12 часов
    CRON_CMD="0 */12 * * * docker compose -f ${DOCKER_COMPOSE_FILE} run --rm certbot renew --quiet && docker compose -f ${DOCKER_COMPOSE_FILE} exec -T nginx nginx -s reload"
    (crontab -l 2>/dev/null | grep -v "certbot renew" ; echo "$CRON_CMD") | crontab -
    log_success "Автопродление SSL добавлено в системный crontab."

    # Dead Man's Switch — health check every 5 minutes, alert to Telegram on failure
    if [ -n "$TELEGRAM_BOT_TOKEN" ] && [ "$TELEGRAM_BOT_TOKEN" != "your_bot_token_here" ]; then
        HEALTH_SCRIPT="${ROOT_DIR}/scripts/healthcheck.sh"
        cat > "$HEALTH_SCRIPT" <<'HEALTHEOF'
#!/bin/bash
FAIL_FILE="/tmp/castleweb_health_fails"
MAX_FAILS=3
HEALTH_URL="http://127.0.0.1:8000/api/v1/health"

if curl -sf --max-time 5 "$HEALTH_URL" > /dev/null 2>&1; then
    rm -f "$FAIL_FILE"
    exit 0
fi

CURRENT=$(cat "$FAIL_FILE" 2>/dev/null || echo 0)
CURRENT=$((CURRENT + 1))
echo "$CURRENT" > "$FAIL_FILE"

if [ "$CURRENT" -ge "$MAX_FAILS" ]; then
    source __ENV_FILE__
    TG_URL="${TELEGRAM_PROXY_URL:-https://api.telegram.org}/bot${TELEGRAM_BOT_TOKEN}/sendMessage"
    MSG="🔴 <b>CASTLEWEB DOWN</b>%0A━━━━━━━━━━━━━━━━━━━━%0AHealth check failed ${CURRENT}x подряд%0AВремя: $(date '+%Y-%m-%d %H:%M:%S')%0A%0AПроверьте: docker compose logs backend"
    curl -s "$TG_URL" -d chat_id="${TELEGRAM_CHAT_ID}" -d text="$MSG" -d parse_mode=HTML > /dev/null 2>&1
    echo 0 > "$FAIL_FILE"
fi
HEALTHEOF
        sed -i "s|__ENV_FILE__|${ENV_FILE}|g" "$HEALTH_SCRIPT"
        chmod +x "$HEALTH_SCRIPT"

        HEALTH_CRON="*/5 * * * * ${HEALTH_SCRIPT}"
        (crontab -l 2>/dev/null | grep -v "healthcheck.sh" ; echo "$HEALTH_CRON") | crontab -
        log_success "Dead Man's Switch: мониторинг здоровья каждые 5 минут → алерт в Telegram."

        # Установка CASTLEWEB Sentinel (полный мониторинг хоста, памяти, диска, контейнеров и дайджеста)
        MONITOR_SCRIPT="${ROOT_DIR}/scripts/server_monitor.sh"
        if [ -f "$MONITOR_SCRIPT" ]; then
            chmod +x "$MONITOR_SCRIPT"
            bash "$MONITOR_SCRIPT" --install >/dev/null 2>&1 || true
            log_success "CASTLEWEB Sentinel: полный мониторинг сервера установлен (проверки каждые 3 мин + дайджест в TG)."
        fi
    fi
}

launch_and_post_install() {
    log_step "Блок 6: Запуск контейнеров, миграций и регистрация Webhook"
    docker compose -f "$DOCKER_COMPOSE_FILE" up -d --build --remove-orphans

    # Синхронизация пароля PostgreSQL с .env на случай повторного деплоя с новым паролем
    if [ -n "$POSTGRES_PASSWORD" ]; then
        docker compose -f "$DOCKER_COMPOSE_FILE" exec -T postgres psql -U "${POSTGRES_USER:-castleweb_user}" -d "${POSTGRES_DB:-castleweb_db}" -c "ALTER USER \"${POSTGRES_USER:-castleweb_user}\" WITH PASSWORD '${POSTGRES_PASSWORD}';" >/dev/null 2>&1 || true
        docker compose -f "$DOCKER_COMPOSE_FILE" restart backend >/dev/null 2>&1 || true
    fi

    log_info "Ожидание готовности FastAPI (до 30 сек)..."
    BACKEND_HEALTHY=false
    for _ in $(seq 1 30); do
        if curl -sf http://127.0.0.1:8000/api/v1/health >/dev/null 2>&1 || \
           docker compose -f "$DOCKER_COMPOSE_FILE" exec -T backend curl -sf http://localhost:8000/api/v1/health >/dev/null 2>&1; then
            BACKEND_HEALTHY=true
            break
        fi
        sleep 1
    done

    if [ "$BACKEND_HEALTHY" = true ]; then
        log_success "Бэкенд успешно отвечает на /api/v1/health!"
    else
        log_warn "Бэкенд еще запускается. Проверьте: docker compose -f $DOCKER_COMPOSE_FILE logs backend"
    fi

    # Проверка статуса LeadHunter Pro
    log_info "Ожидание готовности парсера LeadHunter..."
    LEADHUNTER_HEALTHY=false
    for _ in $(seq 1 15); do
        if docker compose -f "$DOCKER_COMPOSE_FILE" exec -T leadhunter python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" >/dev/null 2>&1; then
            LEADHUNTER_HEALTHY=true
            break
        fi
        sleep 1
    done
    if [ "$LEADHUNTER_HEALTHY" = true ]; then
        log_success "Парсер LeadHunter успешно запущен и отвечает на http://127.0.0.1:8080!"
    else
        log_info "Контейнер LeadHunter инициализируется. Статус: docker compose logs leadhunter"
    fi


    # 1. Автоматический накат миграций Alembic
    log_info "Применение миграций базы данных (Alembic)..."
    docker compose -f "$DOCKER_COMPOSE_FILE" exec -T backend alembic upgrade head || log_warn "Alembic завершил выполнение с предупреждением (проверьте таблицы)."

    # Перезапуск Nginx для сброса DNS upstream кэша и подключения к новым IP контейнеров
    log_info "Перезапуск шлюза Nginx для актуализации сетевых маршрутов..."
    docker compose -f "$DOCKER_COMPOSE_FILE" restart nginx

    # 2. Автоматическая привязка Telegram Webhook
    if [ -n "$TELEGRAM_BOT_TOKEN" ] && [ "$TELEGRAM_BOT_TOKEN" != "your_bot_token_here" ]; then
        log_info "Активация Telegram Webhook..."
        WEBHOOK_URL="https://${DOMAIN_NAME}/api/v1/telegram/webhook"
        TG_BASE="${TELEGRAM_PROXY_URL%/}"
        if [[ "$TG_BASE" == */bot ]]; then
            TG_ENDPOINT="${TG_BASE}${TELEGRAM_BOT_TOKEN}/setWebhook"
        else
            TG_ENDPOINT="${TG_BASE}/bot${TELEGRAM_BOT_TOKEN}/setWebhook"
        fi
        TG_PAYLOAD="{\"url\":\"${WEBHOOK_URL}\",\"allowed_updates\":[\"message\",\"callback_query\"]"
        if [ -n "$TELEGRAM_WEBHOOK_SECRET" ]; then
            TG_PAYLOAD="${TG_PAYLOAD},\"secret_token\":\"${TELEGRAM_WEBHOOK_SECRET}\""
        fi
        TG_PAYLOAD="${TG_PAYLOAD}}"
        TG_RES=$(curl -s -X POST "${TG_ENDPOINT}" -H "Content-Type: application/json" -d "${TG_PAYLOAD}" || echo "")
        if echo "$TG_RES" | grep -q '"ok":true'; then
            log_success "Telegram Webhook успешно привязан: ${WEBHOOK_URL}"
        else
            log_warn "Ответ Telegram API: ${TG_RES}"
        fi

    fi

    echo -e "\n${GREEN}${BOLD}=================================================================${NC}"
    echo -e "${GREEN}${BOLD}     🎉 ПРОЕКТ CASTLEWEB ПОЛНОСТЬЮ РАЗВЕРНУТ И ЗАПУЩЕН!         ${NC}"
    echo -e "${GREEN}${BOLD}=================================================================${NC}"
    echo -e "  • Сайт:           https://${DOMAIN_NAME}/"
    echo -e "  • Документация:   https://${DOMAIN_NAME}/docs"
    echo -e "  • Статус API:     https://${DOMAIN_NAME}/api/v1/status"
    echo -e "  • LeadHunter:     https://leads.${DOMAIN_NAME}/ (резерв: https://${DOMAIN_NAME}/parser/)"
    echo -e "                    или SSH: ssh -L 8080:localhost:8080 root@<SERVER_IP>"
    echo -e "  • Бэкапы БД:     docker volume inspect castleweb_pg_backups"
    echo -e "=================================================================\n"
}

main() {
    MODE="${1:---full}"
    check_root

    case "$MODE" in
        --full)
            log_banner
            setup_admin_env
            load_env
            setup_os_ubuntu
            setup_docker
            build_frontend
            setup_nginx_config
            setup_ssl_and_cron
            launch_and_post_install
            ;;
        --frontend-only)
            log_banner
            load_env
            build_frontend
            docker compose -f "$DOCKER_COMPOSE_FILE" exec -T nginx nginx -s reload || true
            log_success "Фронтенд обновлен!"
            ;;
        --backend-only)
            log_banner
            load_env
            docker compose -f "$DOCKER_COMPOSE_FILE" build backend
            docker compose -f "$DOCKER_COMPOSE_FILE" up -d --no-deps backend
            docker compose -f "$DOCKER_COMPOSE_FILE" restart nginx
            docker compose -f "$DOCKER_COMPOSE_FILE" exec -T backend alembic upgrade head || true
            docker compose -f "$DOCKER_COMPOSE_FILE" exec -u 0 -T backend chmod -R 777 /app/uploads /tmp/uploads 2>/dev/null || true
            curl -sf -X POST http://127.0.0.1:8000/api/v1/telegram/setup-webhook >/dev/null 2>&1 || true
            curl -sf -X POST http://127.0.0.1:8000/api/v1/telegram/test >/dev/null 2>&1 || true
            log_success "Бэкенд обновлен, Nginx синхронизирован и Telegram Webhook активирован!"
            ;;
        --parser-only)
            log_banner
            load_env
            docker compose -f "$DOCKER_COMPOSE_FILE" build leadhunter
            docker compose -f "$DOCKER_COMPOSE_FILE" up -d --no-deps leadhunter
            docker compose -f "$DOCKER_COMPOSE_FILE" restart nginx
            log_success "Парсер LeadHunter Pro обновлен и Nginx синхронизирован!"
            ;;
        --ssl)
            log_banner
            load_env
            log_step "Выпуск / Обновление SSL сертификата Let's Encrypt для ${DOMAIN_NAME} и leads.${DOMAIN_NAME}..."
            docker run --rm \
                -v /etc/letsencrypt:/etc/letsencrypt \
                -v /var/www/certbot:/var/www/certbot \
                certbot/certbot certonly \
                --webroot -w /var/www/certbot \
                --cert-name "${DOMAIN_NAME}" \
                -d "${DOMAIN_NAME}" \
                -d "www.${DOMAIN_NAME}" \
                -d "leads.${DOMAIN_NAME}" \
                --email "${ADMIN_EMAIL}" \
                --agree-tos --no-eff-email \
                --force-renewal
            docker compose -f "$DOCKER_COMPOSE_FILE" exec -T nginx nginx -s reload
            log_success "SSL сертификат успешно обновлен и Nginx перезапущен!"
            ;;
        --migrate)
            load_env
            docker compose -f "$DOCKER_COMPOSE_FILE" exec -T backend alembic upgrade head
            ;;
        --status)
            log_banner
            docker compose -f "$DOCKER_COMPOSE_FILE" ps
            curl -s http://localhost:8000/api/v1/status | jq . 2>/dev/null || true
            ;;
        *)
            echo "Использование: $0 [--full | --frontend-only | --backend-only | --parser-only | --ssl | --migrate | --status]"
            ;;
    esac
}

main "$@"
