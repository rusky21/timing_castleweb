import logging
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import (
    OutreachAccount, OutreachDialog, OutreachMessage,
    OutreachBlacklist, OutreachCampaign, OutreachPrompt,
    DialogStatus, OutreachAccountStatus, utc_now
)
from app.services.outreach import (
    session_manager, screenshot_service, pitch_generator,
    followup_worker
)
from app.services.deepseek.client import deepseek_client

logger = logging.getLogger("api_outreach")
router = APIRouter(prefix="/api/outreach", tags=["AI Outreach & SDR"])


# ====================================================================
# Pydantic схемы
# ====================================================================

class TestOutreachRequest(BaseModel):
    username: str
    website_url: str
    company_name: Optional[str] = "Организация"
    city: Optional[str] = "Москва"


class SendManualMessageRequest(BaseModel):
    text: str


class AddBlacklistRequest(BaseModel):
    identifier: str
    reason: Optional[str] = "Ручная блокировка"


# ====================================================================
# Эндпоинты
# ====================================================================

@router.get("/stats")
async def get_outreach_stats(db: AsyncSession = Depends(get_db)):
    """Сводная аналитика и ключевые метрики конверсии"""
    total = (await db.execute(select(func.count(OutreachDialog.id)))).scalar_one()
    replied = (await db.execute(
        select(func.count(OutreachDialog.id)).where(OutreachDialog.last_client_reply_at.is_not(None))
    )).scalar_one()
    hot_leads = (await db.execute(
        select(func.count(OutreachDialog.id)).where(OutreachDialog.status == DialogStatus.NEEDS_HUMAN)
    )).scalar_one()
    closed_won = (await db.execute(
        select(func.count(OutreachDialog.id)).where(OutreachDialog.status == DialogStatus.CLOSED_WON)
    )).scalar_one()
    sent_today = (await db.execute(select(func.coalesce(func.sum(OutreachAccount.sent_today), 0)))).scalar_one()

    accounts_total = (await db.execute(select(func.count(OutreachAccount.id)))).scalar_one()
    accounts_active = (await db.execute(
        select(func.count(OutreachAccount.id)).where(OutreachAccount.status == OutreachAccountStatus.ACTIVE)
    )).scalar_one()

    return {
        "dialogs_total": total,
        "replied_count": replied,
        "reply_cr": round((replied / total * 100) if total > 0 else 0.0, 1),
        "leads_count": hot_leads,
        "lead_cr": round((hot_leads / total * 100) if total > 0 else 0.0, 1),
        "closed_won": closed_won,
        "sent_today": sent_today,
        "accounts_total": accounts_total,
        "accounts_active": accounts_active,
        "is_paused": followup_worker.is_paused,
    }


@router.get("/accounts")
async def get_accounts(db: AsyncSession = Depends(get_db)):
    """Список рабочих аккаунтов MTProto"""
    res = await db.execute(select(OutreachAccount).order_by(OutreachAccount.id.asc()))
    accounts = res.scalars().all()
    return [a.to_dict() for a in accounts]


