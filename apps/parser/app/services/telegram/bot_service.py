import os
import asyncio
import logging
from typing import Optional
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode

from app.services.telegram.handlers import router
from app.services.telegram.dispatcher import tg_dispatcher

logger = logging.getLogger("tg_bot_service")

class TelegramBotService:
    """Управление жизненным циклом Telegram-бота (старт, стоп, поллинг)"""

    def __init__(self):
        self.token: Optional[str] = None
        self.bot: Optional[Bot] = None
        self.dp: Optional[Dispatcher] = None
        self._polling_task: Optional[asyncio.Task] = None
        self._is_running: bool = False

    @property
    def is_running(self) -> bool:
        return self._is_running

    def load_token(self) -> Optional[str]:
        try:
            from app.config import TELEGRAM_BOT_TOKEN
            if TELEGRAM_BOT_TOKEN:
                return TELEGRAM_BOT_TOKEN.strip()
        except Exception:
            pass
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except Exception:
            pass
        token = os.environ.get("TELEGRAM_BOT_TOKEN") or os.environ.get("TG_BOT_TOKEN")
        if token:
            token = token.strip()
        return token

    async def start(self):
        self.token = self.load_token()
        if not self.token:
            logger.info("ℹ️ TELEGRAM_BOT_TOKEN не задан. Бот ожидает настройки токена.")
            return

        api_server_url = (os.environ.get("TELEGRAM_API_SERVER") or os.environ.get("TELEGRAM_CUSTOM_SERVER") or "").strip()
        raw_proxy = (os.environ.get("TELEGRAM_PROXY") or "").strip()
        if raw_proxy and "workers.dev" in raw_proxy and not api_server_url:
            api_server_url = raw_proxy

        proxy = None
        if raw_proxy:
            # Если в TELEGRAM_PROXY ошибочно вставили адрес Cloudflare Worker — игнорируем
            if not (api_server_url and raw_proxy.rstrip("/") == api_server_url.rstrip("/")):
                raw_p = raw_proxy
                if raw_p.startswith("https://"):
                    raw_p = "http://" + raw_p[8:]
                if any(raw_p.startswith(pref) for pref in ("socks5://", "socks4://", "http://")):
                    proxy = raw_p
        elif not api_server_url:
            sys_proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY")
            if sys_proxy and not sys_proxy.startswith("https://"):
                proxy = sys_proxy.strip()

        
        try:
            from aiohttp import ClientOSError, ServerDisconnectedError
            from aiogram.client.session.aiohttp import AiohttpSession
            from aiogram.client.telegram import TelegramAPIServer
            from aiogram.exceptions import TelegramNetworkError, TelegramRetryAfter
            
            class ResilientAiohttpSession(AiohttpSession):
                """Отказоустойчивая сессия Telegram с автоповтором при сетевых разрывах Cloudflare (WinError 64)"""
                def __init__(self, *args, **kwargs):
                    kwargs.pop("keepalive_timeout", None)
                    super().__init__(*args, **kwargs)
                    self._connector_init["keepalive_timeout"] = 10
                    self._connector_init["enable_cleanup_closed"] = True

                async def make_request(self, bot, method, timeout=None):
                    max_retries = 3
                    for attempt in range(1, max_retries + 1):
                        try:
                            return await super().make_request(bot, method, timeout=timeout)
                        except TelegramRetryAfter as e:
                            logger.warning(f"Telegram flood wait: {e.retry_after}s...")
                            await asyncio.sleep(e.retry_after + 0.2)
                        except (TelegramNetworkError, ClientOSError, ServerDisconnectedError, asyncio.TimeoutError, ConnectionResetError, OSError) as e:
                            self._should_reset_connector = True
                            if self._session and not self._session.closed:
                                try:
                                    await self.close()
                                except Exception:
                                    pass
                            if attempt == max_retries:
                                logger.error(f"Не удалось выполнить {method} после {max_retries} попыток: {e}")
                                raise
                            wait_time = 0.4 * attempt
                            logger.warning(f"Сетевой обрыв соединения Cloudflare ({e}), сброс сокета и повтор {attempt}/{max_retries} через {wait_time:.1f}с...")
                            await asyncio.sleep(wait_time)

            api_server = TelegramAPIServer.from_base(api_server_url.rstrip("/")) if api_server_url else None
            session = ResilientAiohttpSession(
                proxy=proxy,
                api=api_server or TelegramAPIServer.from_base("https://api.telegram.org")
            )
            self.bot = Bot(token=self.token, session=session)
            self.dp = Dispatcher()
            self.dp.include_router(router)

            # Передаем бота в диспетчер доставки
            tg_dispatcher.set_bot(self.bot)

            # Проверяем связь с Telegram API с защитой от холодных стартов Cloudflare
            me = None
            for get_me_attempt in range(1, 4):
                try:
                    me = await asyncio.wait_for(self.bot.get_me(), timeout=35.0)
                    break
                except (asyncio.TimeoutError, Exception) as e:
                    if get_me_attempt == 3:
                        raise
                    logger.info(f"Холодный старт Cloudflare ({e}), повторная попытка {get_me_attempt}/3 через {2.0 * get_me_attempt}с...")
                    await asyncio.sleep(2.0 * get_me_attempt)

            self._is_running = True
            self._polling_task = asyncio.create_task(self._run_polling())
            logger.info(f"✅ Telegram-бот успешно запущен: @{me.username} ({me.full_name})")

        except (asyncio.TimeoutError, Exception) as e:
            err_str = str(e) or type(e).__name__
            logger.warning(
                f"⚠️ Серверы Telegram API недоступны с текущего интернет-соединения ({err_str}).\n"
                f"   Если api.telegram.org блокируется провайдером, включите VPN или задайте TELEGRAM_PROXY=http://... в .env\n"
                f"   Приложение, парсинг FL.ru и десктоп работают в штатном режиме."
            )
            if self.bot and self.bot.session:
                await self.bot.session.close()

    async def _run_polling(self):
        """Отказоустойчивый цикл поллинга с авто-возобновлением при сбоях"""
        while self._is_running:
            try:
                await self.dp.start_polling(self.bot, skip_updates=False)
            except asyncio.CancelledError:
                break
            except Exception as e:
                if not self._is_running:
                    break
                logger.error(f"Сетевой сбой в цикле опроса Telegram ({e}). Перезапуск polling через 2с...", exc_info=True)
                await asyncio.sleep(2)

    async def stop(self):
        self._is_running = False
        if self._polling_task and not self._polling_task.done():
            self._polling_task.cancel()

        if self.dp:
            try:
                await self.dp.stop_polling()
            except Exception:
                pass

        if self.bot and self.bot.session:
            try:
                await self.bot.session.close()
            except Exception:
                pass

        logger.info("Telegram-бот остановлен.")

tg_bot_service = TelegramBotService()
