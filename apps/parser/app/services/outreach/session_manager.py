import asyncio
import random
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from urllib.parse import urlparse

import python_socks
from sqlalchemy import select, update
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import (
    FloodWaitError, SessionPasswordNeededError, PhoneCodeInvalidError,
    UserDeactivatedBanError, AuthKeyUnregisteredError
)
from telethon.tl.types import User as TgUser

from app.config import (
    TELEGRAM_API_ID, TELEGRAM_API_HASH, SESSIONS_DIR,
    OUTREACH_DAILY_LIMIT
)
from app.db.database import async_session_factory
from app.db.models import OutreachAccount, OutreachAccountStatus, utc_now

logger = logging.getLogger("session_manager")


def parse_telethon_proxy(proxy_url: Optional[str]) -> Optional[Dict[str, Any]]:
    """Преобразует строку прокси в словарь для Telethon / python-socks"""
    if not proxy_url or not proxy_url.strip():
        return None
    try:
        p = urlparse(proxy_url.strip())
        proxy_type = python_socks.ProxyType.SOCKS5 if "socks5" in p.scheme else python_socks.ProxyType.HTTP
        return {
            "proxy_type": proxy_type,
            "addr": p.hostname,
            "port": p.port or (1080 if "socks" in p.scheme else 8080),
            "username": p.username,
            "password": p.password,
            "rdns": True
        }
    except Exception as e:
        logger.warning(f"Ошибка парсинга прокси {proxy_url}: {e}")
        return None


def get_telethon_device_config() -> dict:
    """Параметры устройства, согласованные с API_ID для защиты от блокировок Telegram"""
    if TELEGRAM_API_ID == 2040:
        return {
            "device_model": "Desktop",
            "system_version": "Windows 11",
            "app_version": "5.5.0",
            "lang_code": "ru",
            "system_lang_code": "ru",
        }
    return {
        "device_model": "PC 64bit",
        "system_version": "Windows 11",
        "app_version": "5.5.0",
        "lang_code": "ru",
        "system_lang_code": "ru",
    }


