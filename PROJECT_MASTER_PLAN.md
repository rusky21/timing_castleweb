# 🏰 CASTLEWEB & LEADHUNTER PRO — ЕДИНЫЙ МАСТЕР-ПЛАН ПРОЕКТА
> **Единый источник правды (Single Source of Truth) для всей экосистемы.**  
> **ОБЯЗАТЕЛЬНЫЙ РЕГЛАМЕНТ:** Любые новые требования, изменения, планы доработок и технические решения по проекту в обязательном порядке добавляются и ведутся исключительно в данном файле (`PROJECT_MASTER_PLAN.md`). Создание сторонних разрозненных файлов планов строго запрещено.
> Объединяет архитектуру бэкенда студии, новый дизайн Castleweb v2, мультибиржевой парсер, геоскрейпинг, аудит безопасности и регламент развертывания.

---

## 📌 ИСПОЛНИТЕЛЬНОЕ РЕЗЮМЕ (EXECUTIVE SUMMARY)

### 1. Архитектурная карта экосистемы
Проект представляет собой коммерческую платформу веб-студии **CastleWeb** с интегрированным автономным комбайном лидогенерации **LeadHunter Pro**:

```
                       ┌───────────────────────────────────────────────┐
                       │          ПОЛЬЗОВАТЕЛИ И КЛИЕНТЫ               │
                       └───────┬───────────────────────────────┬───────┘
                               │                               │
                      HTTPS / Nginx                     HTTPS / WebApp
                               │                               │
                               ▼                               ▼
       ┌───────────────────────────────────┐   ┌───────────────────────────────────┐
       │   CASTLEWEB FRONTEND (SPA)        │   │   LEADHUNTER DASHBOARD (React)    │
       │   apps/frontend/ (Порт 80/443)    │   │   apps/parser/frontend/           │
       └───────────────────┬───────────────┘   └───────────────────┬───────────────┘
                           │                                       │
                           ▼                                       ▼
       ┌───────────────────────────────────┐   ┌───────────────────────────────────┐
       │   CASTLEWEB BACKEND (FastAPI)     │   │   LEADHUNTER PARSER API (FastAPI) │
       │   apps/backend/ (Порт 8000)       │◄──┤   apps/parser/ (Порт 8080)        │
       │   • Clean Architecture            │   │   • Мультибиржевой комбайн (9-10) │
       │   • PostgreSQL + Redis            │   │   • Яндекс.Карты + 2ГИС           │
       │   • Headless CRM в Telegram       │   │   • Аудит сайтов + AI Офферы      │
       └───────────────────┬───────────────┘   └───────────────────┬───────────────┘
                           │                                       │
                           └───────────────┬───────────────────────┘
                                           │
                                           ▼
                       ┌───────────────────────────────────────┐
                       │    TELEGRAM HEADLESS CRM & ALERTS     │
                       │    @castleweb_bot & Личный бот        │
                       │    (Только для админов студии)        │
                       └───────────────────────────────────────┘
```

---

### 2. Матрица статуса модулей проекта

| Модуль | Расположение | Статус | Описание |
| :--- | :--- | :---: | :--- |
| **CastleWeb Frontend** | `apps/frontend/` | ✅ Готов (v2) | Премиум-дизайн Castleweb v2, Bento-сетка, интерактивный веер карточек, интеграция заявок с FastAPI |
| **CastleWeb Backend** | `apps/backend/` | ✅ Готов | FastAPI, Clean Architecture, Headless CRM в Telegram, Postgres + Redis |
| **Геопарсер карт** | `apps/parser/app/services/scrapers/` | ✅ Готов | Сбор лидов с Яндекс.Карт и 2ГИС через Playwright, обход капчи, SQLite |
| **Глубокий аудит сайтов** | `apps/parser/app/services/site_auditor.py` | ✅ Готов | Проверка SSL, адаптивности, счетчиков, CMS, контактов, AI генерация офферов |
| **Мультибиржа заказов** | `apps/parser/app/services/scrapers/` | ✅ Готов | Сбор FL.ru, Kwork, Freelance.ru, Workspace. Строгая фильтрация (только бесплатные и общедоступные) |
| **Безопасность и стабильность** | `apps/parser/` | ✅ Готов | Закрыты P0/P1 уязвимости (XSS, Open Redirect, Hash ID, Path Traversal, SSRF DNS) |
| **Telegram-уведомления** | `apps/parser/` & `apps/backend/` | ✅ Готов | Устранено дублирование FL.ru, единый визуальный стиль и роутинг сообщений |

