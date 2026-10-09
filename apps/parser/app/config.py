import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Директория для данных и БД (папка data/ для Docker или локального запуска)
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# База данных SQLite: поддержка data/leadhunter.db и обратная совместимость с leadhunter.db
if (DATA_DIR / "leadhunter.db").exists():
    DB_PATH = (DATA_DIR / "leadhunter.db").resolve()
elif (BASE_DIR / "leadhunter.db").is_file():
    DB_PATH = (BASE_DIR / "leadhunter.db").resolve()
else:
    DB_PATH = (DATA_DIR / "leadhunter.db").resolve()

DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH.as_posix()}"

# Директория для профилей браузера и экспорта
EXPORTS_DIR = BASE_DIR / "exports"
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

BROWSER_DATA_DIR = BASE_DIR / "browser_profile"
BROWSER_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Настройки парсинга и аудита
DEFAULT_TIMEOUT_CONNECT = 5.0
DEFAULT_TIMEOUT_READ = 7.0
MAX_AUDIT_WORKERS = 8
CAPTCHA_TIMEOUT_SECONDS = 180  # 3 минуты ожидания ручного прохождения капчи

# Режим headless для браузера Playwright (автоматически True для Linux без GUI и серверов/Docker)
import sys
HEADLESS = os.environ.get("HEADLESS", "").lower() in ("true", "1")
if sys.platform != "win32" and not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
    HEADLESS = True

# Директории для скриншотов дефектов и MTProto сессий
SCREENSHOTS_DIR = DATA_DIR / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

SESSIONS_DIR = DATA_DIR / "sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

# DeepSeek API Configuration
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "").strip()
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com").strip().rstrip("/")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat").strip()

# Токены ботов Telegram (Основной бот парсера и отдельный бот AI SDR)
TELEGRAM_BOT_TOKEN = (os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()
OUTREACH_BOT_TOKEN = (os.environ.get("OUTREACH_BOT_TOKEN") or "").strip()

# Telegram Admin & Manager Configuration

def get_admin_ids() -> set[int]:
    raw = os.environ.get("ADMIN_TELEGRAM_IDS", "").strip()
    ids = set()
    if raw:
        for part in raw.split(","):
            part = part.strip()
            if part.lstrip("-").isdigit():
                ids.add(int(part))
    return ids

ADMIN_TELEGRAM_IDS = get_admin_ids()

_mgr_chat = os.environ.get("MANAGER_TELEGRAM_CHAT_ID", "").strip()
MANAGER_TELEGRAM_CHAT_ID = int(_mgr_chat) if _mgr_chat.lstrip("-").isdigit() else None

# MTProto Telegram Client Credentials (API ID & Hash from my.telegram.org)
_tg_api_id = os.environ.get("TELEGRAM_API_ID", "").strip()
TELEGRAM_API_ID = int(_tg_api_id) if _tg_api_id.isdigit() else 2040  # Default official ID if not provided
TELEGRAM_API_HASH = os.environ.get("TELEGRAM_API_HASH", "b18441a1ff607e10a989891a5462e627").strip()

# Настройки рассылки и безопасности (Anti-Spam & Limits)
OUTREACH_COMPANY_NAME = "CastleWeb"
OUTREACH_DAILY_LIMIT = int(os.environ.get("OUTREACH_DAILY_LIMIT", "18"))
OUTREACH_MIN_DELAY_SECONDS = int(os.environ.get("OUTREACH_MIN_DELAY_SECONDS", "300"))
OUTREACH_MAX_DELAY_SECONDS = int(os.environ.get("OUTREACH_MAX_DELAY_SECONDS", "900"))
OUTREACH_WORK_HOURS_START = int(os.environ.get("OUTREACH_WORK_HOURS_START", "10"))
OUTREACH_WORK_HOURS_END = int(os.environ.get("OUTREACH_WORK_HOURS_END", "18"))