class SessionManager:
    """
    Централизованный менеджер пула рабочих аккаунтов MTProto (Telethon).
    Обеспечивает ротацию, проверку SpamBot, имитацию набора текста и защиту от банов.
    """

    def __init__(self):
        self.clients: Dict[int, TelegramClient] = {}
        self._login_temp_clients: Dict[str, TelegramClient] = {}
        self._incoming_message_handler = None

    def register_incoming_handler(self, handler):
        """Регистрирует callback-функцию для обработки входящих сообщений диалогов"""
        self._incoming_message_handler = handler

    async def get_client(self, account_id: int) -> Optional[TelegramClient]:
        """Возвращает инициализированный и подключенный клиент Telethon"""
        if account_id in self.clients:
            client = self.clients[account_id]
            if client.is_connected():
                return client

        async with async_session_factory() as session:
            result = await session.execute(
                select(OutreachAccount).where(OutreachAccount.id == account_id)
            )
            account = result.scalar_one_or_none()
            if not account or not account.session_string:
                return None

            return await self._init_client_for_account(account)

    async def _init_client_for_account(self, account: OutreachAccount) -> Optional[TelegramClient]:
        """Инициализирует сессию Telethon для аккаунта из БД"""
        try:
            proxy_str = account.proxy_url
            if not proxy_str:
                import os
                env_p = os.environ.get("TELEGRAM_PROXY") or os.environ.get("HTTPS_PROXY")
                if env_p and "workers.dev" not in env_p:
                    proxy_str = env_p
            proxy = parse_telethon_proxy(proxy_str)
            session_storage = StringSession(account.session_string)
            client = TelegramClient(
                session=session_storage,
                api_id=TELEGRAM_API_ID,
                api_hash=TELEGRAM_API_HASH,
                proxy=proxy,
                **get_telethon_device_config()
            )

            await client.connect()
            if not await client.is_user_authorized():
                logger.error(f"Аккаунт #{account.id} ({account.phone}) не авторизован или разлогинен.")
                account.status = OutreachAccountStatus.DISABLED
                async with async_session_factory() as session:
                    await session.execute(
                        update(OutreachAccount)
                        .where(OutreachAccount.id == account.id)
                        .values(status=OutreachAccountStatus.DISABLED)
                    )
                    await session.commit()
                return None

            # Навешиваем обработчик входящих сообщений
            self._attach_event_handlers(client, account.id)

            self.clients[account.id] = client
            logger.info(f"✅ Рабочий аккаунт #{account.id} ({account.phone}) подключен.")
            return client

        except Exception as e:
            logger.error(f"Не удалось запустить MTProto сессию для аккаунта #{account.id}: {e}")
            return None

    def _attach_event_handlers(self, client: TelegramClient, account_id: int):
        """Прикрепляет слушатель входящих сообщений к Telethon клиенту"""
        @client.on(events.NewMessage(incoming=True))
        async def on_new_incoming(event):
            # Игнорируем сервисные чаты Telegram и системные уведомления
            if event.is_private and event.sender_id != 777000:
                if self._incoming_message_handler:
                    try:
                        await self._incoming_message_handler(account_id, event)
                    except Exception as err:
                        logger.error(f"Ошибка в обработчике входящего сообщения: {err}", exc_info=True)

    async def start_all_active_accounts(self):
        """Запускает все активные аккаунты из базы данных"""
        async with async_session_factory() as session:
            result = await session.execute(
                select(OutreachAccount).where(
                    OutreachAccount.status.in_([
                        OutreachAccountStatus.ACTIVE,
                        OutreachAccountStatus.WARMUP
                    ])
                )
            )
            accounts = result.scalars().all()
            for acc in accounts:
                if acc.session_string:
                    await self._init_client_for_account(acc)

    async def pick_best_account(self) -> Optional[OutreachAccount]:
        """
        Выбирает оптимальный рабочий аккаунт для следующего питча:
        - Статус ACTIVE
        - Не превышен суточный лимит
        - Максимальное время с момента последней отправки
        """
        async with async_session_factory() as session:
            result = await session.execute(
                select(OutreachAccount)
                .where(
                    OutreachAccount.status == OutreachAccountStatus.ACTIVE,
                    OutreachAccount.sent_today < OutreachAccount.daily_limit
                )
                .order_by(OutreachAccount.last_sent_at.asc().nullsfirst())
            )
            return result.scalars().first()

    async def send_message_safe(
        self,
        account_id: int,
        recipient: str | int,
        text: str,
        reply_to_msg_id: Optional[int] = None,
        simulate_typing: bool = True
    ) -> Optional[int]:
        """
        Безопасная отправка сообщения с имитацией набора текста человеком и задержкой.
        Возвращает ID отправленного сообщения Telegram или None при ошибке.
        """
        client = await self.get_client(account_id)
        if not client:
            raise RuntimeError(f"Аккаунт #{account_id} недоступен")

        try:
            # Имитация человеческого набора текста (1-4 секунды в зависимости от длины)
            if simulate_typing:
                async with client.action(recipient, 'typing'):
                    type_delay = min(max(len(text) * 0.04, 1.5), 5.0) + random.uniform(0.5, 1.5)
                    await asyncio.sleep(type_delay)

            msg = await client.send_message(
                recipient,
                text,
                reply_to=reply_to_msg_id,
                link_preview=False
            )

            # Обновление счетчиков в БД
            async with async_session_factory() as session:
                await session.execute(
                    update(OutreachAccount)
                    .where(OutreachAccount.id == account_id)
                    .values(
                        sent_today=OutreachAccount.sent_today + 1,
                        last_sent_at=utc_now()
                    )
                )
                await session.commit()

            return msg.id

        except FloodWaitError as e:
            logger.warning(f"Telegram FloodWait на аккаунте #{account_id}: пауза {e.seconds}с")
            async with async_session_factory() as session:
                await session.execute(
                    update(OutreachAccount)
                    .where(OutreachAccount.id == account_id)
                    .values(status=OutreachAccountStatus.COOLDOWN)
                )
                await session.commit()
            raise

        except (UserDeactivatedBanError, AuthKeyUnregisteredError) as ban_err:
            logger.error(f"🚨 Аккаунт #{account_id} заблокирован Telegram: {ban_err}")
            async with async_session_factory() as session:
                await session.execute(
                    update(OutreachAccount)
                    .where(OutreachAccount.id == account_id)
                    .values(status=OutreachAccountStatus.SPAMBLOCKED)
                )
                await session.commit()
            raise

        except Exception as e:
            logger.error(f"Сбой отправки сообщения через аккаунт #{account_id} получателю {recipient}: {e}")
            raise

    async def send_photo_safe(
        self,
        account_id: int,
        recipient: str | int,
        photo_path: str,
        caption: Optional[str] = None
    ) -> Optional[int]:
        """Безопасная отправка фото/скриншота с аккаунта"""
        client = await self.get_client(account_id)
        if not client:
            raise RuntimeError(f"Аккаунт #{account_id} недоступен")

        file_obj = Path(photo_path)
        if not file_obj.exists():
            raise FileNotFoundError(f"Файл скриншота не найден: {photo_path}")

        try:
            async with client.action(recipient, 'photo'):
                await asyncio.sleep(random.uniform(1.2, 2.5))

            msg = await client.send_file(
                recipient,
                file=str(file_obj),
                caption=caption,
                link_preview=False
            )
            return msg.id
        except Exception as e:
            logger.error(f"Сбой отправки скриншота через аккаунт #{account_id}: {e}")
            raise

    async def check_spambot(self, account_id: int) -> Dict[str, Any]:
        """
        Отправляет команду /start в официальный @SpamBot и проверяет статус ограничений.
        """
        client = await self.get_client(account_id)
        if not client:
            return {"ok": False, "status": "CLIENT_NOT_AVAILABLE", "message": "Сессия не подключена"}

        try:
            await client.send_message("@SpamBot", "/start")
            await asyncio.sleep(2.5)

            # Получаем последнее входящее сообщение от SpamBot
            messages = await client.get_messages("@SpamBot", limit=3)
            reply_text = ""
            for m in messages:
                if not m.out:
                    reply_text = m.message or ""
                    break

            is_clean = any(phrase in reply_text.lower() for phrase in [
                "свободен", "никаких ограничений", "good news", "free of any limits", "no limits"
            ])

            now = utc_now()
            new_status = OutreachAccountStatus.ACTIVE if is_clean else OutreachAccountStatus.SPAMBLOCKED

            async with async_session_factory() as session:
                await session.execute(
                    update(OutreachAccount)
                    .where(OutreachAccount.id == account_id)
                    .values(
                        spambot_checked_at=now,
                        status=new_status
                    )
                )
                await session.commit()

            return {
                "ok": True,
                "is_clean": is_clean,
                "status": new_status,
                "bot_reply": reply_text
            }

        except Exception as e:
            logger.error(f"Сбой проверки @SpamBot для аккаунта #{account_id}: {e}")
            return {"ok": False, "status": "ERROR", "message": str(e)}

    # ====================================================================
    # FSM Вспомогательные методы добавления аккаунта (Авторизация по SMS/2FA)
    # ====================================================================

    async def request_login_code(self, phone: str, proxy_url: Optional[str] = None) -> Tuple[bool, str, str]:
        """
        Шаг 1 добавления аккаунта: Отправка кода подтверждения в Telegram.
        Возвращает (success, phone_code_hash_или_error, phone)
        """
        clean_phone = phone.strip().replace(" ", "").replace("-", "")
        if not clean_phone.startswith("+"):
            clean_phone = f"+{clean_phone}"

        if not proxy_url:
            import os
            env_p = os.environ.get("TELEGRAM_PROXY") or os.environ.get("HTTPS_PROXY")
            if env_p and "workers.dev" not in env_p:
                proxy_url = env_p
        proxy = parse_telethon_proxy(proxy_url)
        temp_session = StringSession()
        client = TelegramClient(
            session=temp_session,
            api_id=TELEGRAM_API_ID,
            api_hash=TELEGRAM_API_HASH,
            proxy=proxy,
            timeout=15,
            connection_retries=3,
            **get_telethon_device_config()
        )

        try:
            await client.connect()
            sent_code = await client.send_code_request(clean_phone)
            self._login_temp_clients[clean_phone] = client
            return True, sent_code.phone_code_hash, clean_phone
        except Exception as e:
            await client.disconnect()
            return False, str(e), clean_phone

    async def complete_login_with_code(
        self,
        phone: str,
        code: str,
        phone_code_hash: str,
        password_2fa: Optional[str] = None,
        proxy_url: Optional[str] = None
    ) -> Tuple[bool, str, Optional[int]]:
        """
        Шаг 2 добавления аккаунта: Ввод кода из Telegram и сохранение сессии в базу.
        """
        client = self._login_temp_clients.get(phone)
        if not client or not client.is_connected():
            return False, "Сессия авторизации истекла. Начните сначала с /account_add", None

        try:
            try:
                await client.sign_in(phone=phone, code=code.strip(), phone_code_hash=phone_code_hash)
            except SessionPasswordNeededError:
                if not password_2fa:
                    return False, "NEEDS_2FA", None
                await client.sign_in(password=password_2fa.strip())

            session_str = client.session.save()
            me = await client.get_me()
            is_premium = getattr(me, "premium", False) or False

            # Сохранение аккаунта в SQLite БД
            async with async_session_factory() as session:
                # Проверяем, существует ли уже
                res = await session.execute(select(OutreachAccount).where(OutreachAccount.phone == phone))
                acc = res.scalar_one_or_none()
                if acc:
                    acc.session_string = session_str
                    acc.proxy_url = proxy_url
                    acc.status = OutreachAccountStatus.ACTIVE
                    acc.is_premium = is_premium
                else:
                    acc = OutreachAccount(
                        phone=phone,
                        session_string=session_str,
                        proxy_url=proxy_url,
                        status=OutreachAccountStatus.ACTIVE,
                        is_premium=is_premium,
                        daily_limit=OUTREACH_DAILY_LIMIT,
                        sent_today=0,
                        warmup_stage=1
                    )
                    session.add(acc)
                await session.commit()
                await session.refresh(acc)
                account_id = acc.id

            # Перемещаем клиент в боевой словарь
            self.clients[account_id] = client
            self._attach_event_handlers(client, account_id)
            self._login_temp_clients.pop(phone, None)

            return True, "Авторизация успешно завершена!", account_id

        except PhoneCodeInvalidError:
            return False, "Неверный код подтверждения. Попробуйте еще раз.", None
        except Exception as e:
            return False, f"Ошибка входа: {e}", None

    async def reset_daily_limits(self):
        """Сброс дневных лимитов всех аккаунтов (вызывается в полночь)"""
        async with async_session_factory() as session:
            await session.execute(
                update(OutreachAccount).values(sent_today=0)
            )
            await session.commit()
            logger.info("🔄 Дневные счетчики рассылок всех аккаунтов обнулены.")

    async def disconnect_all(self):
        """Корректное отключение всех Telethon сессий при завершении работы"""
        for acc_id, client in list(self.clients.items()):
            try:
                if client.is_connected():
                    await client.disconnect()
            except Exception:
                pass
        self.clients.clear()


session_manager = SessionManager()
