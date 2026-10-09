# ======================================================================
# LeadHunter Pro — Production Container with Pre-installed Playwright
# ======================================================================
FROM mcr.microsoft.com/playwright/python:v1.49.0-noble

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HEADLESS=1 \
    PORT=8000

# Копируем список зависимостей
COPY requirements.txt .

# Установка зависимостей Python
RUN pip install --no-cache-dir -r requirements.txt

# Установка браузера Chromium для Playwright
RUN playwright install chromium

# Копируем исходный код бэкенда и собранный фронтенд
COPY . .

# Создаем папки для базы данных, экспорта и профиля браузера
RUN mkdir -p data exports browser_profile

EXPOSE 8000

CMD ["python", "run.py"]