---

### 3. Фокус текущего спринта (Горящие задачи)
1. **Фильтрация откликов**: строгий отбор **только бесплатных и доступных для всех** заказов (FL.ru, Kwork, Freelance.ru, Workspace). Платные отклики, пакеты и PRO должны полностью отсекаться.
2. **Устранение дублей FL.ru**: прекратить отправку заказов FL.ru в двух разных форматах (через локальный диспетчер парсера и через webhook бэкенда).
3. **Исправление аудита безопасности**:
   - `P0`: Устранение XSS в `main.py`, Open Redirect в `auth.py`, удаление дефолтного хардкода `TELEGRAM_API_HASH`.
   - `P1`: Детерминированный MD5 ID заказов вместо `hash()`, защита от Path Traversal, асинхронный DNS в аудите.

---

# ЧАСТЬ I. ТЕКУЩИЙ СПРИНТ — ИСПРАВЛЕНИЯ ПАРСЕРА, СТРОГАЯ ФИЛЬТРАЦИЯ И АУДИТ БЕЗОПАСНОСТИ

## 1. Детальный анализ первопричин (Root Cause)

### А. Почему сообщения FL.ru дублируются в двух разных форматах?
1. В `apps/parser/app/services/fl/fl_worker.py` при получении заказа вызываются **две параллельные ветки доставки**:
   - `await tg_dispatcher.dispatch_fl_order(order)` — формирует сообщение в формате `🟠 #FL | Заголовок` с кнопками «В избранное / Скрыть / Открыть проект».
   - `await self._notify_backend_fl_order(order)` — отправляет HTTP POST запрос на `backend:8000/api/v1/telegram/fl-order`, где бэкенд студии формирует сообщение по другому шаблону `⚡️ Новый заказ с FL.ru...` и рассылает в тот же чат админа.
2. В `apps/parser/app/services/orchestrator.py` биржа `"fl"` активна по умолчанию наряду с `fl_worker.py`. В результате оба сервиса опрашивают биржу и дублируют логику оповещений.

### Б. Почему приходят платные заказы и PRO?
- В `fl_worker.py` (строка 169) и `scrapers/fl.py` (строка 20) метод `fetch_projects` вызывается с `only_free=False`.
- В `scrapers/freelanceru.py` флаг `is_pro` вычисляется, но проекты с ним не отсекаются.
- В `scrapers/kwork.py` проекты с фильтрами заказчика `kworks_filters` (требования по рейтингу/отзывам) пропускаются в общий поток.
- В диспетчере `dispatcher.py` отсутствует жесткий фильтр `if not order.is_free: return`.

---

## 2. Контракты и интерфейсы спринта

```python
# 1. scrapers/base.py
@dataclass
class NormalizedOrder:
    composite_id: str
    is_free: bool  # True строго если отклик бесплатный и открыт всем (без PRO, платных пакетов, закрытых фильтров)
    
    def to_fl_order_dict(self) -> Dict[str, Any]:
        # Детерминированный ID на основе MD5 (предотвращает генерацию разных ID для одного заказа после рестарта)
        safe_int_id = int(hashlib.md5(self.composite_id.encode("utf-8")).hexdigest()[:8], 16) % 2147483647
        ...

# 2. fl_fetcher.py
async def fetch_projects(self, category_id: Optional[str] = None, only_free: bool = True) -> List[Dict[str, Any]]:
    """Возвращает исключительно заказы с опцией «для всех», вакансии и конкурсы; PRO исключены"""

# 3. core/security.py / main.py
def is_safe_redirect_url(target_url: str) -> bool:
    """True только если URL относительный, начинается с '/', не содержит '//' и '\\'"""

# 4. site_auditor.py
async def async_resolve_host(host: str) -> List[Tuple[Any, ...]]:
    """Неблокирующий вызов DNS через event loop: asyncio.get_running_loop().getaddrinfo"""
```

---

## 3. Пошаговые задачи реализации
 
### Блок 1. Устранение дублирования FL.ru и единый стиль Telegram
* [x] **`apps/parser/app/services/fl/fl_worker.py`**:
  - В цикле отправки заказа: вызывать `_notify_backend_fl_order` **только при условии**, что `tg_dispatcher.bot is None`. Если локальный бот активен, отправку осуществляет только он.
