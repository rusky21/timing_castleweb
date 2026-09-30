# 🏰 CASTLEWEB Engineering Studio

> Высоконагруженные веб-платформы, SaaS-сервисы, интерактивный 3D WebGL и Telegram Headless CRM.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19.0-61DAFB.svg?logo=react&logoColor=black)](https://react.dev)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16.0-4169E1.svg?logo=postgresql&logoColor=white)](https://www.postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-7.0-DC382D.svg?logo=redis&logoColor=white)](https://redis.io)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg?logo=docker&logoColor=white)](https://www.docker.com)
[![License](https://img.shields.io/badge/License-Proprietary-blue.svg)](#)

---

## ⚡ О проекте

Официальная платформа инженерной студии **CASTLEWEB**. 
Архитектура построена на принципах **Clean Architecture**, **Zero-Cost инфраструктуры** (0 ₽ расходов на CRM и CDN трафик) и максимальной производительности (отклик API < 50ms, выдерживание пиковых нагрузок > 10 000 TPS).

### 🌟 Ключевые возможности:
- **Современный Obsidian Dark интерфейс** в стиле Salesrocket с интерактивной 3D Liquid Chrome визуализацией.
- **Интерактивный конфигуратор стоимости проекта** с моментальным переносом сметы в заявку.
- **Портфолио с архитектурными кейсами**: детальные разборы решений, графики и подтвержденные метрики.
- **Telegram Headless CRM**: автоматическая доставка заявок в закрытый канал инженеров со сменой статусов в 1 клик.
- **Безопасность и антиспам**: Cloudflare Turnstile, скрытый Honeypot и Rate Limiter по IP.
- **0 ₽ за хранение и исходящий трафик**: прямая интеграция с Cloudflare R2 (10 GB free S3, zero egress fee).

---

## 🛠 Технологический стек

| Слой | Технологии |
|---|---|
| **Frontend** | React 19, Vite 6, Plus Jakarta Sans, Lucide Icons, Vanilla CSS Design System |
| **Backend** | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0 (Async), Alembic |
| **Базы данных & Кэш** | PostgreSQL 16 (asyncpg connection pool), Redis 7 (L2 LRU Cache) |
| **Инфраструктура & DevOps** | Docker Compose, Nginx (HTTP/2, SSL termination), Certbot, Cloudflare WAF & R2 |

---

## 🚀 Быстрый старт

### Локальная разработка (Windows):
```powershell
# Запуск бэкенда и SPA в нативном режиме:
.\scripts\deploy.ps1 -RunNative

# Или конфигурация .env:
.\scripts\deploy.ps1 -ConfigOnly
```
* **Сайт:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
* **Интерактивный Swagger API:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* **Живая телеметрия (JSON):** [http://127.0.0.1:8000/api/v1/status](http://127.0.0.1:8000/api/v1/status)

---

### Боевое развертывание на VDS (Ubuntu Linux):
```bash
# Клонируйте репозиторий:
git clone https://github.com/rusky21/timing_castleweb.git /var/www/castleweb
cd /var/www/castleweb

# Запустите полностью автоматический деплой:
sudo ./scripts/deploy.sh
```
Скрипт в интерактивном режиме:
1. Запросит домен, токен Telegram-бота и Chat ID дежурных инженеров.
2. Установит Docker Engine и настроит ротацию логов (10m x 3).
3. Соберет оптимизированный фронтенд в `node:22-alpine`.
4. Сгенерирует конфигурацию Nginx с защитой Cloudflare Real IP.
5. Выпустит бесплатный SSL-сертификат Let's Encrypt и настроит автопродление по cron.
6. Применит миграции базы данных через Alembic (`alembic upgrade head`).

---

## 📁 Структура проекта

```text
├── apps/
│   ├── backend/               # FastAPI Clean Architecture бэкенд
│   │   ├── app/
│   │   │   ├── core/          # Конфигурация, базы данных, Redis
│   │   │   ├── domain/        # Чистые сущности и бизнес-логика
│   │   │   ├── infrastructure/# Репозитории БД, хранилище R2, Telegram бот
│   │   │   └── presentation/  # REST API эндпоинты, Pydantic схемы
│   │   ├── migrations/        # Миграции Alembic
│   │   └── tests/             # Pytest тесты
│   └── frontend/              # React 19 + Vite SPA приложение
│       ├── public/            # 3D Chrome ассеты и медиа кейсов
│       └── src/
│           ├── components/    # Модульные компоненты (Hero, Cases, Calc, Form)
│           └── index.css      # Obsidian Dark дизайн-система
├── nginx/                     # Конфигурация обратного прокси и WAF
├── scripts/                   # Автоматизированные скрипты deploy.sh и deploy.ps1
└── docker-compose.prod.yml    # Производственный стек контейнеров
```

---

## 📄 Лицензия

Все права защищены © CASTLEWEB Engineering Studio.
