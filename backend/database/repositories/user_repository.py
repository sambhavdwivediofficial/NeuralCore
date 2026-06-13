# database/repositories/user_repository.py
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from database.base import BaseRepository
from database.models.user import User


class UserRepository(BaseRepository[User]):
    model = User

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(select(User).where(User.email == email.lower()))
        return result.scalar_one_or_none()

    async def get_by_oauth(self, provider: str, subject: str) -> User | None:
        result = await self.session.execute(
            select(User).where(User.oauth_provider == provider, User.oauth_subject == subject)
        )
        return result.scalar_one_or_none()

    async def get_by_verification_token(self, token: str) -> User | None:
        result = await self.session.execute(select(User).where(User.verification_token == token))
        return result.scalar_one_or_none()

    async def get_by_password_reset_token(self, token: str) -> User | None:
        result = await self.session.execute(select(User).where(User.password_reset_token == token))
        return result.scalar_one_or_none()

    async def increment_failed_attempts(self, user: User) -> User:
        user.failed_login_attempts += 1
        await self.session.flush()
        return user

    async def reset_failed_attempts(self, user: User) -> User:
        user.failed_login_attempts = 0
        user.locked_until = None
        await self.session.flush()
        return user

    async def lock_account(self, user: User, until: datetime) -> User:
        user.locked_until = until
        await self.session.flush()
        return user

    async def update_last_login(self, user: User) -> User:
        user.last_login_at = datetime.now(timezone.utc)
        await self.session.flush()
        return user

    async def list_by_organization(
        self, organization_id: uuid.UUID, offset: int = 0, limit: int = 20
    ) -> list[User]:
        result = await self.session.execute(
            select(User)
            .where(User.organization_id == organization_id)
            .order_by(User.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())