* [x] **`apps/parser/app/services/orchestrator.py`**:
  - Исключить `"fl"` из списка `enabled_platform_names` по умолчанию (оставить `{"workspace", "freelanceru", "kwork"}`), чтобы избежать двойного опроса FL.ru.
* [x] **`apps/backend/app/presentation/api/v1/endpoints/telegram_webhook.py`**:
  - Привести шаблон сообщения `/fl-order` к единому формату `format_fl_order_message` (`🟠 #FL | ...`).

### Блок 2. Строгая фильтрация (только бесплатные и общедоступные)
* [x] **`apps/parser/app/services/fl/fl_worker.py`**:
  - Вызывать `self.fetcher.fetch_projects(category_id=cat_id, only_free=True)`.
  - В цикле сохранения проверять: `if not proj.get("is_free", False): continue`.
  - В цикле отправки проверять: `if not order.is_free: continue`.
* [x] **`apps/parser/app/services/scrapers/fl.py`**:
  - Вызывать `fetch_projects(only_free=True)` и отсекать `if not p.get("is_free", False): continue`.
* [x] **`apps/parser/app/services/scrapers/freelanceru.py`**:
  - Отсекать PRO заказы: `if is_pro: continue`.
* [x] **`apps/parser/app/services/scrapers/kwork.py`**:
  - Отсекать заказы с фильтрами заказчика: `if w.get("kworks_filters"): continue`.
* [x] **`apps/parser/app/services/orchestrator.py`**:
  - В `_poll_fetcher` добавить гвард: `if not order.is_free: continue`.
* [x] **`apps/parser/app/services/telegram/dispatcher.py`**:
  - В `dispatch_fl_order` добавить гвард: `if not getattr(order, "is_free", True): return`.
* [x] **`apps/backend/app/presentation/api/v1/endpoints/telegram_webhook.py`**:
  - В `broadcast_fl_order` отсекать: `if not is_free or is_pro: return {"ok": True, "skipped": "paid_or_pro_order"}`.

### Блок 3. Устранение критических уязвимостей безопасности (P0)
* [x] **`apps/parser/app/config.py`**:
  - Убрать хардкод `TELEGRAM_API_HASH = "b18441a1ff607e10a989891a5462e627"`. Брать строго из окружения: `os.environ.get("TELEGRAM_API_HASH", "").strip()`.
* [x] **`apps/parser/app/main.py`**:
  - Устранить Stored XSS в инъекции `window.__CURRENT_USER__`: экранировать закрывающий тег скрипта `.replace("<", "\\u003c").replace(">", "\\u003e")`.
  - Устранить Open Redirect в `returnUrl`: проверять через `get_safe_redirect_url`, что путь начинается с `/` и не содержит `//` или `\`.
* [x] **`apps/parser/app/api/auth.py`**:
  - Валидировать `returnUrl` при входе через `get_safe_redirect_url` и экранировать в скрытом input формы.
* [x] **`apps/parser/.env.example`**:
  - Обновить шаблон окружения безопасными плейсхолдерами.

### Блок 4. Архитектурные исправления и стабильность (P1 & P2)
* [x] **`apps/parser/app/services/scrapers/base.py`**:
  - Заменить недетерминированный `hash()` в `to_fl_order_dict()` на `hashlib.md5(f"{self.platform}_{self.external_id}".encode()).hexdigest()[:8]`.
* [x] **`apps/parser/app/main.py`**:
  - Защитить раздачу статики фронтенда `serve_frontend` от Path Traversal через `file_candidate.is_relative_to(FRONTEND_DIST.resolve())`.
* [x] **`apps/parser/app/services/site_auditor.py`**:
  - Заменить блокирующий `socket.getaddrinfo()` на `await asyncio.get_running_loop().getaddrinfo()`.
* [x] **`apps/parser/app/core/utils.py`**:
  - Вынести дублирующуюся функцию нормализации телефонов в единый модуль `normalize_phone`.
* [x] **`apps/parser/app/services/filters.py`**:
  - Оптимизировать `hide_existing_excluded_orders()`: выборка батчами через `yield_per(500)` и стриминг для предотвращения всплесков потребления RAM при старте.
* [x] **`apps/parser/app/db/database.py`**:
  - Заменить пустой `except: pass` в миграциях на логирование и перехват конкретного `OperationalError`.

---

## 4. Критерии приёмки спринта
1. **Синтаксис и компиляция**: `python -m py_compile` успешно проходит по всем затронутым файлам.
2. **Фильтрация**: скрипт dry-run подтверждает:
   - 100% спарсенных заказов имеют `is_free == True`.
   - 0 заказов содержат PRO, платные отклики или фильтры заказчика.
3. **Дедупликация**: при появлении заказа генерируется ровно 1 сообщение в Telegram в едином формате.
4. **Тесты безопасности**:
   - XSS-пейлоад в профиле пользователя экранируется и не исполняется.
   - Запросы `/login?returnUrl=//evil.com` безопасно редиректят на `/`.
   - Попытка Path Traversal через `/../../../../windows/win.ini` отклоняется.
   - `to_fl_order_dict()` возвращает один и тот же ID для заказа в разных сессиях Python.

