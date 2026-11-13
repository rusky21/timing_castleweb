"""Database-backed authorization for privileged routes and campaign streams."""

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_session_token
from app.db.database import get_db
from app.db.models import User

PRIVILEGED_ROLES = frozenset({"admin", "superuser", "root"})


async def get_active_session_user(token: str | None, db: AsyncSession) -> User | None:
    payload = decode_session_token(token) if token else None
    subject = payload.get("sub") if payload else None
    # SQLite IDs are signed 64-bit integers. Reject malformed/oversized subjects.
    if not isinstance(subject, str) or not subject.isascii() or not subject.isdecimal() or len(subject) > 19:
        return None
    uid = int(subject)
    if not 0 < uid <= 9223372036854775807:
        return None
    user = await db.get(User, uid)
    return user if user is not None and user.is_active else None


def is_privileged_user(user: User) -> bool:
    return (user.role or "").lower() in PRIVILEGED_ROLES


async def require_privileged_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    # Internal-service credentials are not operator credentials for Outreach.
    user = await get_active_session_user(request.cookies.get("access_token"), db)
    if user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if not is_privileged_user(user):
        raise HTTPException(status_code=403, detail="Требуются права администратора")
    return user
