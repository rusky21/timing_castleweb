import asyncio
import time
import logging
from typing import Dict, Any, Optional
from sqlalchemy import select

from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter, TelegramForbiddenError

from app.db.database import async_session_factory
from app.db.models import TelegramUser, TelegramUserSettings, FLOrderDelivery, utc_now
from app.services.telegram.formatters import format_fl_order_message, format_lead_message
from app.services.telegram.keyboards import order_inline_keyboard, lead_inline_keyboard, captcha_resolved_keyboard

logger = logging.getLogger("tg_dispatcher")

class TelegramDispatcher:
    """
    Диспетчер доставки уведомлений в Telegram:
    - Очередь с контролем лимитов Telegram API (Rate Limiting)
    - Персональная фильтрация по категориям, стоп-словам, бюджету и тумблеру 'Только с TG'
    - Защита от дублей доставки
    """

    def __init__(self):
        self.bot: Optional[Bot] = None
        self._queue: asyncio.Queue = asyncio.Queue()
        self._worker_task: Optional[asyncio.Task] = None
        self._last_sent_per_chat: Dict[int, float] = {}

    def set_bot(self, bot: Optional[Bot]):
        self.bot = bot
        if self.bot and (not self._worker_task or self._worker_task.done()):
            self._worker_task = asyncio.create_task(self._queue_worker())
            logger.info("TelegramDispatcher queue worker запущен.")

    async def _queue_worker(self):
        """Асинхронный воркер отправки сообщений из очереди с соблюдением задержек"""
        while True:
            try:
                item = await self._queue.get()
                if not self.bot:
                    self._queue.task_done()
                    continue

                chat_id = item[0]
                text = item[1]
                reply_markup = item[2]
                disable_notification = item[3] if len(item) > 3 else False

                # Задержка для конкретного пользователя (не чаще 1 сообщения в 1.1 сек)
                last_time = self._last_sent_per_chat.get(chat_id, 0.0)
                elapsed = time.time() - last_time
                if elapsed < 1.1:
                    await asyncio.sleep(1.1 - elapsed)

                try:
                    for send_attempt in range(2):
                        try:
                            await self.bot.send_message(
                                chat_id=chat_id,
                                text=text,
                                parse_mode="HTML",
                                reply_markup=reply_markup,
                                disable_web_page_preview=True,
                                disable_notification=disable_notification
                            )
                            self._last_sent_per_chat[chat_id] = time.time()
                            break
                        except TelegramRetryAfter as e:
                            logger.warning(f"Telegram Flood limit: пауза {e.retry_after} сек.")
                            await asyncio.sleep(e.retry_after + 0.2)
                        except Exception as net_err:
                            if send_attempt == 1:
                                raise
                            await asyncio.sleep(0.5)

                except TelegramForbiddenError:
                    logger.warning(f"Пользователь {chat_id} заблокировал бота, деактивируем.")
                    await self._deactivate_user(chat_id)
                except Exception as send_err:
                    err_str = str(send_err).lower()
                    if "chat not found" in err_str or "bot was blocked" in err_str:
                        logger.warning(f"Чат с пользователем {chat_id} не найден в текущем боте, деактивируем подписку.")
                        await self._deactivate_user(chat_id)
                    else:
                        logger.error(f"Ошибка отправки в Telegram пользователю {chat_id}: {send_err}")

                self._queue.task_done()
                await asyncio.sleep(0.05)  # Небольшая пауза между разными пользователями

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Ошибка в TelegramDispatcher worker: {e}", exc_info=True)
                await asyncio.sleep(0.5)

    async def _deactivate_user(self, chat_id: int):
        try:
            async with async_session_factory() as db:
                user = await db.get(TelegramUser, chat_id)
                if user:
                    user.is_active = False
                    await db.commit()
        except Exception:
            pass

    async def dispatch_fl_order(self, order):
        """Отправка заказа с FL.ru всем подходящим подписчикам"""
        if not self.bot:
            return

        try:
            async with async_session_factory() as db:
                # Получаем активных пользователей с включенными уведомлениями FL
                stmt = (
                    select(TelegramUserSettings)
                    .join(TelegramUser)
                    .where(TelegramUser.is_active == True)
                    .where(TelegramUserSettings.fl_enabled == True)
                )
                res = await db.execute(stmt)
                subscribers = res.scalars().all()

                for sub in subscribers:
                    chat_id = sub.chat_id

                    # 0. Проверка тумблера Live-режима FL (если отключен — не спамим в реальном времени)
                    if not getattr(sub, "fl_live_mode", True):
                        continue

                    # 1. Проверка категории
                    user_cats = sub.fl_categories or []
                    if user_cats and order.category_id:
                        if str(order.category_id) not in [str(c) for c in user_cats]:
                            continue

                    # 2. Проверка флага "Скрывать PRO"
                    if getattr(sub, "fl_hide_pro", False) and getattr(order, "is_pro_only", False):
                        continue

                    # 3. Проверка флага "Только срочные"
                    if getattr(sub, "fl_urgent_only", False) and not getattr(order, "is_urgent", False):
                        continue

                    # 4. Проверка цены / по договоренности
                    if order.is_negotiable or order.price_rub is None:
                        # Если пользователь выключил "по договоренности", пропускаем
                        if not getattr(sub, "fl_allow_negotiable", True):
                            continue
                    else:
                        # Если есть цена, сверяем с минимальным бюджетом
                        if sub.fl_min_price and order.price_rub < sub.fl_min_price:
                            continue

                    # 5. Проверка белых ключевых слов (если заданы, хотя бы одно должно присутствовать)
                    white_words = [w.strip().lower() for w in (getattr(sub, "fl_keywords", []) or []) if w.strip()]
                    combined_text = f"{order.title} {order.description}".lower()
                    if white_words:
                        if not any(w in combined_text for w in white_words):
                            continue

                    # 6. Проверка минус-слов (стоп-слов)
                    neg_words = [nw.strip().lower() for nw in (sub.fl_negative_words or []) if nw.strip()]
                    if neg_words:
                        if any(nw in combined_text for nw in neg_words):
                            continue

                    # 7. Проверка дедупликации доставки
                    delivery_key = (order.id, chat_id)
                    existing_del = await db.get(FLOrderDelivery, delivery_key)
                    if existing_del and existing_del.is_sent:
                        continue

                    # Формируем сообщение и кнопки
                    msg_text = format_fl_order_message(order)
                    kb = order_inline_keyboard(order_id=order.id, url=order.url, is_favorite=False)
                    disable_notif = not getattr(sub, "notify_sound", True)

                    # Записываем доставку в БД
                    if not existing_del:
                        db.add(FLOrderDelivery(
                            order_id=order.id,
                            chat_id=chat_id,
                            is_sent=True,
                            sent_at=utc_now()
                        ))
                    else:
                        existing_del.is_sent = True
                        existing_del.sent_at = utc_now()

                    await self._queue.put((chat_id, msg_text, kb, disable_notif))

                await db.commit()

        except Exception as e:
            logger.error(f"Ошибка dispatch_fl_order: {e}", exc_info=True)

    async def dispatch_lead(self, lead_dict: Dict[str, Any]):
        """Отправка найденного лида (Яндекс / 2ГИС) подписчикам с учетом персональных фильтров"""
        if not self.bot:
            return

        has_tg = bool(lead_dict.get("telegram"))
        website = lead_dict.get("website") or lead_dict.get("final_url")
        has_site = bool(website)
        status_badge = lead_dict.get("status_badge", "")
        lead_source = (lead_dict.get("source") or "").lower()

        try:
            async with async_session_factory() as db:
                stmt = (
                    select(TelegramUserSettings)
                    .join(TelegramUser)
                    .where(TelegramUser.is_active == True)
                    .where(TelegramUserSettings.maps_enabled == True)
                )
                res = await db.execute(stmt)
                subscribers = res.scalars().all()

                for sub in subscribers:
                    chat_id = sub.chat_id

                    # 1. Фильтр по наличию Telegram
                    if sub.maps_only_with_telegram and not has_tg:
                        continue

                    # 2. Фильтр по источнику (Яндекс / 2ГИС)
                    source_filter = getattr(sub, "maps_source_filter", "all") or "all"
                    if source_filter != "all":
                        if source_filter == "yandex" and "yandex" not in lead_source:
                            continue
                        elif source_filter == "2gis" and "2gis" not in lead_source:
                            continue

                    # 3. Фильтр "Только без сайта"
                    if getattr(sub, "maps_only_without_site", False) and has_site:
                        continue

                    # 4. Фильтр "Только без SSL (HTTP)"
                    if getattr(sub, "maps_only_without_ssl", False) and status_badge != "NO_SSL":
                        continue

                    msg_text = format_lead_message(lead_dict)
                    kb = lead_inline_keyboard(
                        org_id=lead_dict.get("id", 0),
                        telegram=lead_dict.get("telegram"),
                        primary_phone=lead_dict.get("primary_phone"),
                        card_url=lead_dict.get("card_url"),
                        website=website
                    )
                    disable_notif = not getattr(sub, "notify_sound", True)

                    await self._queue.put((chat_id, msg_text, kb, disable_notif))

        except Exception as e:
            logger.error(f"Ошибка dispatch_lead: {e}", exc_info=True)

    async def broadcast_captcha_alert(self, service: str, message: str, campaign_id: int):
        """Оповещение о возникновении капчи во всех чатах с включенными уведомлениями"""
        if not self.bot:
            return

        alert_text = (
            f"⚠️ <b>Внимание! Требуется решение капчи!</b>\n\n"
            f"Сервис: <b>{service.capitalize()}</b>\n"
            f"Сообщение: {message}\n\n"
            f"Пожалуйста, пройдите проверку в открытом окне браузера и нажмите кнопку ниже."
        )
        kb = captcha_resolved_keyboard(campaign_id)

        try:
            async with async_session_factory() as db:
                stmt = (
                    select(TelegramUserSettings)
                    .join(TelegramUser)
                    .where(TelegramUser.is_active == True)
                )
                res = await db.execute(stmt)
                users = res.scalars().all()
                for u in users:
                    if getattr(u, "notify_captcha", True):
                        await self._queue.put((u.chat_id, alert_text, kb, False))
        except Exception as e:
            logger.error(f"Ошибка broadcast_captcha_alert: {e}")

tg_dispatcher = TelegramDispatcher()
