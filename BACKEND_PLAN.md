# 🏰 CASTLEWEB — Архитектурный план и Roadmap бэкенда

> **Формат проекта:** Монорепозиторий (`/apps/backend` + `/apps/frontend`)  
> **Стек бэкенда:** Python 3.12+ / FastAPI / SQLAlchemy 2.0 (Async) / PostgreSQL / Redis / Docker  
> **Бюджет инфраструктуры:** 0 ₽ (100% Free Tier & Self-hosted)  
> **Управление заявками:** Headless CRM в Telegram (интерактивные инлайн-кнопки без веб-админки)

---

## 1. Архитектура приложения (Clean Architecture)

Проект строится по принципам чистой слоистой архитектуры, обеспечивающей независимость бизнес-логики от фреймворка, базы данных и внешних API.

```
apps/backend/
├── app/
│   ├── core/                  # Конфигурация (.env), безопасность, зависимости
│   │   ├── config.py          # Pydantic Settings
│   │   ├── security.py        # Валидация Turnstile, хэширование
│   │   └── redis.py           # Пул соединений Redis
│   │
│   ├── domain/                # Доменный слой (чистые сущности и бизнес-правила)
│   │   ├── entities/          # Lead, Case, Attachment, Blacklist
│   │   └── interfaces/        # Интерфейсы репозиториев и нотификаторов
│   │
│   ├── application/           # Слой Use Cases (сценарии использования)
│   │   ├── leads/             # CreateLeadUseCase, ChangeLeadStatusUseCase
│   │   ├── cases/             # GetCasesListUseCase, GetCaseDetailUseCase
│   │   ├── enrich/            # EnrichLeadDataUseCase (GeoIP + Whois)
│   │   └── notifications/     # SendTelegramNotificationUseCase, SendAutoReplyUseCase
│   │
│   ├── infrastructure/        # Адаптеры внешних систем и БД
│   │   ├── db/                # SQLAlchemy модели, сессии, репозитории
│   │   │   ├── models/        # LeadModel, CaseModel, TagModel
│   │   │   └── repositories/  # LeadRepositoryImpl, CaseRepositoryImpl
│   │   ├── storage/           # S3 / Cloudflare R2 / Local volume адаптер
│   │   ├── queue/             # Фоновые воркеры (Redis Queue / ARQ / Celery)
│   │   └── telegram/          # Клиент Telegram Bot API (через Cloudflare Proxy)
│   │
│   └── presentation/          # Слой доставки (API, Webhooks, Schemas)
│       ├── api/v1/
│       │   ├── endpoints/     # leads.py, cases.py, status.py, uploads.py
│       │   └── router.py      # Сборка роутеров
│       ├── schemas/           # Pydantic v2 DTO схемы (вход/выход)
│       ├── telegram_webhook/  # Хэндлер нажатий inline-кнопок из Telegram
│       └── middlewares/       # RateLimitMiddleware, SecurityHeaders, ErrorHandler
│
├── data/                      # Данные для сидирования (Content-as-Code)
│   └── cases.json             # Структурированные кейсы портфолио
├── migrations/                # Alembic миграции
├── scripts/
│   └── seed_cases.py          # Скрипт наполнения БД из data/cases.json
├── tests/                     # Pytest юнит- и интеграционные тесты
├── Dockerfile                 # Многоэтапный Dockerfile
├── requirements.txt           # Зависимости
└── main.py                    # Точка входа ASGI
```

---

## 2. Бесплатный стек инфраструктуры (0 ₽)

| Компонент | Выбранное решение | Почему 0 ₽ |
| :--- | :--- | :--- |
| **Backend Runtime** | **Python 3.12 + FastAPI (Uvicorn)** | Высокая производительность, асинхронный I/O, Pydantic v2. |
| **База данных** | **PostgreSQL 16** в Docker Compose | Запускается на том же VPS рядом с бэкендом, без платных облачных баз. |
| **Кэш и очереди** | **Redis 7** в Docker Compose | Rate limiting, кэш кейсов, очереди задач нотификаций. |
| **Хранилище файлов** | **Cloudflare R2** (или локальный Docker volume) | У Cloudflare R2 бесплатный тариф: **10 ГБ хранилища** и **0$ за исходящий трафик** навсегда. |
| **Telegram прокси** | **Cloudflare Worker** | Обход блокировок и задержек `api.telegram.org` (бесплатно до 100k запросов в день). |
| **Капча / WAF** | **Cloudflare Turnstile + DNS Proxy** | Невидимая капча без пазлов + DDoS защита (бесплатно). |
| **Email-резерв** | **Resend** (или бесплатный SMTP Яндекс/Mail) | До 3000 транзакционных писем в месяц бесплатно. |
| **SSL-сертификаты** | **Let's Encrypt / Certbot** | Автоматический выпуск и продление через Nginx. |

