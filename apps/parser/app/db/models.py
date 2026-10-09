from datetime import datetime, timezone
from typing import List, Optional, Any
from sqlalchemy import (
    Integer, String, Float, Boolean, DateTime, ForeignKey, 
    Text, UniqueConstraint, JSON
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.database import Base

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class SearchCampaign(Base):
    """Поисковая кампания (для вкладки 'Отчёты')"""
    __tablename__ = "search_campaigns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    niche: Mapped[str] = mapped_column(String(255), nullable=False)
    city: Mapped[str] = mapped_column(String(255), nullable=False)
    source: Mapped[str] = mapped_column(String(50), default="all")  # 'yandex', '2gis', 'all'
    target_limit: Mapped[int] = mapped_column(Integer, default=50)
    found_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(50), default="PENDING")  # PENDING, RUNNING, PAUSED_CAPTCHA, COMPLETED, STOPPED, FAILED
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Связь с организациями
    organizations: Mapped[List["Organization"]] = relationship(
        "Organization",
        back_populates="campaign",
        cascade="all, delete-orphan",
        order_by="Organization.id"
    )

    def to_summary_dict(self) -> dict:
        """Сводка по кампании для списка в отчётах"""
        no_site = 0
        no_ssl = 0
        not_responsive = 0
        no_analytics = 0
        
        for org in self.organizations:
            if org.audit:
                if org.audit.status in ("NO_SITE", "SITE_DOWN"):
                    no_site += 1
                if not org.audit.has_ssl and org.audit.status not in ("NO_SITE", "ONLY_SOCIAL"):
                    no_ssl += 1
                if not org.audit.is_adaptive and org.audit.status not in ("NO_SITE", "ONLY_SOCIAL"):
                    not_responsive += 1
                if not org.audit.has_analytics and org.audit.status not in ("NO_SITE", "ONLY_SOCIAL"):
                    no_analytics += 1

        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "niche": self.niche,
            "city": self.city,
            "source": self.source,
            "requested_limit": self.target_limit,
            "found_count": self.found_count,
            "status": self.status,
            "summary": {
                "no_site": no_site,
                "no_ssl": no_ssl,
                "not_responsive": not_responsive,
                "no_analytics": no_analytics
            }
        }


class Organization(Base):
    """Спарсенная организация из геосервиса"""
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    campaign_id: Mapped[int] = mapped_column(Integer, ForeignKey("search_campaigns.id", ondelete="CASCADE"), nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)  # 'yandex' | '2gis'
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    rating: Mapped[float] = mapped_column(Float, default=0.0)
    reviews_count: Mapped[int] = mapped_column(Integer, default=0)
    
    phones: Mapped[Any] = mapped_column(JSON, default=list)  # Список телефонов из карточки
    website: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    telegram: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Прямой ник или ссылка t.me
    has_telegram: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    card_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    # Связи
    campaign: Mapped["SearchCampaign"] = relationship("SearchCampaign", back_populates="organizations")
    audit: Mapped[Optional["AuditResult"]] = relationship(
        "AuditResult",
        back_populates="organization",
        uselist=False,
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("source", "external_id", "campaign_id", name="uq_source_external_campaign"),
    )


class AuditResult(Base):
    """Результаты аудита сайта и персонализированный оффер"""
    __tablename__ = "audit_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    org_id: Mapped[int] = mapped_column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), unique=True, nullable=False)
    
    # Статус аудита: 'OK', 'NO_SITE', 'ONLY_SOCIAL', 'SITE_DOWN', 'BROKEN_SOCIAL_LINK'
    status: Mapped[str] = mapped_column(String(50), default="OK")
    has_ssl: Mapped[bool] = mapped_column(Boolean, default=False)
    is_adaptive: Mapped[bool] = mapped_column(Boolean, default=False)
    has_analytics: Mapped[bool] = mapped_column(Boolean, default=False)
    detected_cms: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_updated_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    final_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    
    # Спарсенные контакты с сайта
    extra_phones: Mapped[Any] = mapped_column(JSON, default=list)
    extra_emails: Mapped[Any] = mapped_column(JSON, default=list)
    extra_socials: Mapped[Any] = mapped_column(JSON, default=list)  # tg, vk, wa

    # Бейдж статуса для фронтенда (согласно референсу)
    # 'NO_SSL' | 'NOT_RESPONSIVE' | 'NO_ANALYTICS' | 'HTTPS_OK' | 'NO_WEBSITE' | 'SITE_DOWN'
    status_badge: Mapped[str] = mapped_column(String(50), default="HTTPS_OK")
    lead_score: Mapped[int] = mapped_column(Integer, default=50)  # 0 - 100

    # Скрипт продаж / оффер для менеджера
    pitch_pain: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    pitch_solution: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    pitch_opening_phrase: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    pitch_full_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    audited_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    organization: Mapped["Organization"] = relationship("Organization", back_populates="audit")


