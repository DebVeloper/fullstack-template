from app.main import app


def test_backend_scaffold_imports() -> None:
    assert app.title == "App"