---

## 3. Спецификация API-эндпоинтов

### Публичный API (для фронтенда)
1. `POST /api/v1/leads`
   * **Назначение:** Прием заявки с сайта.
   * **Защита:** Rate Limit (макс. 3 запроса/10 мин с IP), Honeypot-поле `hp_website`, токен Turnstile.
   * **Логика:**
     1. Проверка honeypot и капчи.
     2. Транзакционная запись в БД со статусом `pending`.
     3. Запуск фоновой задачи в Redis: обогащение данных + отправка в Telegram + автоответ клиенту.
     4. Мгновенный ответ клиенту: `201 Created` (`{ success: true, lead_id: "..." }`).
2. `GET /api/v1/cases`
   * **Назначение:** Каталог кейсов.
   * **Query-параметры:** `?category=saas&stack=fastapi,react&sort=featured`.
   * **Кэш:** Результат кэшируется в Redis на 1 час (сбрасывается при сидировании).
3. `GET /api/v1/cases/{slug}`
   * **Назначение:** Полный технический разбор кейса (схема БД, результаты, видео, метрики).
4. `GET /api/v1/status`
   * **Назначение:** Live-виджет надежности студии.
   * **Ответ:** Uptime сервиса, средний пинг API (`latency: "9ms"`), статусы сервисов (`db: "ok"`, `redis: "ok"`).
5. `POST /api/v1/uploads/presigned-url`
   * **Назначение:** Выдача временной ссылки (10 минут) для прямой загрузки ТЗ/макетов в Cloudflare R2 минуя память сервера.

### Системный Webhook API (для Telegram)
* `POST /api/v1/telegram/webhook`
  * Обработка нажатий инлайн-кнопок из закрытого чата инженеров:
    * `lead_take:{id}` — зафиксировать взятие проекта в работу.
    * `lead_contacted:{id}` — перевести в статус «Связались».
    * `lead_spam:{id}` — отклонить и автоматически забанить IP/контакт спамера в Redis.

---

## 4. Headless CRM в Telegram (Спецификация бота)

Когда на сайте отправляется заявка, бот студии присылает сообщение в закрытый чат инженеров:

```text
🔥 НОВАЯ ЗАЯВКА #104
━━━━━━━━━━━━━━━━━━━━
👤 Клиент: Иван Петров
💬 Контакт: @ivan_founder (Telegram)
💰 Бюджет: 500 000 – 1 000 000 ₽
📝 Задача: Нужен высоконагруженный бэкенд для финтех-сервиса с интеграцией эквайринга.
📎 Вложение: tz_fintech_v1.pdf (Cloudflare R2)

📍 Обогащение данных (GeoIP & Web):
• Город/Страна: Москва, Россия (UTC+3)
• IP: 185.220.xxx.xxx (Провайдер: Selectel)
━━━━━━━━━━━━━━━━━━━━
[💬 Написать в Telegram]  [⚡ Взять в работу]
[✅ Связался]             [🚫 Спам / В бан]
```

**Команды бота для инженеров:**
* `/stats` — сводка: конверсия, количество лидов за неделю/месяц, средний чек.
* `/leads` — последние 5 активных лидов со статусами.

---

## 5. Пошаговый Roadmap реализации бэкенда

### Спринт 1: Фундамент, Монорепозиторий и Данные (✅ Выполнен)
- [x] Инициализация структуры монорепозитория (`/apps/backend`, `/apps/frontend`, `docker-compose.yml`).
- [x] Настройка каркаса FastAPI + Pydantic v2 Settings (`.env` конфигурация).
- [x] Настройка SQLAlchemy 2.0 (asyncpg / aiosqlite) + миграции Alembic.
- [x] Модели таблиц: `leads`, `cases`, `tags`, `blacklist`, `case_tags`.
- [x] Механизм Content-as-Code: скрипт `scripts/seed_cases.py` для заливки кейсов из `data/cases.json` в базу данных.
- [x] Базовый API v1 (`/health`, `/status`, `/cases`, `/cases/{slug}`, `/leads`).
- [x] Тестовый набор Pytest и проверка работоспособности.