class FLOrder(Base):
    """Спарсенный заказ с биржи FL.ru"""
    __tablename__ = "fl_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # ID проекта на FL.ru (например, 5432190)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    price_raw: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Исходная строка (напр. "15 000 ₽" или "По договоренности")
    price_rub: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)  # Парсированная сумма в рублях для фильтрации
    is_negotiable: Mapped[bool] = mapped_column(Boolean, default=False)  # Флаг "По договоренности"
    category_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    category_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    is_pro_only: Mapped[bool] = mapped_column(Boolean, default=False)
    is_urgent: Mapped[bool] = mapped_column(Boolean, default=False)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    # Взаимодействие (избранное/скрыто)
    interaction: Mapped[Optional["FLOrderInteraction"]] = relationship(
        "FLOrderInteraction",
        back_populates="order",
        uselist=False,
        lazy="selectin",
        cascade="all, delete-orphan"
    )

    def to_dict(self) -> dict:
        is_fav = False
        is_hid = False
        is_rd = False
        # Безопасное чтение без DetachedInstanceError при отделенной сессии
        inter = self.__dict__.get("interaction")
        if inter:
            is_fav = getattr(inter, "is_favorite", False)
            is_hid = getattr(inter, "is_hidden", False)
            is_rd = getattr(inter, "is_read", False)

        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "price_raw": self.price_raw,
            "price_rub": self.price_rub,
            "is_negotiable": self.is_negotiable,
            "category_id": self.category_id,
            "category_name": self.category_name,
            "url": self.url,
            "is_pro_only": self.is_pro_only,
            "is_urgent": self.is_urgent,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "is_favorite": is_fav,
            "is_hidden": is_hid,
            "is_read": is_rd,
        }


class FLCategorySync(Base):
    """Фиксация первой синхронизации категории для предотвращения флуда старыми заказами"""
    __tablename__ = "fl_category_sync"

    category_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    category_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class FLOrderInteraction(Base):
    """Пользовательские метки десктопа: прочитано / избранное / скрыто"""
    __tablename__ = "fl_order_interactions"

    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("fl_orders.id", ondelete="CASCADE"), primary_key=True)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    order: Mapped["FLOrder"] = relationship("FLOrder", back_populates="interaction")


class TelegramUser(Base):
    """Пользователь Telegram-бота"""
    __tablename__ = "telegram_users"

    chat_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    settings: Mapped[Optional["TelegramUserSettings"]] = relationship(
        "TelegramUserSettings",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )


