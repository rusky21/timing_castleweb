import asyncio
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, update

from app.config import (
    OUTREACH_WORK_HOURS_START, OUTREACH_WORK_HOURS_END
)
from app.db.database import async_session_factory
from app.db.models import (
    OutreachDialog, OutreachMessage, DialogStatus, utc_now
)
from app.services.outreach.session_manager import session_manager
from app.services.outreach.prompts import get_prompt, DEFAULT_FOLLOWUP_1_PROMPT, DEFAULT_FOLLOWUP_2_PROMPT

logger = logging.getLogger("followup_worker")


class FollowUpWorker:
    """
    Фоновый воркер умной цепочки Follow-up касаний.
    Возвращает до 25-35% молчащих контактов.
    """

    def __init__(self):
        self._is_running = False
        self._task: asyncio.Task | None = None
        self._paused = False

    @property
    def is_paused(self) -> bool:
        return self._paused

    def pause(self):
        self._paused = True
        logger.info("⏸ FollowUpWorker поставлен на паузу.")

    def resume(self):
        self._paused = False
        logger.info("▶️ FollowUpWorker возобновил работу.")

    def is_working_hours(self) -> bool:
        """
        Проверяет, попадает ли текущее время в интервал рабочих часов (по МСК UTC+3).
        """
        # UTC+3 (МСК)
        msk_time = datetime.now(timezone(timedelta(hours=3)))
        # Понедельник = 0, Воскресенье = 6. В выходные активность снижена.
        if msk_time.weekday() >= 6:  # Воскресенье — выходной
            return False
        return OUTREACH_WORK_HOURS_START <= msk_time.hour < OUTREACH_WORK_HOURS_END

    def start(self):
        if self._is_running:
            return
        self._is_running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("⏰ FollowUpWorker успешно запущен.")

    def stop(self):
        self._is_running = False
        if self._task and not self._task.done():
            self._task.cancel()
        logger.info("FollowUpWorker остановлен.")

    async def _run_loop(self):
        while self._is_running:
            try:
                if not self._paused and self.is_working_hours():
                    await self.process_pending_followups()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Сбой в цикле FollowUpWorker: {e}", exc_info=True)

            # Проверка каждые 15 минут
            await asyncio.sleep(900)

    async def process_pending_followups(self):
        """Проверяет все диалоги, ожидающие очередного касания"""
        now = utc_now()
        async with async_session_factory() as session:
            # 1. Поиск диалогов для Follow-up #1 (прошло > 48 часов с момента первого питча, ответа нет)
            fu1_cutoff = now - timedelta(hours=48)
            q1 = select(OutreachDialog).where(
                OutreachDialog.status == DialogStatus.PITCH_SENT,
                OutreachDialog.ai_locked == False,
                OutreachDialog.last_client_reply_at.is_(None),
                OutreachDialog.pitch_sent_at <= fu1_cutoff,
                OutreachDialog.followup_count == 0
            ).limit(10)

            res1 = await session.execute(q1)
            dialogs_fu1 = res1.scalars().all()

            for d in dialogs_fu1:
                await self._send_followup_1(d, session)

            # 2. Поиск диалогов для Follow-up #2 (Break-Up: прошло > 72 часов с момента FU1)
            fu2_cutoff = now - timedelta(hours=72)
            q2 = select(OutreachDialog).where(
                OutreachDialog.status == DialogStatus.FOLLOWUP_1_SENT,
                OutreachDialog.ai_locked == False,
                OutreachDialog.last_client_reply_at.is_(None),
                OutreachDialog.updated_at <= fu2_cutoff,
                OutreachDialog.followup_count == 1
            ).limit(10)

            res2 = await session.execute(q2)
            dialogs_fu2 = res2.scalars().all()

            for d in dialogs_fu2:
                await self._send_followup_2(d, session)

            # 3. Архивирование диалогов, которые проигнорировали FU2 спустя 96 часов
            archive_cutoff = now - timedelta(hours=96)
            q_arch = select(OutreachDialog).where(
                OutreachDialog.status == DialogStatus.FOLLOWUP_2_SENT,
                OutreachDialog.last_client_reply_at.is_(None),
                OutreachDialog.updated_at <= archive_cutoff
            )
            res_arch = await session.execute(q_arch)
            for d in res_arch.scalars().all():
                d.status = DialogStatus.ARCHIVED_NO_REPLY
            await session.commit()

    async def _send_followup_1(self, dialog: OutreachDialog, session):
        """Отправка Follow-Up #1 с предложением скриншота"""
        prompt = await get_prompt("FOLLOWUP_1", session) or DEFAULT_FOLLOWUP_1_PROMPT
        text = "Добрый день! На всякий случай сделал скриншот с экрана смартфона, где видно, как съезжает верстка кнопки заявки. Прислать сюда, чтобы посмотрели?"

        try:
            acc_id = dialog.account_id
            if not acc_id:
                return

            recipient = dialog.client_tg_username or dialog.client_tg_id
            msg_id = await session_manager.send_message_safe(acc_id, recipient, text)

            dialog.status = DialogStatus.FOLLOWUP_1_SENT
            dialog.followup_count = 1
            dialog.updated_at = utc_now()

            session.add(OutreachMessage(
                dialog_id=dialog.id,
                sender_type="bot",
                message_text=text,
                tg_message_id=msg_id
            ))
            await session.commit()
            logger.info(f"📨 Отправлен Follow-Up #1 в диалог #{dialog.id} ({recipient})")

        except Exception as e:
            logger.warning(f"Не удалось отправить Follow-up #1 в #{dialog.id}: {e}")

    async def _send_followup_2(self, dialog: OutreachDialog, session):
        """Отправка Follow-Up #2 (Break-up / вежливое завершение)"""
        text = "Приветствую! Похоже, вопрос с сайтом сейчас не в приоритете, больше отвлекать не буду. Если в будущем понадобится глянуть верстку или мобильную скорость — пишите в любое время. Удачного дня!"

        try:
            acc_id = dialog.account_id
            if not acc_id:
                return

            recipient = dialog.client_tg_username or dialog.client_tg_id
            msg_id = await session_manager.send_message_safe(acc_id, recipient, text)

            dialog.status = DialogStatus.FOLLOWUP_2_SENT
            dialog.followup_count = 2
            dialog.updated_at = utc_now()

            session.add(OutreachMessage(
                dialog_id=dialog.id,
                sender_type="bot",
                message_text=text,
                tg_message_id=msg_id
            ))
            await session.commit()
            logger.info(f"📨 Отправлен Follow-Up #2 (Break-up) в диалог #{dialog.id} ({recipient})")

        except Exception as e:
            logger.warning(f"Не удалось отправить Follow-up #2 в #{dialog.id}: {e}")


followup_worker = FollowUpWorker()
