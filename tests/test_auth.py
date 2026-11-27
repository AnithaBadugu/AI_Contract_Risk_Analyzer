import pytest

from src.auth import (
    UsernameAlreadyExistsError,
    authenticate_user,
    initialize_database,
    register_user,
)


def test_registers_users_and_authenticates_case_insensitively(tmp_path):
    database = tmp_path / "users.sqlite3"
    initialize_database(database)

    username = register_user("Anitha_1", "safe-long-password-123", database)

    assert username == "anitha_1"
    assert authenticate_user("ANITHA_1", "safe-long-password-123", database)
    assert not authenticate_user("anitha_1", "wrong-password", database)
    assert not authenticate_user("unknown_user", "safe-long-password-123", database)

    with pytest.raises(UsernameAlreadyExistsError):
        register_user("anitha_1", "another-safe-password", database)


def test_registration_rejects_invalid_username_and_short_password():
    with pytest.raises(ValueError, match="Username must be"):
        register_user("bad username", "safe-long-password-123")

    with pytest.raises(ValueError, match="at least"):
        register_user("valid_user", "short")