class TelegramUserSettings(Base):
    """Персональные настройки уведомлений и фильтров пользователя Telegram"""
    __tablename__ = "telegram_user_settings"

    chat_id: Mapped[int] = mapped_column(Integer, ForeignKey("telegram_users.chat_id", ondelete="CASCADE"), primary_key=True)
    fl_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    fl_categories: Mapped[Any] = mapped_column(JSON, default=list)  # Список выбранных ID категорий
    fl_min_price: Mapped[int] = mapped_column(Integer, default=0)
    fl_negative_words: Mapped[Any] = mapped_column(JSON, default=list)
    fl_keywords: Mapped[Any] = mapped_column(JSON, default=list)  # Белые ключевые слова для фильтрации
    fl_allow_negotiable: Mapped[bool] = mapped_column(Boolean, default=True)  # Принимать по договоренности
    fl_hide_pro: Mapped[bool] = mapped_column(Boolean, default=False)  # Скрывать только для PRO
    fl_urgent_only: Mapped[bool] = mapped_column(Boolean, default=False)  # Только срочные
    maps_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    maps_only_with_telegram: Mapped[bool] = mapped_column(Boolean, default=False)  # Только с TG
    maps_source_filter: Mapped[str] = mapped_column(String(50), default="all")  # all / yandex / 2gis
    maps_only_without_site: Mapped[bool] = mapped_column(Boolean, default=False)  # Только без сайта
    maps_only_without_ssl: Mapped[bool] = mapped_column(Boolean, default=False)  # Только без SSL
    notify_sound: Mapped[bool] = mapped_column(Boolean, default=True)  # Звуковые уведомления
    notify_captcha: Mapped[bool] = mapped_column(Boolean, default=True)  # Оповещения о капче
    default_limit: Mapped[int] = mapped_column(Integer, default=50)  # Лимит сбора по умолчанию
    fl_live_mode: Mapped[bool] = mapped_column(Boolean, default=True)  # Live-режим мониторинга FL.ru (15-20 сек)

    user: Mapped["TelegramUser"] = relationship("TelegramUser", back_populates="settings")


class FLOrderDelivery(Base):
    """История отправки заказов конкретным Telegram пользователям"""
    __tablename__ = "fl_order_deliveries"

    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("fl_orders.id", ondelete="CASCADE"), primary_key=True)
    chat_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    is_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class User(Base):
    """Пользователь веб-приложения с собственной системой аутентификации"""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="admin", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Demo trial limits and tracking
    demo_searches_left: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    max_companies_per_search: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    last_search_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    tg_user_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)


# ====================================================================
# AI SDR & Outreach Models (CastleWeb)
# ====================================================================

class OutreachAccountStatus:
    WARMUP = "WARMUP"           # В процессе прогрева
    ACTIVE = "ACTIVE"           # Готов к рассылке
    COOLDOWN = "COOLDOWN"       # Дневной лимит достигнут
    SPAMBLOCKED = "SPAMBLOCKED" # Ограничен Telegram
    DISABLED = "DISABLED"       # Отключен вручную


class DialogStatus:
    PENDING = "PENDING"                 # В очереди на первое касание
    PITCH_SENT = "PITCH_SENT"           # Первое сообщение отправлено
    FOLLOWUP_1_SENT = "FOLLOWUP_1_SENT" # Отправлен Follow-up 1
    FOLLOWUP_2_SENT = "FOLLOWUP_2_SENT" # Отправлен Follow-up 2
    REPLIED = "REPLIED"                 # Клиент ответил (в обработке)
    QUALIFYING = "QUALIFYING"           # Идет уточнение (вопрос о компании/баге)
    NEEDS_HUMAN = "NEEDS_HUMAN"         # ПЕРЕДАН ЧЕЛОВЕКУ (Горячий интерес)
    CLOSED_WON = "CLOSED_WON"           # Сделка закрыта
    CLOSED_REJECTED = "CLOSED_REJECTED" # Клиент отказался
    ARCHIVED_NO_REPLY = "ARCHIVED_NO_REPLY" # Не ответил на всю цепочку


class OutreachAccount(Base):
    """Рабочий Telegram MTProto аккаунт в пуле"""
    __tablename__ = "outreach_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    phone: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    session_string: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    proxy_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    status: Mapped[str] = mapped_column(String(50), default=OutreachAccountStatus.WARMUP)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=True)
    daily_limit: Mapped[int] = mapped_column(Integer, default=18)
    sent_today: Mapped[int] = mapped_column(Integer, default=0)
    
    warmup_stage: Mapped[int] = mapped_column(Integer, default=1)
    spambot_checked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    dialogs: Mapped[List["OutreachDialog"]] = relationship("OutreachDialog", back_populates="account")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "phone": self.phone,
            "proxy_url": self.proxy_url,
            "status": self.status,
            "is_premium": self.is_premium,
            "daily_limit": self.daily_limit,
            "sent_today": self.sent_today,
            "warmup_stage": self.warmup_stage,
            "spambot_checked_at": self.spambot_checked_at.isoformat() if self.spambot_checked_at else None,
            "last_sent_at": self.last_sent_at.isoformat() if self.last_sent_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class OutreachCampaign(Base):
    """Кампания пакетной рассылки"""
    __tablename__ = "outreach_campaigns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    filter_city: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    filter_niche: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    filter_min_rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    target_limit: Mapped[int] = mapped_column(Integer, default=50)
    sent_count: Mapped[int] = mapped_column(Integer, default=0)
    replied_count: Mapped[int] = mapped_column(Integer, default=0)
    leads_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(50), default="PENDING")  # PENDING, RUNNING, PAUSED, COMPLETED
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    dialogs: Mapped[List["OutreachDialog"]] = relationship("OutreachDialog", back_populates="campaign")


