#!/usr/bin/env python3
"""
Утилита управления пользователями LeadHunter Pro
Использование:
  python manage_users.py list
  python manage_users.py add <email> <password> [role]
  python manage_users.py passwd <email> <new_password>
  python manage_users.py delete <email>
  python manage_users.py (интерактивный режим)
"""
import sys
import os
import asyncio
from datetime import datetime, timezone

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from sqlalchemy import select, delete
from app.db.database import async_session_factory, init_db
from app.db.models import User
from app.core.security import hash_password

CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"

async def list_users():
    await init_db()
    async with async_session_factory() as session:
        users = (await session.execute(select(User).order_by(User.id))).scalars().all()
        if not users:
            print(f"{YELLOW}Пользователи в базе данных не найдены.{RESET}")
            return

        print(f"\n{CYAN}{BOLD}Список пользователей LeadHunter Pro:{RESET}")
        print("-" * 75)
        print(f"{BOLD}{'ID':<4} {'Email':<30} {'Роль':<10} {'Активен':<9} {'Последний вход':<18}{RESET}")
        print("-" * 75)
        for u in users:
            last_login = u.last_login_at.strftime("%Y-%m-%d %H:%M") if u.last_login_at else "Никогда"
            active_str = f"{GREEN}Да{RESET}" if u.is_active else f"{RED}Нет{RESET}"
            print(f"{u.id:<4} {u.email:<30} {u.role:<10} {active_str:<18} {last_login}")
        print("-" * 75)
        print(f"Всего пользователей: {len(users)}\n")

async def add_user(email: str, password: str, role: str = "admin"):
    await init_db()
    email = email.strip().lower()
    if not email or "@" not in email:
        print(f"{RED}[ОШИБКА] Некорректный email адрес.{RESET}")
        return

    if len(password) < 6:
        print(f"{RED}[ОШИБКА] Пароль должен содержать минимум 6 символов.{RESET}")
        return

    async with async_session_factory() as session:
        existing = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
        if existing:
            print(f"{YELLOW}[ПРЕДУПРЕЖДЕНИЕ] Пользователь с email {email} уже существует (ID: {existing.id})!{RESET}")
            return

        new_user = User(
            email=email,
            password_hash=hash_password(password),
            role=role,
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
        session.add(new_user)
        await session.commit()
        print(f"{GREEN}{BOLD}[✓] Пользователь {email} успешно создан! (Роль: {role}){RESET}")

async def change_password(email: str, new_password: str):
    await init_db()
    email = email.strip().lower()
    if len(new_password) < 6:
        print(f"{RED}[ОШИБКА] Новый пароль должен содержать минимум 6 символов.{RESET}")
        return

    async with async_session_factory() as session:
        user = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
        if not user:
            print(f"{RED}[ОШИБКА] Пользователь {email} не найден!{RESET}")
            return

        user.password_hash = hash_password(new_password)
        await session.commit()
        print(f"{GREEN}{BOLD}[✓] Пароль для {email} успешно обновлен!{RESET}")

async def delete_user(email: str):
    await init_db()
    email = email.strip().lower()
    async with async_session_factory() as session:
        user = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
        if not user:
            print(f"{RED}[ОШИБКА] Пользователь {email} не найден!{RESET}")
            return

        await session.execute(delete(User).where(User.email == email))
        await session.commit()
        print(f"{GREEN}[✓] Пользователь {email} (ID: {user.id}) успешно удален.{RESET}")

async def interactive_menu():
    while True:
        print(f"{CYAN}{BOLD}======================================================================{RESET}")
        print(f"{CYAN}{BOLD}       👥 УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ (LEADHUNTER PRO)                  {RESET}")
        print(f"{CYAN}{BOLD}======================================================================{RESET}")
        print(f"  {BOLD}[1]{RESET} Список пользователей")
        print(f"  {BOLD}[2]{RESET} Добавить нового пользователя")
        print(f"  {BOLD}[3]{RESET} Сменить пароль пользователю")
        print(f"  {BOLD}[4]{RESET} Удалить пользователя")
        print(f"  {BOLD}[0]{RESET} Выход")
        print(f"{CYAN}{BOLD}======================================================================{RESET}")

        choice = input(f"{BOLD}Выберите действие [1/2/3/4/0]: {RESET}").strip()
        if choice == "1":
            await list_users()
        elif choice == "2":
            email = input(f"{BOLD}Введите Email нового пользователя: {RESET}").strip()
            password = input(f"{BOLD}Введите Пароль: {RESET}").strip()
            role = input(f"{BOLD}Роль [admin/user, по умолчанию: admin]: {RESET}").strip() or "admin"
            await add_user(email, password, role)
        elif choice == "3":
            email = input(f"{BOLD}Введите Email пользователя: {RESET}").strip()
            new_password = input(f"{BOLD}Введите Новый пароль: {RESET}").strip()
            await change_password(email, new_password)
        elif choice == "4":
            email = input(f"{BOLD}Введите Email для удаления: {RESET}").strip()
            confirm = input(f"{RED}Вы уверены, что хотите удалить {email}? [y/N]: {RESET}").strip()
            if confirm.lower() in ("y", "yes", "д", "да"):
                await delete_user(email)
        elif choice == "0":
            break
        else:
            print(f"{YELLOW}Неверный ввод, повторите попытку.{RESET}")

def main():
    args = sys.argv[1:]
    if not args:
        asyncio.run(interactive_menu())
        return

    cmd = args[0].lower()
    if cmd in ("list", "ls"):
        asyncio.run(list_users())
    elif cmd in ("add", "create"):
        if len(args) < 3:
            print("Использование: python manage_users.py add <email> <password> [role]")
            sys.exit(1)
        role = args[3] if len(args) > 3 else "admin"
        asyncio.run(add_user(args[1], args[2], role))
    elif cmd in ("passwd", "password"):
        if len(args) < 3:
            print("Использование: python manage_users.py passwd <email> <new_password>")
            sys.exit(1)
        asyncio.run(change_password(args[1], args[2]))
    elif cmd in ("del", "delete", "rm"):
        if len(args) < 2:
            print("Использование: python manage_users.py delete <email>")
            sys.exit(1)
        asyncio.run(delete_user(args[1]))
    else:
        print(f"Неизвестная команда: {cmd}")
        print("Доступные команды: list, add, passwd, delete")
        sys.exit(1)

if __name__ == "__main__":
    main()
