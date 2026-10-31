"""
Creates an admin account (or promotes an existing user). The admin then logs in
with the normal phone + OTP flow.

    python -m scripts.create_admin --phone 03001234567 --name "Umer"
"""

import argparse
import asyncio

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import normalize_pakistan_phone
from app.models.enums import UserRole
from app.models.user import User


async def create_admin(phone: str, name: str | None, role: UserRole) -> None:
    phone = normalize_pakistan_phone(phone)
    async with SessionLocal() as db:
        user = (await db.execute(select(User).where(User.phone == phone))).scalar_one_or_none()
        if user is None:
            user = User(phone=phone, full_name=name)
            db.add(user)
        user.role = role
        user.is_active = True
        if name:
            user.full_name = name
        await db.commit()
        print(f"{phone} is now {role}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--phone", required=True)
    parser.add_argument("--name")
    parser.add_argument("--role", choices=[UserRole.ADMIN, UserRole.STAFF], default=UserRole.ADMIN)
    args = parser.parse_args()
    asyncio.run(create_admin(args.phone, args.name, UserRole(args.role)))