### Спринт 2: Защита, Лидогенерация и Очереди (✅ Выполнен)
- [x] Подключение Redis-пула с graceful fallback на in-memory (`app/core/redis.py`).
- [x] Реализация `RateLimitMiddleware` (скользящее окно 3 запроса/10 мин) (`app/presentation/middlewares/rate_limit.py`).
- [x] Защита от спама: Honeypot-ловушка + верификатор токенов Cloudflare Turnstile (`app/core/security.py`).
- [x] Эндпоинт `POST /api/v1/leads`:
  * Транзакционная запись заявки в БД (Save First).
  * Постановка задачи в очередь фонового воркера (`app/infrastructure/queue/lead_queue.py`).
- [x] Фоновый воркер с GeoIP обогащением данных (`app/infrastructure/queue/worker.py`).
- [x] Полное покрытие тестами Pytest (Rate Limit 429, Honeypot, Queue).

### Спринт 3: Интеграция с Telegram и Фоновые сервисы (✅ Выполнен)
- [x] Cloudflare Worker: скрипт обратного прокси для Telegram Bot API (`scripts/cloudflare_worker_tg_proxy.js`).
- [x] Сервис Telegram Bot API (`app/infr  astructure/telegram/bot_service.py`):
  * Форматирование карточки с кнопками прямого перехода к диалогу (`tg://resolve?domain=...`).
  * Инлайн-кнопки управления заявкой (`Взять в работу`, `Связался`, `В бан / Спам`).
  * Редактирование сообщений в Telegram при нажатии кнопок.
- [x] Webhook хэндлер Telegram (`app/presentation/api/v1/endpoints/telegram_webhook.py`):
  * Обработка `callback_query`: обновление статуса в БД, фиксация инженера (`handled_by`).
  * Кнопка «Спам»: мгновенное занесение IP и контакта в `Blacklist` и блокировка последующих запросов.
  * Инженерные команды: `/stats` (сводка по статусам заявок) и `/leads` (последние 5 лидов).
- [x] Фоновый воркер с отправкой в Telegram и GeoIP обогащением (`app/infrastructure/queue/worker.py`).
- [x] Полное тестирование через Pytest (`4 passed`).

### Спринт 4: Каталог кейсов, Файлы и Live Status (✅ Выполнен)
- [x] Эндпоинты `GET /api/v1/cases` и `GET /api/v1/cases/{slug}` с кэшированием в Redis на 1 час (`app/presentation/api/v1/endpoints/cases.py`).
- [x] Сервис загрузки файлов (`app/infrastructure/storage/r2_storage.py`):
  * Генерация Presigned PUT URLs для Cloudflare R2 со сроком жизни 10 мин (прямой аплоад минуя память сервера).
  * Локальный fallback-эндпоинт `POST /api/v1/uploads/file` и раздача статических файлов из `/uploads`.
  * Валидация форматов и ограничение размера файлов до 50 МБ.
- [x] Эндпоинт `GET /api/v1/status` (live-метрики пинга БД и Redis, аптайм, статус систем).
- [x] Полное тестирование через Pytest (`5 passed`).

### Спринт 5: Production Docker, Nginx и CI/CD (✅ Выполнен)
- [x] Написание многоэтапного `Dockerfile` на базе `python:3.12-slim` с `entrypoint.sh` скриптом автомиграций (`apps/backend/Dockerfile`).
- [x] Конфигурация `docker-compose.prod.yml` (FastAPI + PostgreSQL 16 + Redis 7 + Nginx + Certbot).
- [x] Конфиг Nginx (`nginx/nginx.conf`, `nginx/conf.d/default.conf`): Reverse Proxy, SSL Let's Encrypt, Gzip, WebSocket, буферизация и кэширование статики.
- [x] GitHub Actions CI/CD (`.github/workflows/ci-cd.yml`): автоматический запуск тестов Pytest и автодеплой на сервер по SSH.

