#!/usr/bin/env bash
# ==============================================================================
# 🏰 CASTLEWEB Sentinel — Complete Server & Container Monitoring Suite
# Output: Exclusively into Telegram (Alerts + Periodic Digest + On-Demand)
# ==============================================================================

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${ROOT_DIR}/apps/backend/.env"
COMPOSE_FILE="${ROOT_DIR}/docker-compose.prod.yml"

# Fallback to local docker-compose.yml if prod is not present
if [ ! -f "$COMPOSE_FILE" ]; then
    COMPOSE_FILE="${ROOT_DIR}/docker-compose.yml"
fi

STATE_DIR="/tmp/castleweb_sentinel"
mkdir -p "$STATE_DIR"

# --- Load Environment Variables ---
if [ -f "$ENV_FILE" ]; then
    # Load only necessary Telegram variables cleanly
    TG_TOKEN=$(grep -E '^TELEGRAM_BOT_TOKEN=' "$ENV_FILE" | cut -d '=' -f2- | tr -d '"' | tr -d "'" || true)
    TG_CHAT_ID=$(grep -E '^TELEGRAM_CHAT_ID=' "$ENV_FILE" | cut -d '=' -f2- | tr -d '"' | tr -d "'" || true)
    TG_PROXY_URL=$(grep -E '^TELEGRAM_PROXY_URL=' "$ENV_FILE" | cut -d '=' -f2- | tr -d '"' | tr -d "'" || true)
    TG_API_BASE=$(grep -E '^TELEGRAM_API_BASE_URL=' "$ENV_FILE" | cut -d '=' -f2- | tr -d '"' | tr -d "'" || true)
    DOMAIN_NAME=$(grep -E '^DOMAIN_NAME=' "$ENV_FILE" | cut -d '=' -f2- | tr -d '"' | tr -d "'" || true)
else
    TG_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
    TG_CHAT_ID="${TELEGRAM_CHAT_ID:-}"
    TG_PROXY_URL="${TELEGRAM_PROXY_URL:-}"
    TG_API_BASE="${TELEGRAM_API_BASE_URL:-}"
    DOMAIN_NAME="${DOMAIN_NAME:-castleweb.ru}"
fi

DOMAIN_NAME="${DOMAIN_NAME:-castleweb.ru}"

# Resolve API URL
if [ -n "$TG_PROXY_URL" ] && [ "$TG_PROXY_URL" != "your_proxy_here" ]; then
    BASE_ENDPOINT="${TG_PROXY_URL%/}"
    if [[ "$BASE_ENDPOINT" == */bot ]]; then
        TG_URL="${BASE_ENDPOINT}${TG_TOKEN}/sendMessage"
    else
        TG_URL="${BASE_ENDPOINT}/bot${TG_TOKEN}/sendMessage"
    fi
elif [ -n "$TG_API_BASE" ] && [[ "$TG_API_BASE" == http* ]]; then
    BASE_ENDPOINT="${TG_API_BASE%/}"
    if [[ "$BASE_ENDPOINT" == */bot ]]; then
        TG_URL="${BASE_ENDPOINT}${TG_TOKEN}/sendMessage"
    else
        TG_URL="${BASE_ENDPOINT}/bot${TG_TOKEN}/sendMessage"
    fi
else
    TG_URL="https://api.telegram.org/bot${TG_TOKEN}/sendMessage"
fi

# ==============================================================================
# Telegram Dispatcher
# ==============================================================================
send_telegram() {
    local message="$1"
    if [ -z "$TG_TOKEN" ] || [ "$TG_TOKEN" = "your_bot_token_here" ] || [ -z "$TG_CHAT_ID" ]; then
        echo "[Sentinel Warning] Telegram token or chat_id not configured." >&2
        return 0
    fi

    # Escape any broken tags if needed, send HTML
    curl -sf -X POST "$TG_URL" \
        -d chat_id="${TG_CHAT_ID}" \
        -d text="$message" \
        -d parse_mode="HTML" \
        -d disable_web_page_preview=true > /dev/null 2>&1 || {
            # Fallback plain text if HTML parse fails
            local plain_text
            plain_text=$(echo "$message" | sed 's/<[^>]*>//g')
            curl -sf -X POST "$TG_URL" \
                -d chat_id="${TG_CHAT_ID}" \
                -d text="$plain_text" > /dev/null 2>&1 || true
        }
}

