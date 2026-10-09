import asyncio
import datetime
import logging
from typing import Dict, Optional
from sqlalchemy import select, update

from app.config import HEADLESS
from app.db.database import async_session_factory
from app.db.models import SearchCampaign, Organization, AuditResult, utc_now
from app.services.scrapers.base import ScrapedOrgItem
from app.services.scrapers.yandex_scraper import YandexScraper
from app.services.scrapers.twogis_scraper import TwoGisScraper
from app.services.site_auditor import SiteAuditor
from app.services.connection_manager import ws_manager
from app.schemas.lead import LeadItem, PitchDetail

logger = logging.getLogger("task_manager")

class TaskContext:
    def __init__(self, campaign_id: int):
        self.campaign_id = campaign_id
        self.task: Optional[asyncio.Task] = None
        self.is_cancelled: bool = False
        self.active_yandex_scraper: Optional[YandexScraper] = None
        self.active_twogis_scraper: Optional[TwoGisScraper] = None

class TaskManager:
    """Менеджер фоновых поисковых задач с поддержкой паузы, отмены и стриминга"""

    def __init__(self):
        self._tasks: Dict[int, TaskContext] = {}

    def is_running(self, campaign_id: int) -> bool:
        ctx = self._tasks.get(campaign_id)
        return ctx is not None and ctx.task is not None and not ctx.task.done()

    def signal_captcha_resolved(self, campaign_id: int):
        ctx = self._tasks.get(campaign_id)
        if ctx:
            if ctx.active_yandex_scraper:
                ctx.active_yandex_scraper.signal_captcha_resolved()
            if ctx.active_twogis_scraper:
                ctx.active_twogis_scraper.signal_captcha_resolved()
            logger.info(f"Sent captcha resolved signal for campaign {campaign_id}")

    def stop_campaign(self, campaign_id: int) -> bool:
        ctx = self._tasks.get(campaign_id)
        if ctx:
            ctx.is_cancelled = True
            if ctx.task and not ctx.task.done():
                ctx.task.cancel()
            logger.info(f"Campaign {campaign_id} stopped by user")
            return True
        return False

    def start_campaign(self, campaign_id: int, niche: str, city: str, source: str, limit: int):
        ctx = TaskContext(campaign_id)
        self._tasks[campaign_id] = ctx
        ctx.task = asyncio.create_task(
            self._run_campaign_worker(ctx, niche, city, source, limit)
        )
        return ctx.task

    async def _run_campaign_worker(
        self,
        ctx: TaskContext,
        niche: str,
        city: str,
        source: str,
        limit: int
    ):
        campaign_id = ctx.campaign_id
        auditor = SiteAuditor()
        collected_count = 0

        # Обновляем статус в БД на RUNNING
        async with async_session_factory() as db:
            await db.execute(
                update(SearchCampaign)
                .where(SearchCampaign.id == campaign_id)
                .values(status="RUNNING")
            )
            await db.commit()

        async def on_status(message: str):
            await ws_manager.broadcast(campaign_id, {
                "type": "AUDIT_STATUS",
                "data": {
                    "domain": "",
                    "step": "SCRAPING",
                    "message": message
                }
            })

        async def on_captcha(message: str):
            # Переводим статус в PAUSED_CAPTCHA
            async with async_session_factory() as db:
                await db.execute(
                    update(SearchCampaign)
                    .where(SearchCampaign.id == campaign_id)
                    .values(status="PAUSED_CAPTCHA")
                )
                await db.commit()

            await ws_manager.broadcast(campaign_id, {
                "type": "CAPTCHA_REQUIRED",
                "data": {
                    "service": "yandex",
                    "message": message,
                    "hint": "Пройдите проверку в окне браузера и нажмите кнопку 'Готово' в интерфейсе"
                }
            })

            from app.services.telegram.dispatcher import tg_dispatcher
            asyncio.create_task(tg_dispatcher.broadcast_captcha_alert(
                service="yandex",
                message=message,
                campaign_id=campaign_id
            ))

        async def on_item_scraped(item: ScrapedOrgItem):
            nonlocal collected_count
            if ctx.is_cancelled or collected_count >= limit:
                return

            domain_name = item.website or "без сайта"

            # Статус аудита для радара
            await ws_manager.broadcast(campaign_id, {
                "type": "AUDIT_STATUS",
                "data": {
                    "domain": domain_name,
                    "step": "AUDITING_SITE",
                    "message": f"Аудит: {item.name} ({domain_name})..."
                }
            })

            # Выполняем глубокий аудит сайта
            audit_res = await auditor.audit_url(
                url=item.website,
                org_name=item.name,
                category=item.category or niche,
                city=city
            )

            # Объединяем соцсети и мессенджеры из скрейпера карт и сайта
            combined_socials = list(item.socials or [])
            for s in (audit_res.get("extra_socials") or []):
                if s not in combined_socials:
                    combined_socials.append(s)

            telegram_val = item.telegram or next((s for s in combined_socials if "t.me" in s), None)
            has_tg = bool(telegram_val)

            # Сохраняем организацию и аудит в SQLite
            lead_dto: Optional[LeadItem] = None
            saved_successfully = False
            async with async_session_factory() as db:
                try:
                    org = Organization(
                        campaign_id=campaign_id,
                        source=item.source,
                        external_id=item.external_id,
                        name=item.name,
                        category=item.category or niche,
                        address=item.address,
                        rating=item.rating,
                        reviews_count=item.reviews_count,
                        phones=item.phones,
                        website=item.website,
                        telegram=telegram_val,
                        has_telegram=has_tg,
                        card_url=item.card_url
                    )
                    db.add(org)
                    await db.flush()

                    pitch_info = audit_res.get("pitch", {})
                    audit_record = AuditResult(
                        org_id=org.id,
                        status=audit_res["status"],
                        has_ssl=audit_res["has_ssl"],
                        is_adaptive=audit_res["is_adaptive"],
                        has_analytics=audit_res["has_analytics"],
                        detected_cms=audit_res["detected_cms"],
                        last_updated_year=audit_res["last_updated_year"],
                        final_url=audit_res["final_url"],
                        extra_phones=audit_res["extra_phones"],
                        extra_emails=audit_res["extra_emails"],
                        extra_socials=combined_socials,
                        status_badge=audit_res["status_badge"],
                        lead_score=audit_res["lead_score"],
                        pitch_pain=pitch_info.get("pain"),
                        pitch_solution=pitch_info.get("solution"),
                        pitch_opening_phrase=pitch_info.get("opening_phrase"),
                        pitch_full_text=pitch_info.get("full_text")
                    )
                    db.add(audit_record)

                    collected_count += 1
                    saved_successfully = True

                    # Обновляем счетчик в кампании
                    await db.execute(
                        update(SearchCampaign)
                        .where(SearchCampaign.id == campaign_id)
                        .values(found_count=collected_count)
                    )
                    await db.commit()

                    # Собираем DTO для WebSocket
                    all_phones = list(item.phones)
                    for ep in audit_res["extra_phones"]:
                        if ep not in all_phones:
                            all_phones.append(ep)

                    primary_phone = all_phones[0] if all_phones else None
                    email = audit_res["extra_emails"][0] if audit_res["extra_emails"] else None

                    lead_dto = LeadItem(
                        id=org.id,
                        campaign_id=campaign_id,
                        name=org.name,
                        category=org.category,
                        address=org.address,
                        rating=org.rating,
                        reviews_count=org.reviews_count,
                        primary_phone=primary_phone,
                        all_phones=all_phones,
                        email=email,
                        all_emails=audit_res["extra_emails"],
                        telegram=telegram_val,
                        socials=[{"url": s} for s in combined_socials],
                        website=org.website,
                        final_url=audit_res["final_url"],
                        card_url=org.card_url,
                        source=org.source,
                        status_badge=audit_res["status_badge"],
                        lead_score=audit_res["lead_score"],
                        has_ssl=audit_res["has_ssl"],
                        is_adaptive=audit_res["is_adaptive"],
                        has_analytics=audit_res["has_analytics"],
                        detected_cms=audit_res["detected_cms"],
                        last_updated_year=audit_res["last_updated_year"],
                        pitch=PitchDetail(**pitch_info) if pitch_info else None
                    )

                except Exception as db_err:
                    logger.error(f"Error saving lead to DB: {db_err}")
                    await db.rollback()

            # Отправляем события в WebSocket при успешном сохранении
            if saved_successfully:
                percent = int((collected_count / limit) * 100) if limit > 0 else 100
                percent = min(percent, 100)

                await ws_manager.broadcast(campaign_id, {
                    "type": "PROGRESS",
                    "data": {
                        "found": collected_count,
                        "limit": limit,
                        "percent": percent
                    }
                })

                if lead_dto:
                    await ws_manager.broadcast(campaign_id, {
                        "type": "NEW_LEAD",
                        "data": lead_dto.model_dump()
                    })

                    from app.services.telegram.dispatcher import tg_dispatcher
                    asyncio.create_task(tg_dispatcher.dispatch_lead(lead_dto.model_dump()))

        try:
            # Запуск скрейперов в зависимости от выбранного источника
            # Парсинг исключительно через Яндекс.Карты (2ГИС отключен)
            ctx.active_yandex_scraper = YandexScraper(headless=HEADLESS)
            await ctx.active_yandex_scraper.scrape(
                niche=niche,
                city=city,
                limit=limit,
                on_item_scraped=on_item_scraped,
                on_status=on_status,
                on_captcha=on_captcha,
                is_cancelled=lambda: ctx.is_cancelled or collected_count >= limit
            )

            final_status = "STOPPED" if ctx.is_cancelled else "COMPLETED"

            # Фиксируем завершение кампании в БД
            async with async_session_factory() as db:
                await db.execute(
                    update(SearchCampaign)
                    .where(SearchCampaign.id == campaign_id)
                    .values(
                        status=final_status,
                        found_count=collected_count,
                        finished_at=utc_now()
                    )
                )
                await db.commit()

            await ws_manager.broadcast(campaign_id, {
                "type": final_status,
                "data": {
                    "campaign_id": campaign_id,
                    "total_found": collected_count,
                    "status": final_status
                }
            })

        except asyncio.CancelledError:
            async with async_session_factory() as db:
                await db.execute(
                    update(SearchCampaign)
                    .where(SearchCampaign.id == campaign_id)
                    .values(status="STOPPED", finished_at=utc_now())
                )
                await db.commit()

            await ws_manager.broadcast(campaign_id, {
                "type": "STOPPED",
                "data": {"campaign_id": campaign_id, "message": "Поиск остановлен пользователем"}
            })

        except Exception as e:
            logger.exception(f"Unhandled error in campaign {campaign_id}: {e}")
            async with async_session_factory() as db:
                await db.execute(
                    update(SearchCampaign)
                    .where(SearchCampaign.id == campaign_id)
                    .values(status="FAILED", error_message=str(e), finished_at=utc_now())
                )
                await db.commit()

            await ws_manager.broadcast(campaign_id, {
                "type": "ERROR",
                "data": {"campaign_id": campaign_id, "error": str(e)}
            })

task_manager = TaskManager()
