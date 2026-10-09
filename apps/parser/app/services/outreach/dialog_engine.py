import asyncio
import logging
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime, timezone
from sqlalchemy import select, update

from app.db.database import async_session_factory
from app.db.models import (
    OutreachDialog, OutreachMessage, OutreachBlacklist,
    DialogStatus, OutreachAccount, Organization, utc_now
)
from app.services.outreach.session_manager import session_manager
from app.services.outreach.intent_classifier import intent_classifier
from app.services.deepseek.client import deepseek_client
from app.services.outreach.prompts import get_prompt, DEFAULT_DIALOG_REPLY_PROMPT

logger = logging.getLogger("dialog_engine")


class DialogEngine:
    """
    Интеллектуальный мультимодальный диалоговый движок.
    Управляет жизненным циклом диалогов, классификацией, передачей человеку (Human Takeover)
    и автоответами с позиционированием CastleWeb.
    """

    def __init__(self):
        self._admin_mirror_callbacks: List[Callable] = []
        self._manager_alert_callback: Optional[Callable] = None
        # Связываем с менеджером сессий
        session_manager.register_incoming_handler(self.handle_incoming_event)

    def register_admin_mirror(self, callback: Callable):
        """Регистрирует callback для live-зеркалирования переписки в Admin Bot"""
        self._admin_mirror_callbacks.append(callback)

    def register_manager_alert(self, callback: Callable):
        """Регистрирует callback для P0-алертов менеджерам о горячих лидах"""
        self._manager_alert_callback = callback

    async def _notify_admin_mirror(self, dialog: OutreachDialog, incoming_text: str, intent_info: Dict[str, Any], bot_reply: Optional[str] = None):
        """Отправляет live-уведомление администраторам"""
        for cb in self._admin_mirror_callbacks:
            try:
                await cb(dialog, incoming_text, intent_info, bot_reply)
            except Exception as e:
                logger.debug(f"Ошибка вызова admin mirror callback: {e}")

    async def _notify_manager_p0(self, dialog: OutreachDialog, incoming_text: str, intent_info: Dict[str, Any]):
        """Эскалация P0: Горячий лид передан человеку"""
        if self._manager_alert_callback:
            try:
                await self._manager_alert_callback(dialog, incoming_text, intent_info)
            except Exception as e:
                logger.error(f"Ошибка отправки P0-алерта менеджеру: {e}")

    async def handle_incoming_event(self, account_id: int, event):
        """
        Главный обработчик входящего сообщения от Telethon-клиента.
        """
        sender = await event.get_sender()
        if not sender:
            return

        sender_id = getattr(sender, "id", None)
        sender_username = getattr(sender, "username", None)
        sender_phone = getattr(sender, "phone", None)
        incoming_text = (event.message.message or "").strip()
        tg_msg_id = event.message.id

        if not incoming_text:
            return

        logger.info(f"📨 Входящее сообщение от {sender_username or sender_id}: «{incoming_text[:60]}...»")

        async with async_session_factory() as session:
            # 1. Проверка черного списка
            identifiers = []
            if sender_username:
                identifiers.append(f"@{sender_username.lower()}")
            if sender_phone:
                identifiers.append(sender_phone)
            if sender_id:
                identifiers.append(str(sender_id))

            bl_check = await session.execute(
                select(OutreachBlacklist).where(OutreachBlacklist.identifier.in_(identifiers))
            )
            if bl_check.scalar_one_or_none():
                logger.info(f"Контакт {sender_username or sender_id} находится в Blacklist. Игнорируем.")
                return

            # 2. Поиск существующего диалога
            query = select(OutreachDialog).where(
                (OutreachDialog.client_tg_id == sender_id) |
                (OutreachDialog.client_tg_username == sender_username)
            ).order_by(OutreachDialog.id.desc())

            res = await session.execute(query)
            dialog = res.scalar_one_or_none()

            # Если диалог не найден — создаем новый (входящий контакт)
            if not dialog:
                dialog = OutreachDialog(
                    account_id=account_id,
                    client_tg_id=sender_id,
                    client_tg_username=sender_username,
                    client_phone=sender_phone,
                    status=DialogStatus.REPLIED,
                    pitch_text="[Входящий диалог]",
                    is_test=False
                )
                session.add(dialog)
                await session.commit()
                await session.refresh(dialog)

            # 3. Фиксация входящего сообщения в БД
            msg_obj = OutreachMessage(
                dialog_id=dialog.id,
                sender_type="client",
                message_text=incoming_text,
                tg_message_id=tg_msg_id
            )
            session.add(msg_obj)
            dialog.last_client_reply_at = utc_now()
            dialog.status = DialogStatus.REPLIED
            await session.commit()

            # 4. Если ИИ заблокирован (диалог ведет живой менеджер) — НЕ ОТВЕЧАЕМ АВТОМАТОМ!
            if dialog.ai_locked:
                logger.info(f"Диалог #{dialog.id} заблокирован для ИИ (ведется человеком). Пропускаем автоответ.")
                await self._notify_admin_mirror(dialog, incoming_text, {"intent": "HUMAN_CONTROLLED", "requires_human": True}, None)
                return

            # 5. Загрузка истории диалога для классификатора
            history_res = await session.execute(
                select(OutreachMessage).where(OutreachMessage.dialog_id == dialog.id).order_by(OutreachMessage.sent_at.asc())
            )
            all_messages = history_res.scalars().all()
            dialog_history = [
                {"sender": m.sender_type, "text": m.message_text}
                for m in all_messages
            ]

            # 6. Классификация намерения (Intent Classification)
            classification = await intent_classifier.classify(incoming_text, dialog_history, session)
            intent = classification.get("intent", "OTHER_CONVERSATION")
            confidence = classification.get("confidence", 0.8)
            requires_human = classification.get("requires_human", False)

            dialog.last_intent = intent
            dialog.intent_confidence = confidence

            # 7. Обработка по сценариям матрицы поведения:

            # Сценарий SC-01 / P0: Прямой интерес, готовность, цена, телефон оставлен
            if requires_human or intent == "INTERESTED":
                dialog.ai_locked = True
                dialog.status = DialogStatus.NEEDS_HUMAN
                await session.commit()

                logger.info(f"🔥 [P0] Лид проявил интерес в диалоге #{dialog.id}! Передаем человеку.")
                await self._notify_manager_p0(dialog, incoming_text, classification)
                await self._notify_admin_mirror(dialog, incoming_text, classification, None)
                return

            # Сценарий SC-10: Жесткий отказ / Негатив / Требование удалить
            if intent == "REJECT_HARD":
                dialog.ai_locked = True
                dialog.status = DialogStatus.CLOSED_REJECTED
                # Добавление в стоп-лист
                block_id = f"@{sender_username.lower()}" if sender_username else str(sender_id)
                session.add(OutreachBlacklist(identifier=block_id, reason="Жесткий отказ / спам"))
                await session.commit()

                farewell_text = "Понял вас, извините за беспокойство. Больше не потревожу."
                try:
                    bot_msg_id = await session_manager.send_message_safe(
                        account_id=dialog.account_id or account_id,
                        recipient=dialog.client_tg_username or dialog.client_tg_id,
                        text=farewell_text,
                        reply_to_msg_id=tg_msg_id
                    )
                    session.add(OutreachMessage(
                        dialog_id=dialog.id,
                        sender_type="bot",
                        message_text=farewell_text,
                        tg_message_id=bot_msg_id
                    ))
                    await session.commit()
                except Exception as e:
                    logger.warning(f"Не удалось отправить прощальное сообщение: {e}")

                await self._notify_admin_mirror(dialog, incoming_text, classification, farewell_text)
                return

            # Сценарий SC-02: Запрос пруфа / скриншота
            bot_reply = ""
            if intent == "REQUEST_PROOF":
                if dialog.defect_screenshot_path:
                    try:
                        await session_manager.send_photo_safe(
                            account_id=dialog.account_id or account_id,
                            recipient=dialog.client_tg_username or dialog.client_tg_id,
                            photo_path=dialog.defect_screenshot_path,
                            caption="Вот, с телефона открывал — выделил проблемное место."
                        )
                        bot_reply = "Вот, с телефона открывал — выделил проблемное место. Заметно как перекрывается?"
                        # Мягкое прояснение
                        await asyncio.sleep(1.5)
                        bot_msg_id = await session_manager.send_message_safe(
                            account_id=dialog.account_id or account_id,
                            recipient=dialog.client_tg_username or dialog.client_tg_id,
                            text="Сайтом сейчас кто-то занимается, или помочь поправить верстку?"
                        )
                        dialog.status = DialogStatus.QUALIFYING
                        session.add(OutreachMessage(
                            dialog_id=dialog.id,
                            sender_type="bot",
                            message_text=bot_reply,
                            tg_message_id=bot_msg_id
                        ))
                        await session.commit()
                        await self._notify_admin_mirror(dialog, incoming_text, classification, bot_reply)
                        return
                    except Exception as e:
                        logger.warning(f"Не удалось отправить заготовленный скриншот: {e}")

            # Сценарий SC-12: Тест Тьюринга («Ты бот?»)
            if intent == "IS_BOT":
                bot_reply = "Да не, руками пишу) Я разработчик из CastleWeb, сайты делаем. Просто с телефона на сайт зашел и увидел косяк в верстке"

            # Сценарий SC-03: Идентификация («Вы кто?»)
            elif intent == "QUESTION_IDENTITY":
                bot_reply = "Я разработчик из CastleWeb (занимаемся разработкой и доработкой сайтов). Зашел к вам с телефона и заметил, что форма заявки съехала, решил написать"

            # Сценарий SC-04: «Откуда номер?»
            elif intent == "QUESTION_SOURCE":
                bot_reply = "Искал контакты на Яндекс.Картах / 2ГИС в карточке вашей компании."

            # Сценарий SC-05: «У нас свой программист»
            elif intent == "OBJECTION_DEV":
                bot_reply = "Отлично! Передайте ему скриншот/описание — пусть поправит форму, а то с мобилок клиенты отваливаются. Денег не нужно, просто хотел помочь."

            # Сценарий SC-06: Скепсис («У нас все работает»)
            elif intent == "SKEPTIC":
                bot_reply = "На компьютере всё отлично. Ошибка вылезает именно на экранах смартфонов шириной до 390px (iPhone/Android). Прислать скриншот с телефона?"

            # Сценарий SC-07: «Скиньте на почту»
            elif intent == "SEND_EMAIL":
                bot_reply = "Шаблонов КП не держу, задача точечная на 1–2 часа работы. Давайте пришлю скриншот сюда или кратко созвонимся на 3 минуты?"

            # Иные сценарии — контекстная генерация DeepSeek с правилами CastleWeb
            else:
                recommended = classification.get("recommended_response")
                if recommended and len(recommended.strip()) > 5:
                    bot_reply = recommended.strip()
                elif deepseek_client.is_configured():
                    try:
                        reply_prompt_tpl = await get_prompt("DIALOG_REPLY", session) or DEFAULT_DIALOG_REPLY_PROMPT
                        prompt = reply_prompt_tpl
                        for ph, val in (
                            ("{company_name}", dialog.company_name or "вашей компании"),
                            ("{website_url}", dialog.website_url or "вашем сайте"),
                            ("{dialog_history}", formatted_history_text(dialog_history)),
                            ("{intent}", intent),
                            ("{incoming_message}", incoming_text),
                        ):
                            prompt = prompt.replace(ph, str(val))
                        messages = [{"role": "user", "content": prompt}]
                        bot_reply = await deepseek_client.chat_completion(messages, temperature=0.3, max_tokens=150)
                    except Exception:
                        bot_reply = "Подсказать детальнее по ошибке или скинуть скриншот с экрана смартфона?"
                else:
                    bot_reply = "Подсказать детальнее по ошибке или скинуть скриншот с экрана смартфона?"

            # Отправка сформированного ответа
            if bot_reply:
                dialog.status = DialogStatus.QUALIFYING
                try:
                    bot_msg_id = await session_manager.send_message_safe(
                        account_id=dialog.account_id or account_id,
                        recipient=dialog.client_tg_username or dialog.client_tg_id,
                        text=bot_reply,
                        reply_to_msg_id=tg_msg_id
                    )
                    session.add(OutreachMessage(
                        dialog_id=dialog.id,
                        sender_type="bot",
                        message_text=bot_reply,
                        tg_message_id=bot_msg_id
                    ))
                    await session.commit()
                except Exception as e:
                    logger.error(f"Не удалось отправить автоответ в диалог #{dialog.id}: {e}")

            await self._notify_admin_mirror(dialog, incoming_text, classification, bot_reply)

    async def process_simulated_reply(self, dialog_id: int, incoming_text: str) -> Dict[str, Any]:
        """
        Интерактивная симуляция ответа клиента:
        - Добавляет входящее сообщение от клиента в БД
        - Вызывает DeepSeek Intent Classifier
        - Формирует ответ CastleWeb или инициирует P0 эскалацию
        - Отправляет уведомления в Admin Mirror и чат менеджеров
        - Возвращает результат для мгновенного отображения в интерфейсе
        """
        async with async_session_factory() as session:
            dialog = (await session.execute(
                select(OutreachDialog).where(OutreachDialog.id == dialog_id)
            )).scalar_one_or_none()

            if not dialog:
                return {"ok": False, "error": f"Диалог #{dialog_id} не найден"}

            # 1. Фиксация входящего сообщения клиента
            msg_obj = OutreachMessage(
                dialog_id=dialog.id,
                sender_type="client",
                message_text=incoming_text,
                tg_message_id=None
            )
            session.add(msg_obj)
            dialog.last_client_reply_at = utc_now()
            dialog.status = DialogStatus.REPLIED
            await session.commit()

            # 2. Если диалог уже под контролем человека
            if dialog.ai_locked:
                await self._notify_admin_mirror(dialog, incoming_text, {"intent": "HUMAN_CONTROLLED", "requires_human": True}, None)
                return {
                    "ok": True,
                    "intent": "HUMAN_CONTROLLED",
                    "confidence": 1.0,
                    "requires_human": True,
                    "bot_reply": None,
                    "status": dialog.status,
                    "ai_locked": True,
                    "p0_triggered": False
                }

            # 3. Загрузка истории диалога
            history_res = await session.execute(
                select(OutreachMessage).where(OutreachMessage.dialog_id == dialog.id).order_by(OutreachMessage.sent_at.asc())
            )
            dialog_history = [
                {"sender": m.sender_type, "text": m.message_text}
                for m in history_res.scalars().all()
            ]

            # 4. Классификация намерения (Intent Classifier)
            classification = await intent_classifier.classify(incoming_text, dialog_history, session)
            intent = classification.get("intent", "OTHER_CONVERSATION")
            confidence = classification.get("confidence", 0.8)
            requires_human = classification.get("requires_human", False)

            dialog.last_intent = intent
            dialog.intent_confidence = confidence

            # 5. P0 Эскалация (Интерес / Запрос цены / Телефон)
            if requires_human or intent == "INTERESTED":
                dialog.ai_locked = True
                dialog.status = DialogStatus.NEEDS_HUMAN
                await session.commit()

                await self._notify_manager_p0(dialog, incoming_text, classification)
                await self._notify_admin_mirror(dialog, incoming_text, classification, None)
                return {
                    "ok": True,
                    "intent": intent,
                    "confidence": confidence,
                    "requires_human": True,
                    "bot_reply": None,
                    "status": DialogStatus.NEEDS_HUMAN,
                    "ai_locked": True,
                    "p0_triggered": True
                }

            # 6. Жесткий отказ
            if intent == "REJECT_HARD":
                dialog.ai_locked = True
                dialog.status = DialogStatus.CLOSED_REJECTED
                farewell_text = "Понял вас, извините за беспокойство. Больше не потревожу."
                session.add(OutreachMessage(
                    dialog_id=dialog.id,
                    sender_type="bot",
                    message_text=farewell_text,
                    tg_message_id=None
                ))
                await session.commit()
                await self._notify_admin_mirror(dialog, incoming_text, classification, farewell_text)
                return {
                    "ok": True,
                    "intent": intent,
                    "confidence": confidence,
                    "requires_human": False,
                    "bot_reply": farewell_text,
                    "status": DialogStatus.CLOSED_REJECTED,
                    "ai_locked": True,
                    "p0_triggered": False
                }

            # 7. Запрос пруфа / скриншота
            bot_reply = ""
            if intent == "REQUEST_PROOF":
                bot_reply = "Вот, с телефона открывал — выделил проблемное место. Заметно как перекрывается?"
                dialog.status = DialogStatus.QUALIFYING

            elif intent == "IS_BOT":
                bot_reply = "Да не, руками пишу) Я разработчик из CastleWeb, сайты делаем. Просто с телефона на сайт зашел и увидел косяк в верстке"
                dialog.status = DialogStatus.QUALIFYING

            elif intent == "QUESTION_IDENTITY":
                bot_reply = "Я разработчик из CastleWeb (занимаемся разработкой и доработкой сайтов). Зашел к вам с телефона и заметил, что форма заявки съехала, решил написать"
                dialog.status = DialogStatus.QUALIFYING

            elif intent == "QUESTION_SOURCE":
                bot_reply = "Искал контакты на Яндекс.Картах / 2ГИС в карточке вашей компании."
                dialog.status = DialogStatus.QUALIFYING

            elif intent == "OBJECTION_DEV":
                bot_reply = "Отлично! Передайте ему скриншот/описание — пусть поправит форму, а то с мобилок клиенты отваливаются. Денег не нужно, просто хотел помочь."
                dialog.status = DialogStatus.QUALIFYING

            elif intent == "SKEPTIC":
                bot_reply = "На компьютере всё отлично. Ошибка вылезает именно на экранах смартфонов шириной до 390px (iPhone/Android). Прислать скриншот с телефона?"
                dialog.status = DialogStatus.QUALIFYING

            elif intent == "SEND_EMAIL":
                bot_reply = "Шаблонов КП не держу, задача точечная на 1–2 часа работы. Давайте пришлю скриншот сюда или кратко созвонимся на 3 минуты?"
                dialog.status = DialogStatus.QUALIFYING

            else:
                recommended = classification.get("recommended_response")
                if recommended and len(recommended.strip()) > 5:
                    bot_reply = recommended.strip()
                elif deepseek_client.is_configured():
                    try:
                        reply_prompt_tpl = await get_prompt("DIALOG_REPLY", session) or DEFAULT_DIALOG_REPLY_PROMPT
                        prompt = reply_prompt_tpl
                        for ph, val in (
                            ("{company_name}", dialog.company_name or "вашей компании"),
                            ("{website_url}", dialog.website_url or "вашем сайте"),
                            ("{dialog_history}", formatted_history_text(dialog_history)),
                            ("{intent}", intent),
                            ("{incoming_message}", incoming_text),
                        ):
                            prompt = prompt.replace(ph, str(val))
                        messages = [{"role": "user", "content": prompt}]
                        bot_reply = await deepseek_client.chat_completion(messages, temperature=0.3, max_tokens=150)
                    except Exception:
                        bot_reply = "Подсказать детальнее по ошибке или скинуть скриншот с экрана смартфона?"
                else:
                    bot_reply = "Подсказать детальнее по ошибке или скинуть скриншот с экрана смартфона?"
                dialog.status = DialogStatus.QUALIFYING

            session.add(OutreachMessage(
                dialog_id=dialog.id,
                sender_type="bot",
                message_text=bot_reply,
                tg_message_id=None
            ))
            await session.commit()
            await self._notify_admin_mirror(dialog, incoming_text, classification, bot_reply)

            return {
                "ok": True,
                "intent": intent,
                "confidence": confidence,
                "requires_human": False,
                "bot_reply": bot_reply,
                "status": dialog.status,
                "ai_locked": dialog.ai_locked,
                "p0_triggered": False,
                "defect_screenshot_path": dialog.defect_screenshot_path
            }


def formatted_history_text(dialog_history: List[Dict[str, str]]) -> str:
    res = ""
    for m in dialog_history[-6:]:
        role = "Мы" if m.get("sender") in ("bot", "manager") else "Клиент"
        res += f"{role}: {m.get('text', '')}\n"
    return res or "Начало диалога"


dialog_engine = DialogEngine()
