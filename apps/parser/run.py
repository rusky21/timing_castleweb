import uvicorn
import sys
import asyncio
import subprocess

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass
    if sys.version_info < (3, 14):
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        except Exception:
            pass

def check_playwright():
    """Проверка и доустановка браузера Playwright Chromium при первом запуске"""
    try:
        import playwright
    except ImportError:
        print("[!] Библиотека playwright не установлена. Установите зависимости: pip install -r requirements.txt")

def main():
    import os
    from pathlib import Path
    try:
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).resolve().parent / ".env")
    except Exception:
        pass

    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", 8000))

    print("=" * 60)
    print(" 🚀 LeadHunter & Audit Backend API")
    print("=" * 60)
    print(f" • Сервер запускается на: http://{host}:{port}")
    print(f" • Документация Swagger UI: http://{host}:{port}/docs")
    print(f" • WebSocket поток событий: ws://{host}:{port}/ws/{{campaign_id}}")
    print("=" * 60)

    try:
        uvicorn.run(
            "app.main:app",
            host=host,
            port=port,
            reload=False,
            proxy_headers=True,
            forwarded_allow_ips="*",
            loop="asyncio.windows_events:ProactorEventLoop" if (sys.platform == "win32" and sys.version_info < (3, 14)) else "auto"
        )
    except OSError as e:
        if "10048" in str(e) or "address already in use" in str(e).lower():
            print(f"\n[ОШИБКА] Порт {port} уже занят другим приложением на вашем ПК!")
            print(f"Освободите порт {port} или задайте другой через переменную окружения PORT (например, PORT=8080).")
        else:
            print(f"\n[ОШИБКА СЕТИ] {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[КРИТИЧЕСКАЯ ОШИБКА БЭКЕНДА] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
