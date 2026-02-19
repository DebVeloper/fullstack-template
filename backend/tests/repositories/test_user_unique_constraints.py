import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


async def test_duplicate_google_sub_raises_integrity_error(
    db_session: AsyncSession,
) -> None:
    first_user = User(
        google_sub="duplicate-google-sub",
        email="first-google-sub@example.com",
        name="First",
        picture_url="https://example.com/first.png",
        is_active=True,
    )
    duplicate_user = User(
        google_sub="duplicate-google-sub",
        email="second-google-sub@example.com",
        name="Second",
        picture_url="https://example.com/second.png",
        is_active=True,
    )
    db_session.add(first_user)
    await db_session.flush()

    db_session.add(duplicate_user)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_duplicate_email_raises_integrity_error(db_session: AsyncSession) -> None:
    first_user = User(
        google_sub="first-email-sub",
        email="duplicate-email@example.com",
        name="First Email",
        picture_url="https://example.com/first-email.png",
        is_active=True,
    )
    duplicate_user = User(
        google_sub="second-email-sub",
        email="duplicate-email@example.com",
        name="Second Email",
        picture_url="https://example.com/second-email.png",
        is_active=True,
    )
    db_session.add(first_user)
    await db_session.flush()

    db_session.add(duplicate_user)
    with pytest.raises(IntegrityError):
        await db_session.flush()