---

# ЧАСТЬ II. МУЛЬТИБИРЖЕВОЙ КОМБАЙН ПАРСИНГА (10 ПЛОЩАДОК)

## 1. Реестр площадок и векторы подключения

| Площадка | Вектор сбора | Тип защиты | Определение бесплатности отклика (`is_free`) |
| :--- | :--- | :--- | :--- |
| **1. FL.ru** | RSS `all.xml` + HTML лента | DDoS-Guard | Метка `(для всех)`, вакансии, конкурсы; без PRO |
| **2. Kwork** | Встроенный JSON `stateData.wants` | Nginx | Стандартные коннекты; без закрытых фильтров заказчика |
| **3. Freelancehunt** | REST API v2 `/v2/projects` | Cloudflare | `is_plus_only == False` |
| **4. Freelance.ru** | HTML `/task` | DDoS-Guard | Проекты без бейджа PRO (`is_pro == False`) |
| **5. Freelancer.com** | REST API `/api/projects/0.1/projects/active` | Открытое API | Стандартный отклик; без NDA, Sealed и депозита |
| **6. Workspace** | RSS `/tenders/rss/` + HTML | Nginx | Открытая подача на тендер |
| **7. Upwork** | GraphQL/RSS + Прокси | Cloudflare Enterprise | Наличие стартовых коннектов |
| **8. Weblancer** | HTML `/jobs/` | Cloudflare WAF | Доступные заявки по базовому тарифу |
| **9. PeoplePerHour** | HTML `/freelance-jobs` | Cloudflare | Проекты в рамках ежемесячной квоты Proposals |
| **10. Contra** | GraphQL `/api/graphql` | Cloudflare / SPA | Прямой отклик без комиссии фрилансера |

## 2. Разграничение прав (Admin vs Test Mode)
* **Для обычных / демо-пользователей:**
  - Раздел «Биржи фриланса» в веб/десктоп закрыт замком `🔒`. Эндпоинты `/api/fl/*` возвращают `403 Forbidden`.
  - Доступен только парсинг карт с лимитом 10 организаций.
  - Обычные пользователи бота **никогда не получают** уведомления о заказах с бирж.
* **Для администраторов системы:**
  - Полный доступ к ленте всех 10 бирж, фильтрация по платформам, добавление в избранное, скрытие.
  - Мгновенные пуши в Telegram с интерактивными кнопками (`⭐ В избранное`, `❌ Скрыть`, `🔗 Открыть`).

## 3. Stealth-движок и сетевая защита
* **Библиотека:** `curl-cffi` для точной имитации TLS-отпечатков браузера (JA3/JA4, BoringSSL, ALPN h2).
* **HTTP Headers Pipeline:** точный порядок заголовков Chrome (`:authority`, `sec-ch-ua`, `sec-ch-ua-platform: "Windows"`, `User-Agent`).
* **Gaussian Jitter:** случайные интервалы между запросами (30с ± 7с) вместо фиксированных таймеров.
* **Circuit Breaker:** при 3 ошибках подряд опрос площадки ставится на паузу на 5 минут с логированием.

---

# ЧАСТЬ III. ПАРСИНГ ГЕОСЕРВИСОВ И ГЛУБОКИЙ АУДИТ САЙТОВ

