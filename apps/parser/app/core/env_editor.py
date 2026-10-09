import os
from pathlib import Path
from typing import Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / ".env"
ENV_EXAMPLE_PATH = BASE_DIR / ".env.example"

ENV_META = {
    "DEEPSEEK_API_KEY": {
        "title": "API-ключ DeepSeek",
        "desc": "Ключ для генерации питчей и классификации (sk-...)",
        "default": "",
        "secret": True
    },
    "ADMIN_TELEGRAM_IDS": {
        "title": "Telegram ID администраторов",
        "desc": "ID админов через запятую (например: 12345678,87654321)",
        "default": "",
        "secret": False
    },
    "MANAGER_TELEGRAM_CHAT_ID": {
        "title": "Чат менеджеров для P0-лидов",
        "desc": "ID чата/группы для мгновенных алертов о горячих лидах",
        "default": "",
        "secret": False
    },
    "TELEGRAM_BOT_TOKEN": {
        "title": "Токен основного бота (Парсер FL.ru и Карты)",
        "desc": "Токен бота от @BotFather для заказов FL.ru и уведомлений по картам",
        "default": "",
        "secret": True
    },
    "OUTREACH_BOT_TOKEN": {
        "title": "Токен отдельного бота AI SDR (Автоответчик)",
        "desc": "Токен второго бота от @BotFather для управления рассылками и тестов",
        "default": "",
        "secret": True
    },
    "TELEGRAM_API_SERVER": {
        "title": "Реверс-прокси Cloudflare Telegram",
        "desc": "URL Cloudflare Worker для работы без VPN",
        "default": "https://jolly-haze-c6cf.eprof6682-3e3.workers.dev",
        "secret": False
    },
    "TELEGRAM_PROXY": {
        "title": "SOCKS5/HTTP прокси для бота",
        "desc": "Формат: socks5://user:pass@host:port (если нет Cloudflare)",
        "default": "",
        "secret": False
    },
    "OUTREACH_DAILY_LIMIT": {
        "title": "Дневной лимит отправок на аккаунт",
        "desc": "Максимум первых питчей с одного номера в сутки (рек. 15-20)",
        "default": "18",
        "secret": False
    },
    "OUTREACH_WORK_HOURS_START": {
        "title": "Начало рабочих часов рассылки (МСК)",
        "desc": "Час старта активности бота (по умолчанию: 10)",
        "default": "10",
        "secret": False
    },
    "OUTREACH_WORK_HOURS_END": {
        "title": "Конец рабочих часов рассылки (МСК)",
        "desc": "Час окончания активности бота (по умолчанию: 18)",
        "default": "18",
        "secret": False
    },
    "HOST": {
        "title": "Хост API бэкенда",
        "desc": "Сетевой адрес для прослушивания (по умолчанию 0.0.0.0)",
        "default": "0.0.0.0",
        "secret": False
    },
    "PORT": {
        "title": "Порт API бэкенда",
        "desc": "Сетевой порт (по умолчанию 8000)",
        "default": "8000",
        "secret": False
    }
}


def get_all_env_values() -> Dict[str, str]:
    """Считывает все переменные из .env файла"""
    if not ENV_PATH.exists():
        if ENV_EXAMPLE_PATH.exists():
            return parse_env_text(ENV_EXAMPLE_PATH.read_text(encoding="utf-8"))
        return {}
    return parse_env_text(ENV_PATH.read_text(encoding="utf-8"))


def parse_env_text(content: str) -> Dict[str, str]:
    res = {}
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            res[k.strip()] = v.strip().strip("'\"")
    return res


def get_env_value(key: str, default: str = "") -> str:
    """Возвращает значение переменной из .env или os.environ"""
    val = os.environ.get(key)
    if val is not None and val != "":
        return val
    values = get_all_env_values()
    return values.get(key, default)


def set_env_value(key: str, value: str) -> None:
    """
    Безопасно сохраняет или обновляет ключ в файле .env,
    сохраняя комментарии и структуру, а также обновляет os.environ.
    """
    clean_val = str(value).strip()
    os.environ[key] = clean_val

    # Читаем существующий .env или копируем шаблон
    if not ENV_PATH.exists():
        if ENV_EXAMPLE_PATH.exists():
            lines = ENV_EXAMPLE_PATH.read_text(encoding="utf-8").splitlines()
        else:
            lines = []
    else:
        lines = ENV_PATH.read_text(encoding="utf-8").splitlines()

    updated = False
    new_lines = []

    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            k, _ = stripped.split("=", 1)
            if k.strip() == key:
                new_lines.append(f"{key}={clean_val}")
                updated = True
                continue
        new_lines.append(line)

    if not updated:
        new_lines.append(f"{key}={clean_val}")

    ENV_PATH.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