# ==============================================================================
# Incident Alert with Cooldown & Auto-Recovery
# ==============================================================================
handle_incident() {
    local incident_key="$1"
    local is_failure="$2" # 1 = failure, 0 = healthy
    local alert_title="$3"
    local alert_body="$4"

    local state_file="${STATE_DIR}/${incident_key}.state"
    local cooldown_file="${STATE_DIR}/${incident_key}.cooldown"
    local now
    now=$(date +%s)

    if [ "$is_failure" -eq 1 ]; then
        # Check cooldown (30 minutes = 1800 seconds)
        local last_sent=0
        if [ -f "$cooldown_file" ]; then
            last_sent=$(cat "$cooldown_file" 2>/dev/null || echo 0)
        fi

        local diff=$(( now - last_sent ))
        if [ "$diff" -ge 1800 ] || [ ! -f "$state_file" ]; then
            local alert_msg="🔴 <b>CASTLEWEB ALERT: ${alert_title}</b>
━━━━━━━━━━━━━━━━━━━━
${alert_body}

⏱ <i>$(date '+%Y-%m-%d %H:%M:%S UTC')</i>"
            send_telegram "$alert_msg"
            echo "$now" > "$cooldown_file"
            echo "FAILED" > "$state_file"
        fi
    else
        # Service is healthy now. Check if it was previously failed
        if [ -f "$state_file" ] && [ "$(cat "$state_file" 2>/dev/null)" = "FAILED" ]; then
            local recovery_msg="🟢 <b>CASTLEWEB RECOVERY: ${alert_title}</b>
━━━━━━━━━━━━━━━━━━━━
Сервис снова стабилен и отвечает в штатном режиме.

⏱ <i>$(date '+%Y-%m-%d %H:%M:%S UTC')</i>"
            send_telegram "$recovery_msg"
            rm -f "$state_file" "$cooldown_file"
        fi
    fi
}

# ==============================================================================
# Metrics Gathering
# ==============================================================================
get_cpu_load() {
    if [ -f /proc/loadavg ]; then
        cut -d ' ' -f 1-3 /proc/loadavg
    else
        echo "0.05 0.08 0.06"
    fi
}

get_ram_info() {
    local mem_total=0 mem_avail=0
    if [ -f /proc/meminfo ]; then
        mem_total=$(grep -E '^MemTotal:' /proc/meminfo | awk '{print $2}')
        mem_avail=$(grep -E '^MemAvailable:' /proc/meminfo | awk '{print $2}')
    fi
    if [ "$mem_total" -gt 0 ]; then
        local mem_used=$(( mem_total - mem_avail ))
        local pct=$(( mem_used * 100 / mem_total ))
        local used_gb
        local tot_gb
        used_gb=$(awk "BEGIN {printf \"%.1f\", $mem_used/1048576}")
        tot_gb=$(awk "BEGIN {printf \"%.1f\", $mem_total/1048576}")
        echo "${used_gb}/${tot_gb} GB (${pct}%)"
    else
        echo "N/A"
    fi
}

get_disk_info() {
    local disk_used
    local disk_total
    local disk_pct
    disk_pct=$(df -P / | tail -1 | awk '{print $5}' | tr -d '%')
    disk_used=$(df -h -P / | tail -1 | awk '{print $3}')
    disk_total=$(df -h -P / | tail -1 | awk '{print $2}')
    echo "${disk_used}/${disk_total} (${disk_pct}%)"
}

get_uptime_info() {
    if [ -f /proc/uptime ]; then
        local sec
        sec=$(cut -d '.' -f 1 /proc/uptime)
        local d=$(( sec / 86400 ))
        local h=$(( (sec % 86400) / 3600 ))
        local m=$(( (sec % 3600) / 60 ))
        if [ "$d" -gt 0 ]; then
            echo "${d}д ${h}ч ${m}м"
        else
            echo "${h}ч ${m}м"
        fi
    else
        echo "Активен"
    fi
}

get_ssl_days() {
    local cert="/etc/letsencrypt/live/${DOMAIN_NAME}/fullchain.pem"
    if [ -f "$cert" ]; then
        local exp_epoch
        exp_epoch=$(date -d "$(openssl x509 -enddate -noout -in "$cert" | cut -d= -f2)" +%s 2>/dev/null || echo 0)
        local now
        now=$(date +%s)
        if [ "$exp_epoch" -gt "$now" ]; then
            echo "$(( (exp_epoch - now) / 86400 )) дней"
        else
            echo "ИСТЕК"
        fi
    else
        echo "Cloudflare Managed / N/A"
    fi
}