class OutreachDialog(Base):
    """Диалог с конкретной организацией или контактом"""
    __tablename__ = "outreach_dialogs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    campaign_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("outreach_campaigns.id", ondelete="SET NULL"), nullable=True, index=True)
    org_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True)
    account_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("outreach_accounts.id", ondelete="SET NULL"), nullable=True, index=True)
    
    client_tg_username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    client_tg_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    client_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    company_name: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    website_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    
    status: Mapped[str] = mapped_column(String(50), default=DialogStatus.PENDING, index=True)
    ai_locked: Mapped[bool] = mapped_column(Boolean, default=False)  # True = боту запрещено писать (человек у руля)
    is_test: Mapped[bool] = mapped_column(Boolean, default=False)    # Тестовый аутрич
    
    pitch_text: Mapped[str] = mapped_column(Text, nullable=False)
    defect_screenshot_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Временные метки касаний для Follow-up движка
    pitch_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_client_reply_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    next_followup_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    followup_count: Mapped[int] = mapped_column(Integer, default=0)
    
    last_intent: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    intent_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    account: Mapped[Optional["OutreachAccount"]] = relationship("OutreachAccount", back_populates="dialogs")
    campaign: Mapped[Optional["OutreachCampaign"]] = relationship("OutreachCampaign", back_populates="dialogs")
    organization: Mapped[Optional["Organization"]] = relationship("Organization")
    messages: Mapped[List["OutreachMessage"]] = relationship("OutreachMessage", back_populates="dialog", cascade="all, delete-orphan", order_by="OutreachMessage.sent_at")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "campaign_id": self.campaign_id,
            "org_id": self.org_id,
            "account_id": self.account_id,
            "client_tg_username": self.client_tg_username,
            "client_tg_id": self.client_tg_id,
            "client_phone": self.client_phone,
            "company_name": self.company_name or (self.organization.name if self.organization else None),
            "website_url": self.website_url or (self.organization.website if self.organization else None),
            "status": self.status,
            "ai_locked": self.ai_locked,
            "is_test": self.is_test,
            "pitch_text": self.pitch_text,
            "defect_screenshot_path": self.defect_screenshot_path,
            "pitch_sent_at": self.pitch_sent_at.isoformat() if self.pitch_sent_at else None,
            "last_client_reply_at": self.last_client_reply_at.isoformat() if self.last_client_reply_at else None,
            "next_followup_at": self.next_followup_at.isoformat() if self.next_followup_at else None,
            "followup_count": self.followup_count,
            "last_intent": self.last_intent,
            "intent_confidence": self.intent_confidence,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class OutreachMessage(Base):
    """История каждого сообщения в рамках переписки"""
    __tablename__ = "outreach_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dialog_id: Mapped[int] = mapped_column(Integer, ForeignKey("outreach_dialogs.id", ondelete="CASCADE"), index=True, nullable=False)
    
    sender_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "bot" | "client" | "manager" | "system"
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    media_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    tg_message_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    dialog: Mapped["OutreachDialog"] = relationship("OutreachDialog", back_populates="messages")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "dialog_id": self.dialog_id,
            "sender_type": self.sender_type,
            "message_text": self.message_text,
            "media_url": self.media_url,
            "tg_message_id": self.tg_message_id,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
        }


class OutreachBlacklist(Base):
    """Глобальный стоп-лист (номера, username, домены, которые отказались)"""
    __tablename__ = "outreach_blacklist"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    identifier: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)  # телефон, username или домен
    reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class OutreachPrompt(Base):
    """Настраиваемые промпты нейросети (для редактирования через Telegram-бота)"""
    __tablename__ = "outreach_prompts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    prompt_key: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

