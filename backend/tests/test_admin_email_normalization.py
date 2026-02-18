from app.api.v1.endpoints.users import is_admin_email, normalize_email


def test_normalize_email_trims_whitespace_and_casefolds() -> None:
    assert normalize_email("  Admin@Example.COM  ") == "admin@example.com"


def test_is_admin_email_compares_case_insensitive_trimmed_values() -> None:
    assert is_admin_email(
        user_email=" admin@example.com ",
        admin_email="ADMIN@EXAMPLE.COM",
    )


def test_is_admin_email_returns_false_for_non_matching_emails() -> None:
    assert not is_admin_email(
        user_email="member@example.com",
        admin_email="admin@example.com",
    )
