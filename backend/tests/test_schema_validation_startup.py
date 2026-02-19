import pytest

import app.core.database as database_module
import app.main as main_module


class FakeResult:
    def __init__(self, rows: list[tuple[str]]) -> None:
        self._rows = rows

    def fetchall(self) -> list[tuple[str]]:
        return self._rows


class FakeConnection:
    def __init__(self, rows: list[tuple[str]]) -> None:
        self._rows = rows

    async def execute(self, _query: object) -> FakeResult:
        return FakeResult(self._rows)


class FakeConnectionContext:
    def __init__(self, rows: list[tuple[str]]) -> None:
        self._rows = rows

    async def __aenter__(self) -> FakeConnection:
        return FakeConnection(self._rows)

    async def __aexit__(
        self,
        _exc_type: object,
        _exc: object,
        _tb: object,
    ) -> None:
        return None


class FakeEngine:
    def __init__(self, rows: list[tuple[str]]) -> None:
        self._rows = rows

    def connect(self) -> FakeConnectionContext:
        return FakeConnectionContext(self._rows)


async def test_validate_database_schema_raises_when_required_tables_are_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        database_module,
        "get_engine",
        lambda: FakeEngine([("alembic_version",)]),
    )

    with pytest.raises(RuntimeError) as exc_info:
        await database_module.validate_database_schema()

    assert "Missing tables: users" in str(exc_info.value)
    assert "uv run alembic upgrade head" in str(exc_info.value)


async def test_validate_database_schema_passes_when_required_tables_exist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        database_module,
        "get_engine",
        lambda: FakeEngine([("users",), ("alembic_version",)]),
    )

    await database_module.validate_database_schema()


async def test_lifespan_validates_database_schema_on_startup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called = False

    async def fake_validate_database_schema() -> None:
        nonlocal called
        called = True

    monkeypatch.setattr(
        main_module,
        "validate_database_schema",
        fake_validate_database_schema,
        raising=False,
    )

    async with main_module.lifespan(main_module.app):
        pass

    assert called is True