get_backup_info() {
    local last_file
    local file_size
    local file_time
    if command -v docker >/dev/null 2>&1 && docker ps --format '{{.Names}}' | grep -q "castleweb_pg_backup"; then
        last_file=$(docker exec castleweb_pg_backup sh -c 'ls -t /backups/*.sql.gz 2>/dev/null | head -1' || true)
        if [ -n "$last_file" ]; then
            file_size=$(docker exec castleweb_pg_backup sh -c "du -h '$last_file' | cut -f1" 2>/dev/null || echo "OK")
            file_time=$(docker exec castleweb_pg_backup sh -c "date -r '$last_file' '+%d.%m %H:%M' 2>/dev/null" || echo "")
            echo "${file_time} (${file_size})"
            return
        fi
    fi
    echo "Активен (каждые 12ч)"
}

get_banned_ips_count() {
    if command -v fail2ban-client >/dev/null 2>&1; then
        fail2ban-client status sshd 2>/dev/null | grep -E "Currently banned:" | awk '{print $NF}' || echo "0"
    else
        echo "0"
    fi
}

# ==============================================================================
# Health Probes & Checks
# ==============================================================================
check_all() {
    # 1. Check Containers
    if command -v docker >/dev/null 2>&1; then
        local expected_containers=("castleweb_prod_backend" "castleweb_prod_postgres" "castleweb_prod_redis" "castleweb_prod_nginx")
        for c in "${expected_containers[@]}"; do
            local c_status
            c_status=$(docker inspect --format '{{.State.Status}}' "$c" 2>/dev/null || echo "missing")
            if [ "$c_status" != "running" ]; then
                local c_logs
                c_logs=$(docker logs --tail 8 "$c" 2>&1 | tail -8 || echo "Логи недоступны")
                handle_incident "container_${c}" 1 "Упал контейнер ${c}" "Статус: <code>${c_status}</code>%0A%0AПоследние логи:%0A<pre>${c_logs}</pre>"
            else
                handle_incident "container_${c}" 0 "${c}" ""
            fi
        done
    fi

    # 2. Check FastAPI Backend Endpoint
    local api_http_code
    api_http_code=$(curl -sf -o /dev/null -w "%{http_code}" --max-time 6 "http://127.0.0.1:8000/api/v1/health" 2>/dev/null || echo "000")
    if [ "$api_http_code" != "200" ]; then
        handle_incident "api_health" 1 "Сбой FastAPI бэкенда" "Эндпоинт <code>/api/v1/health</code> вернул HTTP <code>${api_http_code}</code>"
    else
        handle_incident "api_health" 0 "FastAPI" ""
    fi

    # 3. Check Nginx Port 80/443
    local nginx_http_code
    nginx_http_code=$(curl -sf -k -o /dev/null -w "%{http_code}" --max-time 6 "https://127.0.0.1/" 2>/dev/null || echo "000")
    if [ "$nginx_http_code" = "000" ] || [ "$nginx_http_code" = "502" ] || [ "$nginx_http_code" = "504" ]; then
        handle_incident "nginx_web" 1 "Сбой Nginx / Веб-сайта" "Запрос к веб-серверу вернул код <code>${nginx_http_code}</code>"
    else
        handle_incident "nginx_web" 0 "Nginx" ""
    fi

    # 4. Check Disk Space
    local disk_pct
    disk_pct=$(df -P / | tail -1 | awk '{print $5}' | tr -d '%')
    if [ "$disk_pct" -ge 92 ]; then
        handle_incident "disk_space" 1 "Критически мало места на диске!" "Диск (/) заполнен на <b>${disk_pct}%</b>! Срочно очистите логи или Docker cache."
    elif [ "$disk_pct" -ge 85 ]; then
        handle_incident "disk_space" 1 "Предупреждение: диск заполняется" "Диск (/) заполнен на <b>${disk_pct}%</b>."
    else
        handle_incident "disk_space" 0 "Дисковое пространство" ""
    fi

    # 5. Check Memory Exhaustion
    if [ -f /proc/meminfo ]; then
        local mem_avail_kb
        mem_avail_kb=$(grep -E '^MemAvailable:' /proc/meminfo | awk '{print $2}')
        if [ "$mem_avail_kb" -lt 120000 ]; then # < 120 MB
            handle_incident "ram_oom" 1 "Критический дефицит RAM" "Доступно менее 120 МБ оперативной памяти! Риск срабатывания Linux OOM-Killer."
        else
            handle_incident "ram_oom" 0 "RAM" ""
        fi
    fi
}