### Спринт 6: Скрипт автоматического развертывания (Ubuntu 26.04 LTS), Интерактивный визард .env и Интеграция Фронтенда (✅ Выполнен)
- [x] Интерактивный терминальный конфигуратор переменных окружения (ввод токенов бота, чатов, ключей Turnstile, генерация безопасных паролей БД и JWT-секретов с валидацией).
- [x] Оптимизация под Ubuntu 26.04 LTS (non-interactive режим, подавление needrestart-диалогов, Swap 2-4 ГБ, базовая безопасность UFW/fail2ban с закрытием портов БД от внешней сети).
- [x] Установка Docker Engine & Docker Compose Plugin официальным скриптом.
- [x] Изолированный сборщик фронтенда (Zero Host Pollution): автоматическая сборка фронтенда во временном Docker-контейнере `node:22-alpine` при наличии `apps/frontend` без установки Node.js на хост.
- [x] Поддержка автономных режимов скрипта: `--full` (первичная настройка сервера), `--frontend-only` (быстрый ребилд фронтенда при обновлениях), `--backend-only` (обновление контейнеров бэкенда), `--config-only` (перегенерация `.env`).
- [x] Интеграция Nginx с автовыпуском SSL Let's Encrypt и Cloudflare Real IP (определение реальных IP клиентов для Rate Limiter).
- [x] Автоматические Smoke-тесты здоровья API (`/api/v1/health`, `/api/v1/status`) и вывод итоговой сводки.

---

## 6. Детальный план скрипта серверного развертывания (`scripts/deploy.sh` для Ubuntu 26.04 LTS)

Скрипт проектируется как идемпотентный, автономный инструмент первоначальной подготовки "чистого" сервера Ubuntu 26.04 LTS и последующих накатов обновлений бэкенда и фронтенда.