## 1. Скрейпинг геосервисов (Яндекс.Карты и 2ГИС)
* **Яндекс.Карты (`yandex_scraper.py`):**
  - Запуск Playwright с рандомизацией отпечатков.
  - Непрерывный сбор данных на лету в `Set[external_id]` для преодоления DOM Virtualization в контейнере выдачи.
  - Детектор конца выдачи для предотвращения вечного цикла.
  - Детекция капчи (`.SmartCaptcha`) с отправкой события через WebSocket и ожиданием ручного решения.
* **2ГИС (`twogis_scraper.py`):**
  - Перехват актуального сессионного ключа API из сетевого запроса к `catalog.api.2gis.com`.
  - Асинхронная пагинация через HTTPX без рендеринга страниц для максимальной скорости сбора.

## 2. Глубокий аудит сайтов (`site_auditor.py`)
* **Анализируемые метрики:**
  - Наличие и валидность SSL сертификата (с обработкой самоподписанных сертификатов без падения аудита).
  - Мобильная адаптивность (`<meta name="viewport">`).
  - Установленная веб-аналитика (Яндекс.Метрика, Google Analytics, пиксели соцсетей).
  - CMS / Конструктор (Tilda, WordPress, Bitrix, Wix, Webflow).
  - Год последнего обновления (копирайт в футере, `sitemap.xml`, заголовок `Last-Modified`).
  - Поиск скрытых контактов на подстраницах (`/contacts`, `/about`, `/policy`): email, телефоны, WhatsApp, Telegram, реквизиты/ИНН.

## 3. Генератор персонализированных офферов (`pitch_maker.py`)
Автоматическое формирование скрипта продаж и болевых точек для звонка менеджера:
* Нет сайта $\rightarrow$ оффер на разработку конверсионного лендинга/квиза под ключ.
* Только соцсеть $\rightarrow$ оффер на собственный сайт для SEO-трафика и сквозной аналитики.
* Нет адаптивности $\rightarrow$ аудит потери до 70% мобильного трафика.
* Нет метрики $\rightarrow$ указание на слив рекламного бюджета вслепую.
* Устаревший сайт $\rightarrow$ предложение редизайна и переноса на современный стек.

---

# ЧАСТЬ IV. АРХИТЕКТУРА БЭКЕНДА СТУДИИ CASTLEWEB (CLEAN ARCHITECTURE)

## 1. Структура слоев (`apps/backend`)
```
apps/backend/app/
├── core/                  # Конфигурация, Pydantic Settings, Turnstile, Redis пул
├── domain/                # Чистые сущности: Lead, Case, Attachment, Blacklist
├── application/           # Сценарии использования (Use Cases):
│   ├── leads/             # Создание, обработка статусов, валидация
│   ├── enrich/            # Обогащение лидов (GeoIP, Whois)
│   └── notifications/     # Telegram-нотификации и автоответчики
├── infrastructure/        # Адаптеры БД (PostgreSQL / SQLite), Redis, S3/R2 Storage
└── presentation/          # FastAPI роутеры v1, Pydantic DTO схемы, Webhooks
```

## 2. Headless CRM в Telegram
* Управление всеми поступающими заявками с сайта студии через Telegram-бота `@castleweb_bot`.
* Интерактивные инлайн-кнопки под карточкой заявки:
  - `[ В работу ]` $\rightarrow$ перевод статуса в `IN_PROGRESS`, назначение ответственного.
  - `[ Успешно ]` $\rightarrow$ статус `COMPLETED`.
  - `[ Спам / В бан ]` $\rightarrow$ статус `SPAM`, автоматическое добавление IP/email в блэклист.
* Защита от спама через Cloudflare Turnstile с серверной верификацией токена.

---

# ЧАСТЬ V. РЕГЛАМЕНТ РАЗВЕРТЫВАНИЯ И ИНФРАСТРУКТУРА

## 1. Схема размещения на сервере (Ubuntu Linux, 2 vCPU / 4 GB RAM)
На одном сервере запускаются оба сервиса в изолированных Docker-контейнерах через общий Nginx Reverse Proxy:

