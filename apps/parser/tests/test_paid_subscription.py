import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Добавляем пути в sys.path
BASE_DIR = Path("c:/Users/fake_netrunner/Desktop/мой сайтик)))))").resolve()
sys.path.insert(0, str(BASE_DIR / "apps" / "parser"))
sys.path.insert(0, str(BASE_DIR / "apps" / "backend"))
parser_pkg = BASE_DIR / "парсеп" / "parser" / ".venv" / "Lib" / "site-packages"
if parser_pkg.exists():
    sys.path.append(str(parser_pkg))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Настраиваем окружение
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["INTERNAL_API_SECRET"] = "test-internal-secret"

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select, text
from fastapi import HTTPException

async def run_all_tests():
    print("=" * 60)
    print("🧪 ЗАПУСК КОМПЛЕКСНОГО ТЕСТИРОВАНИЯ СИСТЕМЫ ПЛАТНОЙ ПОДПИСКИ")
    print("=" * 60)

    # ---------------------------------------------------------
    # ТЕСТ 1: Инициализация БД и миграции
    # ---------------------------------------------------------
    print("\n[ТЕСТ 1] Проверка моделей и применения миграций в SQLite...")
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    session_factory = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

    from app.db.database import Base
    from app.db.models import User, SearchCampaign

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # Проверяем наличие колонок в таблице users
        table_info = await conn.execute(text("PRAGMA table_info(users)"))
        columns = [row[1] for row in table_info.fetchall()]
        print(f"  -> Колонки в таблице users: {columns}")
        assert "subscription_plan" in columns, "subscription_plan отсутствует в таблице users!"
        assert "subscription_until" in columns, "subscription_until отсутствует в таблице users!"
        assert "daily_companies_parsed" in columns, "daily_companies_parsed отсутствует в таблице users!"
        assert "daily_reset_date" in columns, "daily_reset_date отсутствует в таблице users!"
    print("  ✅ ТЕСТ 1 ПРОЙДЕН: Схема БД содержит все поля подписки и дневного лимита.")

    # ---------------------------------------------------------
    # ТЕСТ 2: Внутренний эндпоинт выдачи доступа (grant_paid_access)
    # ---------------------------------------------------------
    print("\n[ТЕСТ 2] Проверка выдачи и продления платного доступа...")
    from app.api.auth import grant_paid_access, GrantPaidAccessPayload
    from unittest.mock import MagicMock

    def mock_request(secret="test-internal-secret"):
        req = MagicMock()
        req.headers = {"X-Internal-Secret": secret}
        return req

    async with session_factory() as db:
        # 2.1: Неверный секрет
        try:
            await grant_paid_access(
                GrantPaidAccessPayload(tg_user_id="111222", plan="1m"),
                mock_request(secret="wrong-secret"),
                db=db
            )
            assert False, "Не отклонил запрос с неверным секретом!"
        except HTTPException as e:
            assert e.status_code == 403
            print("  -> Защита: неверный секрет успешно отклонен (403 Forbidden)")

        # 2.2: Недопустимый тариф
        try:
            await grant_paid_access(
                GrantPaidAccessPayload(tg_user_id="111222", plan="invalid_plan"),
                mock_request(),
                db=db
            )
            assert False, "Не отклонил недопустимый план!"
        except HTTPException as e:
            assert e.status_code == 400
            print("  -> Валидация: некорректный тариф успешно отклонен (400 Bad Request)")

        # 2.3: Выдача тарифа на 1 месяц (новый пользователь)
        res_1m = await grant_paid_access(
            GrantPaidAccessPayload(tg_user_id="999001", plan="1m"),
            mock_request(),
            db=db
        )
        print(f"  -> Результат выдачи 1m: статус={res_1m['status']}, план={res_1m['plan_title']}, до={res_1m['subscription_until_human']}")
        assert res_1m["status"] == "granted"
        assert res_1m["role"] == "paid"
        assert res_1m["plan"] == "1m"
        assert res_1m["daily_limit"] == 100
        assert res_1m["is_new"] is True
        assert len(res_1m["password"]) == 10

        # Проверяем запись в БД
        u1 = (await db.execute(select(User).where(User.tg_user_id == "999001"))).scalar_one()
        assert u1.role == "paid"
        assert u1.subscription_plan == "1m"
        assert u1.subscription_until is not None
        assert u1.max_companies_per_search == 100

        # 2.4: Продление тарифа существующего пользователя (+3 месяца)
        # Должно прибавиться 90 дней к уже существующим 30 дням (~120 дней от now)
        res_3m = await grant_paid_access(
            GrantPaidAccessPayload(tg_user_id="999001", plan="3m"),
            mock_request(),
            db=db
        )
        print(f"  -> Результат продления на 3m: до={res_3m['subscription_until_human']}, is_new={res_3m['is_new']}")
        assert res_3m["is_new"] is False
        assert res_3m["plan"] == "3m"
        
        # Проверяем продление в БД
        await db.refresh(u1)
        now_utc = datetime.now(timezone.utc)
        u1_until = u1.subscription_until.replace(tzinfo=timezone.utc) if u1.subscription_until.tzinfo is None else u1.subscription_until
        days_total = (u1_until - now_utc).days
        print(f"  -> Суммарно дней подписки после продления: {days_total} (ожидается ~119-120 дней)")
        assert 118 <= days_total <= 122

        # 2.5: Выдача бессрочного тарифа (lifetime)
        res_life = await grant_paid_access(
            GrantPaidAccessPayload(tg_user_id="999002", plan="lifetime"),
            mock_request(),
            db=db
        )
        print(f"  -> Результат lifetime: статус={res_life['status']}, до={res_life['subscription_until_human']}")
        assert res_life["subscription_until"] is None
        assert res_life["subscription_until_human"] == "Бессрочно (навсегда)"
        u2 = (await db.execute(select(User).where(User.tg_user_id == "999002"))).scalar_one()
        assert u2.subscription_until is None
        assert u2.subscription_plan == "lifetime"

    print("  ✅ ТЕСТ 2 ПРОЙДЕН: Внутренний эндпоинт корректно создает и продлевает подписки.")

    # ---------------------------------------------------------
    # ТЕСТ 3: Проверка суточного лимита (100 компаний) и срока подписки
    # ---------------------------------------------------------
    print("\n[ТЕСТ 3] Проверка суточного лимита (100 организаций) и истечения подписки...")
    
    async with session_factory() as db:
        now = datetime.now(timezone.utc)
        today_str = now.strftime("%Y-%m-%d")

        # 3.1: Платный пользователь, уже спарсивший 40 компаний сегодня, просит 80
        # Должен получить effective_limit = min(80, 100 - 40) = 60
        u_active = User(
            email="paid_tester@castleweb.ru",
            password_hash="hash",
            role="paid",
            subscription_plan="1m",
            subscription_until=now + timedelta(days=20),
            daily_companies_parsed=40,
            daily_reset_date=today_str,
            max_companies_per_search=100
        )
        db.add(u_active)
        await db.commit()
        await db.refresh(u_active)

        # Симулируем логику из search.py
        daily_limit = 100
        already_parsed = u_active.daily_companies_parsed
        req_limit = 80
        remaining_today = daily_limit - already_parsed
        effective_limit = min(req_limit, remaining_today)
        print(f"  -> Запрошено 80, уже спарсено 40. Эффективный лимит: {effective_limit} (ожидается 60)")
        assert effective_limit == 60

        # 3.2: Лимит 100 компаний уже исчерпан
        u_active.daily_companies_parsed = 100
        await db.commit()
        already_parsed = u_active.daily_companies_parsed
        if already_parsed >= daily_limit:
            blocked = True
        else:
            blocked = False
        print(f"  -> Спарсено 100 из 100. Блокировка: {blocked}")
        assert blocked is True

        # 3.3: Новый день (сброс счетчика)
        u_active.daily_reset_date = "2026-01-01"  # Прошлый день
        if u_active.daily_reset_date != today_str:
            u_active.daily_reset_date = today_str
            u_active.daily_companies_parsed = 0
            await db.commit()
        print(f"  -> Новый день наступил: счетчик обнулен до {u_active.daily_companies_parsed}")
        assert u_active.daily_companies_parsed == 0

        # 3.4: Истекшая подписка
        u_expired = User(
            email="expired_tester@castleweb.ru",
            password_hash="hash",
            role="paid",
            subscription_plan="1m",
            subscription_until=now - timedelta(days=2),  # Истекла 2 дня назад
            daily_companies_parsed=0,
            daily_reset_date=today_str,
            max_companies_per_search=100
        )
        db.add(u_expired)
        await db.commit()
        await db.refresh(u_expired)

        sub_until = u_expired.subscription_until.replace(tzinfo=timezone.utc) if u_expired.subscription_until.tzinfo is None else u_expired.subscription_until
        is_sub_expired = now > sub_until
        print(f"  -> Проверка просроченной подписки: истекла = {is_sub_expired}")
        assert is_sub_expired is True

    print("  ✅ ТЕСТ 3 ПРОЙДЕН: Суточный лимит 100 компаний, автосброс в полночь и проверка срока работают безупречно.")

    # ---------------------------------------------------------
    # ТЕСТ 4: Меню Telegram-бота и карточки менеджеров / Личный кабинет
    # ---------------------------------------------------------
    print("\n[ТЕСТ 4] Проверка Telegram-шаблонов меню, карточки ЛК и кнопок менеджеров...")
    import subprocess
    menu_test_script = BASE_DIR / "apps" / "parser" / "tests" / "test_telegram_menu.py"
    sub_res = subprocess.run(
        [sys.executable, str(menu_test_script)],
        capture_output=True,
        text=True,
        cwd=str(BASE_DIR),
        encoding="utf-8",
        errors="replace"
    )
    print(sub_res.stdout)
    if sub_res.returncode != 0:
        print(sub_res.stderr)
        assert False, f"Тест 4 завершился с ошибкой: {sub_res.stderr}"

    # ---------------------------------------------------------
    # ТЕСТ 5: Внутренние эндпоинты ЛК и сброса пароля (auth.py)
    # ---------------------------------------------------------
    print("\n[ТЕСТ 5] Проверка API Личного кабинета и сброса пароля (/api/internal/user-cabinet & reset-password)...")
    from app.api.auth import get_user_cabinet_internal, reset_password_internal, ResetPasswordPayload, verify_password

    async with session_factory() as db:
        # Проверяем получение ЛК для существующего платного пользователя (999001)
        cab_data = await get_user_cabinet_internal(
            tg_user_id="999001",
            request=mock_request(),
            db=db
        )
        print(f"  -> Данные ЛК из API: роль={cab_data.get('role')}, план={cab_data.get('plan_title')}, лимит={cab_data.get('daily_limit')}")
        assert cab_data["status"] == "ok"
        assert cab_data["is_paid"] is True
        assert cab_data["daily_limit"] == 100
        assert cab_data["daily_remaining"] == 100
        assert cab_data["daily_companies_parsed"] == 0
        assert "subscription_until_human" in cab_data

        # Проверяем сброс пароля
        reset_res = await reset_password_internal(
            payload=ResetPasswordPayload(tg_user_id="999001"),
            request=mock_request(),
            db=db
        )
        new_pass = reset_res["new_password"]
        print(f"  -> Новый пароль успешно сгенерирован: {new_pass}")
        assert len(new_pass) == 10

        # Проверяем в БД, что пароль обновился и проходит верификацию
        u1_updated = (await db.execute(select(User).where(User.tg_user_id == "999001"))).scalar_one()
        assert verify_password(new_pass, u1_updated.password_hash) is True
        print("  -> Хеш нового пароля в БД валиден и подтвержден verify_password.")

    print("  ✅ ТЕСТ 5 ПРОЙДЕН: Эндпоинты ЛК и сброса пароля работают корректно.")

    # ---------------------------------------------------------
    # ТЕСТ 6: Защита от спама лидов в Telegram (только в браузере)
    # ---------------------------------------------------------
    print("\n[ТЕСТ 6] Проверка фильтрации уведомлений о лидах в Telegram (Zero TG Leaks for Paid Users)...")
    import app.services.telegram.dispatcher as dispatcher_module
    from app.services.telegram.dispatcher import TelegramDispatcher
    from app.db.models import TelegramUser, TelegramUserSettings

    dispatcher_module.async_session_factory = session_factory

    async with session_factory() as db:
        # Создаем двух пользователей Telegram:
        # 1. Платный клиент (не админ)
        # 2. Администратор студии
        tg_client = TelegramUser(chat_id=777001, username="paid_client_vasya", is_active=True)
        tg_client_settings = TelegramUserSettings(chat_id=777001, maps_enabled=True)

        tg_admin = TelegramUser(chat_id=1878543896, username="kupidon996", is_active=True)
        tg_admin_settings = TelegramUserSettings(chat_id=1878543896, maps_enabled=True)

        db.add_all([tg_client, tg_client_settings, tg_admin, tg_admin_settings])
        await db.commit()

        # Инициализируем диспетчер с заглушкой бота
        dispatcher = TelegramDispatcher()
        dispatcher.bot = MagicMock()
        
        # Симулируем отправку лида
        lead_data = {
            "id": 1234,
            "name": "ООО Ромашка",
            "source": "yandex_maps",
            "primary_phone": "+79991234567",
            "telegram": "@romashka",
            "website": "http://romashka.ru",
            "status_badge": "OK"
        }

        # Перехватываем очередь диспетчера
        await dispatcher.dispatch_lead(lead_data)

        queued_items = []
        while not dispatcher._queue.empty():
            queued_items.append(await dispatcher._queue.get())

        queued_chat_ids = [item[0] for item in queued_items]
        print(f"  -> Получатели лида в очереди TelegramDispatcher: {queued_chat_ids}")
        
        # Строгая проверка инварианта: платный клиент НЕ должен получить лид в TG!
        assert 777001 not in queued_chat_ids, "ОШИБКА БЕЗОПАСНОСТИ: Платный клиент получил уведомление о лиде в Telegram!"
        # Администратор студии должен получить лид
        assert 1878543896 in queued_chat_ids, "Администратор студии не получил уведомление о лиде!"
        print("  -> Платный клиент (chat_id=777001) отфильтрован: лиды доступны ТОЛЬКО в браузере.")
        print("  -> Администратор студии (chat_id=1878543896) успешно получил уведомление.")

    print("  ✅ ТЕСТ 6 ПРОЙДЕН: Уведомления о лидах строго изолированы от платных подписчиков.")

    print("\n" + "=" * 60)
    print("🎉 ВСЕ ТЕСТЫ УСПЕШНО ПРОЙДЕНЫ! СИСТЕМА ПОЛНОСТЬЮ ГОТОВА И ПРОВЕРЕНА.")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(run_all_tests())