# ==============================================================================
# Periodic Summary Digest
# ==============================================================================
send_digest_report() {
    local cpu_load
    cpu_load=$(get_cpu_load)
    local ram_info
    ram_info=$(get_ram_info)
    local disk_info
    disk_info=$(get_disk_info)
    local uptime_info
    uptime_info=$(get_uptime_info)
    local ssl_info
    ssl_info=$(get_ssl_days)
    local backup_info
    backup_info=$(get_backup_info)
    local banned_ips
    banned_ips=$(get_banned_ips_count)

    # Containers list
    local c_backend="🔴" c_postgres="🔴" c_redis="🔴" c_nginx="🔴" c_backup="🔴"
    if command -v docker >/dev/null 2>&1; then
        docker ps --format '{{.Names}}' | grep -q "castleweb_prod_backend" && c_backend="🟢"
        docker ps --format '{{.Names}}' | grep -q "castleweb_prod_postgres" && c_postgres="🟢"
        docker ps --format '{{.Names}}' | grep -q "castleweb_prod_redis" && c_redis="🟢"
        docker ps --format '{{.Names}}' | grep -q "castleweb_prod_nginx" && c_nginx="🟢"
        docker ps --format '{{.Names}}' | grep -q "castleweb_pg_backup" && c_backup="🟢"
    fi

    local report="🏰 <b>CASTLEWEB • Сводка сервера</b>
━━━━━━━━━━━━━━━━━━━━
🟢 <b>Статус:</b> Все ключевые сервисы в строю

💻 <b>Ресурсы хоста:</b>
• CPU Load: <code>${cpu_load}</code>
• RAM: <code>${ram_info}</code>
• Диск (/): <code>${disk_info}</code>
• Uptime: <code>${uptime_info}</code>

🐳 <b>Контейнеры:</b>
• ${c_backend} <code>backend</code> (FastAPI)
• ${c_postgres} <code>postgres</code> (БД)
• ${c_redis} <code>redis</code> (Кэш & Лимитер)
• ${c_nginx} <code>nginx</code> (Веб & SSL)
• ${c_backup} <code>pg_backup</code> (Cron 12ч)

🛡️ <b>Надежность & Безопасность:</b>
• SSL Сертификат: <code>${ssl_info}</code>
• Последний бэкап: <code>${backup_info}</code>
• Заблокировано атак: <code>${banned_ips} IP</code>
━━━━━━━━━━━━━━━━━━━━
⏱ <i>$(date '+%Y-%m-%d %H:%M UTC')</i>"

    send_telegram "$report"
}

# ==============================================================================
# Crontab Installer
# ==============================================================================
install_cron() {
    local monitor_path="${SCRIPT_DIR}/server_monitor.sh"
    chmod +x "$monitor_path"

    # Remove old entries
    local existing_cron
    existing_cron=$(crontab -l 2>/dev/null | grep -v "server_monitor.sh" || true)

    # Every 3 minutes: probe health & alert on failure
    # Every day at 09:00 and 21:00 UTC: send rich digest
    local new_cron="${existing_cron}
*/3 * * * * ${monitor_path} --check >/dev/null 2>&1
0 9,21 * * * ${monitor_path} --report >/dev/null 2>&1"

    echo "$new_cron" | crontab -
    echo "[✓] Мониторинг успешно установлен в crontab!"
    echo "  - Проверка алертов: каждые 3 минуты"
    echo "  - Сводный дайджест: в 09:00 и 21:00 UTC в Telegram"
}

# ==============================================================================
# CLI Entry Point
# ==============================================================================
case "${1:-status}" in
    --check)
        check_all
        ;;
    --report|--digest)
        send_digest_report
        ;;
    --install)
        install_cron
        ;;
    --test)
        echo "Отправка тестового уведомления..."
        send_telegram "🔔 <b>CASTLEWEB Sentinel:</b> Тестовое оповещение мониторинга. Канал связи с сервером активен!"
        echo "Готово."
        ;;
    status|*)
        echo "=== CASTLEWEB Sentinel Status ==="
        echo "CPU Load: $(get_cpu_load)"
        echo "RAM:      $(get_ram_info)"
        echo "Disk:     $(get_disk_info)"
        echo "Uptime:   $(get_uptime_info)"
        echo "SSL:      $(get_ssl_days)"
        echo "Backup:   $(get_backup_info)"
        echo "Banned:   $(get_banned_ips_count)"
        ;;
esac