### Блок 0: Интерактивный конфигуратор администратора (Interactive .env Wizard)
Если файл `apps/backend/.env` отсутствует (или запуск выполнен с флагом `--config`), скрипт запускает интерактивный пошаговый мастер в консоли:
1. **Домен и SSL:**
   - `DOMAIN_NAME` (например, `castleweb.ru` или `api.castleweb.ru`)
   - `ADMIN_EMAIL` (email администратора для уведомлений Certbot / Let's Encrypt)
2. **Telegram Bot & CRM:**
   - `TELEGRAM_BOT_TOKEN` (токен от @BotFather)
   - `TELEGRAM_CHAT_ID` (ID закрытого чата инженеров для получения лидов)
   - `TELEGRAM_PROXY_URL` (URL Cloudflare Worker прокси или прямой `https://api.telegram.org`)
3. **Безопасность и Антиспам:**
   - `TURNSTILE_SECRET_KEY` (секретный ключ Cloudflare Turnstile)
   - `POSTGRES_PASSWORD` (автоматическая генерация надежного пароля через `openssl rand -base64 24` с возможностью задать свой)
   - `SECRET_KEY` (автоматическая генерация криптографического ключа `openssl rand -hex 32`)
4. **Хранилище файлов (Cloudflare R2 / S3 — опционально):**
   - Запрос на использование внешнего S3 или локального диска сервера.
   - При выборе R2: `CLOUDFLARE_R2_ACCOUNT_ID`, `CLOUDFLARE_R2_ACCESS_KEY_ID`, `CLOUDFLARE_R2_SECRET_ACCESS_KEY`, `CLOUDFLARE_R2_BUCKET_NAME`, `CLOUDFLARE_R2_PUBLIC_URL`.
5. **CORS и окружение:**
   - Автоматическая подстановка `CORS_ORIGINS=["https://${DOMAIN_NAME}"]`.
   - Запись готового файла в `apps/backend/.env` и установка прав доступа `chmod 600`.

### Блок 1: Подготовка и безопасность ОС (Ubuntu 26.04 LTS)
- **Non-interactive режим:** Экспорт `DEBIAN_FRONTEND=noninteractive` и конфигурация `needrestart` (`needrestart -r a`), чтобы предотвратить зависание скрипта на интерактивных экранах обновления ядра/сервисов Ubuntu 26.04.
- **Обновление пакетов:** `apt update && apt upgrade -y`.
- **Файл подкачки (Swap):** Выделение 2–4 ГБ подкачки (`fallocate -l 2G /swapfile`, `chmod 600`, `mkswap`, `swapon`, автодобавление в `/etc/fstab` с `vm.swappiness=10`) для предотвращения OOM-killer при сборке контейнеров на недорогих VPS (1-2 ГБ RAM).
- **Базовые утилиты:** `curl`, `git`, `ufw`, `fail2ban`, `jq`, `certbot`, `python3-certbot-nginx`.
- **Файрвол UFW:**
  - Открытие портов 22 (SSH), 80 (HTTP), 443 (HTTPS).
  - Запрет внешнего доступа к портам 5432 (PostgreSQL) и 6379 (Redis) — только внутри закрытой Docker-сети `castleweb_internal`.
  - Включение UFW (`ufw --force enable`).

### Блок 2: Контейнеризация (Docker & Compose)
- Автоматическая установка последней версии Docker Engine и Docker Compose Plugin через официальный скрипт `https://get.docker.com`.
- Включение автозапуска демона `systemctl enable --now docker`.

### Блок 3: Сборка и деплой фронтенда (Zero Host Pollution)
- **Умное обнаружение фронтенда:** Проверка наличия директории `apps/frontend` и файла `package.json`.
- **Изолированная сборка через Docker:** Чтобы не засорять хост-систему Ubuntu пакетами Node.js и глобальными npm-модулями, сборка артефактов SPA/SSR запускается в эфемерном контейнере:
  ```bash
  docker run --rm \
    -v $(pwd)/apps/frontend:/app \
    -w /app \
    -e VITE_API_URL="https://${DOMAIN_NAME}" \
    node:22-alpine \
    sh -c "npm ci && npm run build"
  ```
- **Раздача статики:** Артефакты из `apps/frontend/dist` монтируются в Nginx (`/var/www/castleweb/frontend`) с долговременным кэшированием неизменяемых хэшированных ассетов (`Cache-Control: public, max-age=31536000, immutable`).
- **Сценарий до добавления фронтенда:** Если фронтенд еще в разработке, Nginx раздает встроенную техническую заглушку-страничку с live-статусом API или проксирует корень на бэкенд `/docs`.
- **Быстрый накат фронтенда:** Наличие флага `./deploy.sh --frontend-only`, позволяющего пересобрать и обновить фронтенд за 15 секунд без перезапуска баз данных и бэкенда.

### Блок 4: Сеть и Nginx Reverse Proxy (с поддержкой Cloudflare Real IP)
- Генерация конфигурации доверенных IP-диапазонов Cloudflare (`set_real_ip_from` для IPv4 и IPv6) для корректной работы Rate Limiter и бана спамеров по реальным IP клиентов.
- Настройка `default.conf` с разделением маршрутов:
  - `/api/` и `/docs` -> проксирование на `backend:8000`.
  - `/uploads/` -> раздача загруженных файлов ТЗ из volume.
  - `/` -> SPA маршрутизация с fallback на `index.html`.

### Блок 5: SSL, Cron и Запуск
- Первичный выпуск Let's Encrypt сертификата через Certbot (Standalone или Webroot).
- Автоматическое добавление задачи продления Let's Encrypt в системный crontab (`0 */12 * * *`).
- Запуск продакшн-контейнеров: `docker compose -f docker-compose.prod.yml up -d --build`.
- Автоматический накат миграций Alembic (`alembic upgrade head`).
- Автоматическая регистрация Telegram Webhook с валидацией ответа API.
- Проверка здоровья через `curl -sf http://localhost:8000/api/v1/health` и `status`.
- Вывод карточки готовности сервера в консоль.

### Кросс-платформенность: PowerShell-версия для Windows (`scripts/deploy.ps1`)
Для удобной локальной разработки и тестирования в среде Windows (Docker Desktop) создан нативный PowerShell-скрипт [scripts/deploy.ps1](file:///c:/Users/fake_netrunner/Desktop/мой%20сайтик%29%29%29%29%29/scripts/deploy.ps1):
- Интерактивный визард создания `.env` с генерацией паролей PostgreSQL и секретных ключей.
- Автоматическая проверка статуса Docker Desktop.
- Сборка фронтенда во временном контейнере `node:22-alpine` без установки Node.js на хост.
- Автоматическое применение миграций Alembic после запуска БД.
- Команды: `.\scripts\deploy.ps1 [-Full | -FrontendOnly | -BackendOnly | -Migrate | -Status]`.