@router.get("/dialogs")
async def get_dialogs(
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """Список диалогов с фильтрацией по статусу"""
    query = select(OutreachDialog).order_by(OutreachDialog.updated_at.desc())
    if status:
        query = query.where(OutreachDialog.status == status)

    query = query.limit(limit).offset(offset)
    res = await db.execute(query)
    dialogs = res.scalars().all()
    return [d.to_dict() for d in dialogs]


@router.get("/dialogs/{dialog_id}")
async def get_dialog_detail(dialog_id: int, db: AsyncSession = Depends(get_db)):
    """Детальная информация о диалоге со всей историей переписки"""
    res = await db.execute(select(OutreachDialog).where(OutreachDialog.id == dialog_id))
    dlg = res.scalar_one_or_none()
    if not dlg:
        raise HTTPException(status_code=404, detail="Диалог не найден")

    m_res = await db.execute(
        select(OutreachMessage).where(OutreachMessage.dialog_id == dialog_id).order_by(OutreachMessage.sent_at.asc())
    )
    messages = m_res.scalars().all()

    data = dlg.to_dict()
    data["messages"] = [m.to_dict() for m in messages]
    return data


@router.post("/dialogs/{dialog_id}/takeover")
async def takeover_dialog(dialog_id: int, db: AsyncSession = Depends(get_db)):
    """Human Takeover: Мгновенная блокировка автоответов ИИ для передачи диалога менеджеру"""
    res = await db.execute(select(OutreachDialog).where(OutreachDialog.id == dialog_id))
    dlg = res.scalar_one_or_none()
    if not dlg:
        raise HTTPException(status_code=404, detail="Диалог не найден")

    dlg.ai_locked = True
    dlg.status = DialogStatus.NEEDS_HUMAN
    await db.commit()
    return {"ok": True, "message": "ИИ успешно заблокирован. Диалог передан менеджеру."}


@router.post("/dialogs/{dialog_id}/message")
async def send_manual_dialog_message(
    dialog_id: int,
    req: SendManualMessageRequest,
    db: AsyncSession = Depends(get_db)
):
    """Отправка ручного ответа клиенту от имени рабочего MTProto-аккаунта"""
    res = await db.execute(select(OutreachDialog).where(OutreachDialog.id == dialog_id))
    dlg = res.scalar_one_or_none()
    if not dlg:
        raise HTTPException(status_code=404, detail="Диалог не найден")

    if not dlg.account_id:
        raise HTTPException(status_code=400, detail="У диалога не привязан рабочий аккаунт")

    recipient = dlg.client_tg_username or dlg.client_tg_id
    if not recipient:
        raise HTTPException(status_code=400, detail="Не указан контакт получателя")

    try:
        msg_id = await session_manager.send_message_safe(
            account_id=dlg.account_id,
            recipient=recipient,
            text=req.text,
            simulate_typing=True
        )
        msg_obj = OutreachMessage(
            dialog_id=dlg.id,
            sender_type="manager",
            message_text=req.text,
            tg_message_id=msg_id
        )
        db.add(msg_obj)
        dlg.ai_locked = True
        await db.commit()
        return {"ok": True, "message_id": msg_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка отправки через Telegram: {e}")


@router.post("/test")
async def trigger_test_outreach(req: TestOutreachRequest, db: AsyncSession = Depends(get_db)):
    """Эндпоинт запуска ручного теста с генерацией пруфа и питча"""
    account = await session_manager.pick_best_account()
    if not account:
        raise HTTPException(status_code=400, detail="В пуле нет активных аккаунтов")

    # 1. Скриншот через Playwright
    screenshot_path = await screenshot_service.capture_mobile_defect(req.website_url)

    # 2. Генерация первого питча CastleWeb
    pitch_text, issue_summary = await pitch_generator.generate(
        company_name=req.company_name,
        city=req.city,
        website_url=req.website_url,
        audit_data={"pitch_pain": "Сдвиг формы", "is_adaptive": False},
        db_session=db
    )

    # 3. Отправка через MTProto
    try:
        clean_user = req.username.strip()
        msg_id = await session_manager.send_message_safe(
            account_id=account.id,
            recipient=clean_user,
            text=pitch_text,
            simulate_typing=True
        )

        dialog = OutreachDialog(
            account_id=account.id,
            client_tg_username=clean_user.lstrip("@"),
            company_name=req.company_name,
            website_url=req.website_url,
            pitch_text=pitch_text,
            defect_screenshot_path=screenshot_path,
            pitch_sent_at=utc_now(),
            status=DialogStatus.PITCH_SENT,
            is_test=True
        )
        db.add(dialog)
        await db.commit()
        await db.refresh(dialog)

        db.add(OutreachMessage(
            dialog_id=dialog.id,
            sender_type="bot",
            message_text=pitch_text,
            tg_message_id=msg_id
        ))
        await db.commit()

        return {
            "ok": True,
            "dialog_id": dialog.id,
            "pitch_text": pitch_text,
            "screenshot_path": screenshot_path,
            "account_used": account.phone
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка отправки через Telegram: {e}")


@router.get("/blacklist")
async def get_blacklist(db: AsyncSession = Depends(get_db)):
    """Список заблокированных контактов"""
    res = await db.execute(select(OutreachBlacklist).order_by(OutreachBlacklist.added_at.desc()))
    items = res.scalars().all()
    return [{"id": b.id, "identifier": b.identifier, "reason": b.reason, "added_at": b.added_at.isoformat()} for b in items]


@router.post("/blacklist")
async def add_to_blacklist(req: AddBlacklistRequest, db: AsyncSession = Depends(get_db)):
    """Добавление контакта в стоп-лист"""
    clean_id = req.identifier.strip()
    res = await db.execute(select(OutreachBlacklist).where(OutreachBlacklist.identifier == clean_id))
    if res.scalar_one_or_none():
        return {"ok": True, "message": "Контакт уже находится в черном списке"}

    item = OutreachBlacklist(identifier=clean_id, reason=req.reason)
    db.add(item)
    await db.commit()
    return {"ok": True, "identifier": clean_id}


@router.delete("/blacklist/{item_id}")
async def remove_from_blacklist(item_id: int, db: AsyncSession = Depends(get_db)):
    """Удаление контакта из стоп-листа"""
    await db.execute(delete(OutreachBlacklist).where(OutreachBlacklist.id == item_id))
    await db.commit()
    return {"ok": True}


@router.get("/health")
async def get_outreach_health():
    """Проверка здоровья всех компонентов аутрича"""
    ds_ok, ds_lat, ds_msg = await deepseek_client.ping()
    return {
        "deepseek": {
            "status": "OK" if ds_ok else "ERROR",
            "latency_ms": ds_lat,
            "message": ds_msg
        },
        "sessions_online": len(session_manager.clients),
        "followup_worker": {
            "is_running": followup_worker._is_running,
            "is_paused": followup_worker.is_paused,
            "is_working_hours": followup_worker.is_working_hours()
        }
    }


class UpdateSettingRequest(BaseModel):
    key: str
    value: str


@router.get("/settings")
async def get_settings():
    """Получение списка параметров .env с маскированием секретов"""
    from app.core.env_editor import ENV_META, get_env_value
    res = []
    for k, meta in ENV_META.items():
        v = get_env_value(k, meta["default"])
        masked = (v[:6] + "..." + v[-4:]) if (meta["secret"] and len(v) > 10) else ("******" if meta["secret"] and v else v)
        res.append({
            "key": k,
            "title": meta["title"],
            "desc": meta["desc"],
            "value": masked,
            "is_set": bool(v),
            "secret": meta["secret"]
        })
    return res


@router.post("/settings")
async def update_setting(req: UpdateSettingRequest):
    """Обновление параметра в файле .env"""
    from app.core.env_editor import set_env_value, ENV_META
    if req.key not in ENV_META:
        raise HTTPException(status_code=400, detail="Недопустимый ключ конфигурации")
    set_env_value(req.key, req.value)
    if req.key == "DEEPSEEK_API_KEY":
        deepseek_client.set_api_key(req.value)
    return {"ok": True, "key": req.key}

