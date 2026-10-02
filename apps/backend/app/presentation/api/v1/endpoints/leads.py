from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import verify_turnstile_token
from app.infrastructure.db.models import Lead, Blacklist
from app.domain.entities import LeadStatus
from app.presentation.schemas.lead import LeadCreate, LeadResponse
from app.presentation.middlewares.rate_limit import check_rate_limit
from app.infrastructure.queue.lead_queue import push_lead_to_queue

router = APIRouter()

# In-memory deduplication fallback when Redis is offline: {hash: (lead_id, expire_at)}
_in_memory_dedup: dict[str, tuple[int, float]] = {}


@router.post("", response_model=LeadResponse, status_code=status.HTTP_201_CREATED, summary="Submit a Lead from Website")
async def create_lead(
    payload: LeadCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    # 1. Rate Limiting Check (Max 3 submissions per 10 minutes from same IP)
    await check_rate_limit(request, key_prefix="ratelimit:leads", max_requests=3, window_seconds=600)

    # 2. Extract Client IP and User-Agent
    forwarded_for = request.headers.get("x-forwarded-for")
    client_ip = forwarded_for.split(",")[0].strip() if forwarded_for else (request.client.host if request.client else None)
    user_agent = request.headers.get("user-agent")

    # 3. Honeypot Anti-Spam Check: If hidden field is filled, silently ignore
    if payload.hp_website:
        return LeadResponse(
            id=0,
            name=payload.name,
            contact=payload.contact,
            task_description=payload.task_description,
            budget=payload.budget,
            attachment_url=payload.attachment_url,
            status=LeadStatus.SPAM,
            created_at=datetime.now(timezone.utc)
        )

    # 4. Cloudflare Turnstile Verification (only when token is present)
    from app.core.config import get_settings as _get_settings
    _settings = _get_settings()
    if _settings.CLOUDFLARE_TURNSTILE_ENABLED and payload.turnstile_token:
        is_human = await verify_turnstile_token(payload.turnstile_token, remote_ip=client_ip)
        if not is_human:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Проверка капчи не пройдена. Пожалуйста, обновите страницу."
            )

    # 5. Check Blacklist
    if client_ip:
        bl_check = await db.execute(select(Blacklist).where(Blacklist.ip_address == client_ip))
        if bl_check.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    # 5.5. Deduplication — prevent accidental double-submits (5-min window)
    import hashlib
    import time
    from app.core.redis import get_redis_client
    dedup_hash = hashlib.sha256(f"{payload.contact.strip()}:{payload.task_description.strip()}".encode()).hexdigest()[:16]
    dedup_key = f"lead_dedup:{dedup_hash}"
    existing_id = None

    redis = await get_redis_client()
    if redis:
        try:
            cached_val = await redis.get(dedup_key)
            if cached_val:
                existing_id = int(cached_val)
        except Exception:
            pass

    if existing_id is None:
        now_ts = time.time()
        if dedup_hash in _in_memory_dedup:
            lead_id_mem, exp_mem = _in_memory_dedup[dedup_hash]
            if now_ts < exp_mem:
                existing_id = lead_id_mem
            else:
                _in_memory_dedup.pop(dedup_hash, None)

    if existing_id is not None:
        existing = await db.execute(select(Lead).where(Lead.id == existing_id))
        existing_lead = existing.scalar_one_or_none()
        if existing_lead:
            return existing_lead

    # 6. Save to Database (Save First Principle)
    new_lead = Lead(
        name=payload.name.strip(),
        contact=payload.contact.strip(),
        task_description=payload.task_description.strip(),
        budget=payload.budget.strip() if payload.budget else None,
        attachment_url=payload.attachment_url.strip() if payload.attachment_url else None,
        status=LeadStatus.PENDING,
        ip_address=client_ip,
        user_agent=user_agent
    )

    db.add(new_lead)
    await db.commit()
    await db.refresh(new_lead)

    # Store dedup key for 5 minutes
    if redis:
        try:
            await redis.set(dedup_key, str(new_lead.id), ex=300)
        except Exception:
            pass
    _in_memory_dedup[dedup_hash] = (new_lead.id, time.time() + 300)


    # 7. Push to background queue for GeoIP enrichment and Telegram delivery
    await push_lead_to_queue(new_lead.id)

    return new_lead


@router.delete("/{lead_id}", summary="Delete Lead Record by ID")
async def delete_lead(
    lead_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Удаляет запись заявки (лида) из базы данных по её ID.
    """
    res = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = res.scalar_one_or_none()
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Заявка #{lead_id} не найдена в базе данных"
        )

    await db.delete(lead)
    await db.commit()
    return {"ok": True, "message": f"Заявка #{lead_id} успешно удалена", "deleted_id": lead_id}
