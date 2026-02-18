from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.user_repository import user_repository


async def test_get_by_email_returns_matching_user(db_session: AsyncSession) -> None:
    user = User(
        google_sub="google-sub-001",
        email="lookup-email@example.com",
        name="Email Lookup",
        picture_url="https://example.com/email.png",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    found = await user_repository.get_by_email(db_session, email=user.email)

    assert found is not None
    assert found.id == user.id
    assert found.google_sub == "google-sub-001"


async def test_get_by_google_sub_returns_matching_user(
    db_session: AsyncSession,
) -> None:
    user = User(
        google_sub="google-sub-lookup",
        email="lookup-sub@example.com",
        name="Sub Lookup",
        picture_url="https://example.com/sub.png",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    found = await user_repository.get_by_google_sub(
        db_session, google_sub=user.google_sub
    )

    assert found is not None
    assert found.id == user.id
    assert found.email == "lookup-sub@example.com"
