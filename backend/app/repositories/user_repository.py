from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    async def get_by_id(self, db: AsyncSession, user_id: UUID) -> User | None:
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, db: AsyncSession, email: str) -> User | None:
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_google_sub(self, db: AsyncSession, google_sub: str) -> User | None:
        result = await db.execute(select(User).where(User.google_sub == google_sub))
        return result.scalar_one_or_none()

    async def list_users(
        self,
        db: AsyncSession,
        *,
        page: int,
        size: int,
    ) -> list[User]:
        query = select(User).where(User.deleted_at.is_(None))

        offset = (page - 1) * size
        result = await db.execute(
            query.order_by(User.created_at.desc()).offset(offset).limit(size)
        )
        return list(result.scalars().all())

    async def count_users(
        self,
        db: AsyncSession,
    ) -> int:
        query = select(func.count()).select_from(User).where(User.deleted_at.is_(None))

        result = await db.execute(query)
        return int(result.scalar_one())

    async def set_active_status(
        self,
        db: AsyncSession,
        *,
        user: User,
        is_active: bool,
    ) -> User:
        user.is_active = is_active
        await db.flush()
        await db.refresh(user)
        return user

    async def delete(self, db: AsyncSession, *, user: User) -> User:
        await db.delete(user)
        await db.flush()
        return user

    async def upsert_google_user(
        self,
        db: AsyncSession,
        *,
        google_sub: str,
        email: str,
        name: str,
        picture_url: str | None,
    ) -> User:
        user = await self.get_by_google_sub(db, google_sub=google_sub)
        if user is None:
            user = User(
                google_sub=google_sub,
                email=email,
                name=name,
                picture_url=picture_url,
                is_active=True,
            )
            db.add(user)
        else:
            user.email = email
            user.name = name
            user.picture_url = picture_url

        await db.flush()
        return user


user_repository = UserRepository()