```
                          Внешний трафик (80 / 443)
                                      │
                                      ▼
                        ┌───────────────────────────┐
                        │       Nginx Reverse Proxy │
                        └─────────────┬─────────────┘
                                      │
              ┌───────────────────────┴───────────────────────┐
              │                                               │
              ▼                                               ▼
┌───────────────────────────┐                   ┌───────────────────────────┐
│ CASTLEWEB СТУДИЯ          │                   │ LEADHUNTER PRO            │
│ • apps/frontend (Static)  │                   │ • Контейнер leadhunter    │
│ • apps/backend (Порт 8000)│                   │ • Порт 127.0.0.1:8080     │
│ • Postgres + Redis        │                   │ • Лимит RAM: 1500M        │
│ • castleweb.ru            │                   │ • leads.castleweb.ru      │
└───────────────────────────┘                   └───────────────────────────┘
```

## 2. Лимиты ресурсов Docker
Для защиты основного сайта от нехватки памяти при пиках потребления Playwright/Chromium установлены жесткие лимиты:
* `mem_limit: 1500m`
* `cpus: 1.4`
* Volume-монтирование базы данных и экспортов для сохранности данных при перезапусках контейнеров.

---

# ЧАСТЬ VI. МИГРАЦИЯ FRONTEND НА CASTLEWEB V2, ИНТЕГРАЦИЯ ЛИДОВ И ОЧИСТКА РЕПОЗИТОРИЯ

## 1. Архитектурный контекст Castleweb v2
Новый дизайн сайта (`Castleweb v2`) разработан в соответствии со стандартами `DESIGN_RULES.md`:
* **Эстетика & Дизайн-система:** Темная и светлая палитры (`data-theme`), акроматические фоновые токены, шрифтовой контраст (`Anton`, `Cinzel`, `Inter`, `JetBrains Mono`, `Playfair Display`), Bento-сетка, плавающие сквиркл-бейджи.
* **Интерактивные механики:** Адаптивный веер карточек Hero-секции с 3D-разлетом при скролле, раскрывающиеся кейсы (Onyx OS, Hytte, Skog), блок основателей студии.
* **Юридические стандарты:** Интегрированные страницы политики конфиденциальности (`privacy.html` по 152-ФЗ РФ) и пользовательского соглашения (`terms.html`).

## 2. План выполнения миграции

| Этап | Задача | Файлы / Пути | Статус |
| :--- | :--- | :--- | :---: |
| **1. Архитектура и правила** | Фиксация мастер-плана как Single Source of Truth | `PROJECT_MASTER_PLAN.md` | ✅ Выполнено |
| **2. Чистка устаревшего кода** | Удаление тяжелых неиспользуемых папок и устаревших HTML | `apps/frontend_backup_react/`, `apps/frontend_backup/`, устаревшие `*.html` | ✅ Выполнено |
| **3. Перенос ассетов** | Копирование проектов, карточек, кейсов и команды v2 | `apps/frontend/assets/`, `apps/frontend/public/assets/` | ✅ Выполнено |
| **4. Перенос страниц** | Установка `index.html`, `privacy.html`, `terms.html` | `apps/frontend/` | ✅ Выполнено |
| **5. Интеграция API лидов** | Подключение `#contactForm` к `POST /api/v1/leads` бэкенда | `apps/frontend/index.html` (обработчик отправки + honeypot) | ✅ Выполнено |
| **6. Конфигурация сборки** | Настройка Rollup/Vite multi-page input | `apps/frontend/vite.config.js` | ✅ Выполнено |
| **7. Проверка и тесты** | `npm run build`, валидация endpoint лидов, тесты парсера | `apps/frontend/dist/` (0 errors, 220ms build) | ✅ Выполнено |
| **8. Git релиз** | Коммит по Conventional Commits и push в `origin/main` | Git репозиторий | 🔄 Релиз в процессе |

## 3. Регламент единого плана (Master Plan Invariant)
* **Запрет фрагментации:** Все изменения, фичи, технические долги и результаты тестов документируются исключительно в данном файле (`PROJECT_MASTER_PLAN.md`).
* **Любой новый запрос** пользователя сначала сопоставляется с текущими разделами мастер-плана, после чего в план вносятся отметки о статусе и diff.

---

## 📌 СТАТУС ВЫПОЛНЕНИЯ И СЛЕДУЮЩИЙ ШАГ
* **Блоки 1–4 (Парсер и Безопасность):** ✅ Полностью реализованы, протестированы и синхронизированы.
* **Блок миграции Frontend (Castleweb v2):** ✅ Завершен перенос макета, сборка `dist/` без ошибок, очищены устаревшие бэкапы, форма лидов привязана к FastAPI.
* **Релиз:** Выполняется отправка изменений в Git (`git push origin main`).
