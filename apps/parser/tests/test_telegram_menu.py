import os
import sys
from pathlib import Path

# Добавляем путь backend первым
BASE_DIR = Path("c:/Users/fake_netrunner/Desktop/мой сайтик)))))").resolve()
sys.path.insert(0, str(BASE_DIR / "apps" / "backend"))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.presentation.api.v1.endpoints.telegram_webhook import (
    get_buy_parser_menu,
    get_manager_grant_keyboard,
    format_demo_access_response,
    get_client_main_menu,
    format_user_cabinet
)

def run_tests():
    # 1. Меню покупки
    buy_text, buy_kb = get_buy_parser_menu()
    assert "2 000 ₽" in buy_text
    assert "5 000 ₽" in buy_text
    assert "10 000 ₽" in buy_text
    assert "50 000 ₽" in buy_text
    assert "100" in buy_text
    callbacks = [btn["callback_data"] for row in buy_kb["inline_keyboard"] for btn in row if "callback_data" in btn]
    assert "buy_parser_request" in callbacks
    print("  -> Меню покупки содержит правильные цены (2к/5к/10к/50к) и кнопку заявки.")

    # 2. Кнопки менеджеров
    mgr_kb = get_manager_grant_keyboard(123456789)
    mgr_callbacks = [btn["callback_data"] for row in mgr_kb["inline_keyboard"] for btn in row if "callback_data" in btn]
    print(f"  -> Callback'и в группе менеджеров: {mgr_callbacks}")
    assert "grant_sub:123456789:1m" in mgr_callbacks
    assert "grant_sub:123456789:3m" in mgr_callbacks
    assert "grant_sub:123456789:1y" in mgr_callbacks
    assert "grant_sub:123456789:lifetime" in mgr_callbacks
    assert "decline_sub:123456789" in mgr_callbacks

    # 3. Карточка исчерпанного демо
    exhausted_text, exhausted_kb = format_demo_access_response({"status": "exhausted"}, "https://leads.castleweb.ru")
    ex_callbacks = [btn["callback_data"] for row in exhausted_kb["inline_keyboard"] for btn in row if "callback_data" in btn]
    assert "buy_parser_menu" in ex_callbacks
    print("  -> В карточке исчерпанного демо присутствует кнопка покупки подписки.")

    # 4. Главное меню клиента
    main_text, main_kb = get_client_main_menu("Иван")
    main_callbacks = [btn["callback_data"] for row in main_kb["inline_keyboard"] for btn in row if "callback_data" in btn]
    assert "buy_parser_menu" in main_callbacks
    assert "client_cabinet" in main_callbacks
    print("  -> В главном меню клиента присутствуют кнопки покупки и Личного кабинета LeadHunter.")

    # 5. Проверка рендера карточки Личного кабинета
    cab_info = {
        "status": "ok",
        "email": "user_999001@castleweb.ru",
        "role": "paid",
        "is_paid": True,
        "plan_title": "1 месяц (Стандарт)",
        "subscription_until_human": "15.11.2026",
        "is_expired": False,
        "daily_companies_parsed": 25,
        "daily_limit": 100,
        "daily_remaining": 75
    }
    cab_text, cab_kb = format_user_cabinet(cab_info, "https://leads.castleweb.ru")
    assert "1 месяц (Стандарт)" in cab_text
    assert "user_999001@castleweb.ru" in cab_text
    assert "25" in cab_text
    assert "100" in cab_text
    assert "15.11.2026" in cab_text
    assert ("в браузере" in cab_text) or ("веб-интерфейсе" in cab_text)
    cab_callbacks = [btn["callback_data"] for row in cab_kb["inline_keyboard"] for btn in row if "callback_data" in btn]
    assert "client_cabinet" in cab_callbacks
    assert "cabinet_reset_password" in cab_callbacks
    assert "buy_parser_menu" in cab_callbacks
    print("  -> Карточка Личного кабинета отображает суточный лимит 100, тариф, срок, веб-доступ и кнопки сброса/продления.")
    print("  ✅ ТЕСТ 4 ПРОЙДЕН: Все шаблоны и клавиатуры Telegram согласованы.")

if __name__ == "__main__":
    run_tests()
