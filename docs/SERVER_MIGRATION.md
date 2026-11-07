# Перенос CASTLEWEB на новый VDS

Инструкция повторяет фактическую схему развёртывания проекта. Значения в угловых скобках заменяйте своими. Секреты не добавляйте в Git и не вставляйте в команды, которые сохраняются в shell history.

## 1. Подготовить DNS и доступ

До переключения домена сохраните доступ к старому серверу и сделайте резервные копии PostgreSQL, Docker volumes и загруженных файлов. На новом сервере проверьте SSH host keys:

```bash
ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub -E sha256
ssh-keygen -lf /etc/ssh/ssh_host_ecdsa_key.pub -E sha256
```

ED25519 используйте для ручной проверки первого подключения. ECDSA fingerprint закрепляется в `.github/workflows/ci-cd.yml`, потому что его согласовывает SSH-клиент GitHub Action.

## 2. Обновить ОС и получить проект

```bash
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get upgrade -y
apt-get install -y git curl ca-certificates
git clone https://github.com/rusky21/timing_castleweb.git /root/timing_castleweb
cd /root/timing_castleweb
```

Если `apt` занят автоматическим обновлением, дождитесь завершения процесса. Не удаляйте lock-файлы `apt` или `dpkg` вручную.

## 3. Создать серверные `.env`

```bash
cp apps/backend/.env.example apps/backend/.env
cp apps/parser/.env.example apps/parser/.env
touch .env
chmod 600 apps/backend/.env apps/parser/.env .env
```

Заполните реальные значения через редактор на сервере. Обязательные группы настроек: PostgreSQL, Redis, Telegram bot, Turnstile и LeadHunter. `ADMIN_EMAIL` должен содержать синтаксически корректный адрес: Certbot использует его при регистрации ACME-аккаунта. Файлы `.env` остаются только на сервере и никогда не коммитятся.

## 4. Выполнить первый production-деплой

```bash
cd /root/timing_castleweb
./scripts/deploy.sh --full
```

Скрипт устанавливает Docker, включает UFW и fail2ban, создаёт swap при необходимости, собирает frontend и Docker images, запускает миграции и контейнеры. При вопросе о перезаписи уже заполненных `.env` отвечайте `n`.

Если домены ещё указывают на старый IP, скрипт оставит временный самоподписанный сертификат. После переключения DNS выпустите настоящий сертификат:

```bash
cd /root/timing_castleweb
./scripts/deploy.sh --ssl
docker compose --env-file apps/backend/.env -f docker-compose.prod.yml restart nginx
```

## 5. Ограничить сетевой доступ

Публичными должны быть только SSH, HTTP и HTTPS:

```bash
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp comment 'SSH'
ufw allow 80/tcp comment 'HTTP'
ufw allow 443/tcp comment 'HTTPS'
ufw --force enable
ufw status verbose
```

Проверьте фактические listeners:

```bash
ss -lntup
docker compose --env-file apps/backend/.env -f docker-compose.prod.yml ps
```

Ожидаемая схема:

- `22`, `80`, `443` слушают публичные адреса;
- backend `8000` и LeadHunter `8080` привязаны только к `127.0.0.1`;
- PostgreSQL `5432` и Redis `6379` не имеют host-публикации;
- DNS resolver и chrony могут слушать loopback.

Важно: Docker умеет обходить обычные UFW-правила для опубликованных портов. Поэтому внутренние сервисы защищаются не только UFW, но и отсутствием `ports` либо явной привязкой `127.0.0.1:host:container` в Compose.

## 6. Перенести CI/CD

Лучше использовать отдельный ED25519-ключ GitHub Actions. Публичную часть добавьте deploy-пользователю:

```bash
install -d -m 700 /root/.ssh
touch /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys
```

Добавьте одну строку публичного ключа в `/root/.ssh/authorized_keys`. Приватный ключ храните только в GitHub Environment secret `PROD_SSH_KEY`.

В GitHub откройте `Settings → Environments → prod` и задайте secrets:

- `PROD_HOST` — новый IP;
- `PROD_USER` — deploy-пользователь;
- `PROD_PORT` — SSH-порт, обычно `22`;
- `PROD_SSH_KEY` — приватный CI-ключ.

Environment variables:

- `PROD_PATH=/root/timing_castleweb`;
- `PROD_URL=https://castleweb.ru`;
- `PROD_HEALTH_URL=https://castleweb.ru/api/v1/health`.

Обновите ECDSA fingerprint в `.github/workflows/ci-cd.yml`, затем отправьте commit в `main`. Workflow выполнит тесты и запустит `scripts/auto-deploy.sh` на сервере.

## 7. Переключить DNS

Поменяйте A-записи основного домена и `leads` на новый IP. Если используется Cloudflare proxy, на время первого выпуска Let's Encrypt при необходимости выключите proxy (режим DNS only), дождитесь обновления DNS и выполните `./scripts/deploy.sh --ssl`. После успешного выпуска сертификата proxy можно вернуть.

Проверка DNS:

```bash
getent ahostsv4 castleweb.ru
getent ahostsv4 leads.castleweb.ru
```

## 8. Финальная проверка

```bash
cd /root/timing_castleweb
docker compose --env-file apps/backend/.env -f docker-compose.prod.yml ps
curl -fsS http://127.0.0.1:8000/api/v1/health
curl -fsS http://127.0.0.1:8080/health
curl -fsS https://castleweb.ru/api/v1/health
fail2ban-client status sshd
ufw status verbose
git rev-parse HEAD
```

В GitHub Actions все CI jobs и `Deploy production` должны быть зелёными, а SHA на сервере должен совпадать с SHA workflow.

После успешной проверки смените временный root-пароль. Ещё безопаснее создать отдельного deploy-пользователя, разрешить ему Docker и вход только по SSH-ключу, а затем отключить SSH-вход root по паролю — но делать это следует только после отдельной проверки входа в новой сессии.
