import hashlib
import hmac
import os
import re
import secrets
import sqlite3
from contextlib import closing
from pathlib import Path


PASSWORD_HASH_ITERATIONS = 600_000
PASSWORD_MIN_LENGTH = 12
PASSWORD_MAX_LENGTH = 128
USERNAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_.-]{2,31}$")
DUMMY_SALT = "7f3b9c2a1d5e8f604b7a9c1d3e5f7082"
DEFAULT_DATABASE_PATH = Path(
    os.environ.get(
        "CONTRACT_ANALYZER_DB_PATH",
        str(Path(__file__).resolve().parent.parent / "data" / "users.sqlite3"),
    )
).expanduser()


class UsernameAlreadyExistsError(ValueError):
    pass


def hash_password(password: str, salt: str) -> str:
    salt_bytes = bytes.fromhex(salt)
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt_bytes,
        PASSWORD_HASH_ITERATIONS,
    ).hex()


def verify_password(password: str, salt: str, expected_hash: str) -> bool:
    try:
        actual_hash = hash_password(password, salt)
    except ValueError:
        return False
    return hmac.compare_digest(actual_hash, expected_hash.lower())


def initialize_database(db_path: Path | str = DEFAULT_DATABASE_PATH) -> None:
    database_path = Path(db_path)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(database_path)) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY COLLATE NOCASE,
                password_salt TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.commit()


def _normalize_username(username: str) -> str:
    normalized = username.strip().lower()
    if not USERNAME_PATTERN.fullmatch(normalized):
        raise ValueError(
            "Username must be 3 to 32 characters and use letters, numbers, "
            "periods, underscores, or hyphens."
        )
    return normalized


def register_user(
    username: str,
    password: str,
    db_path: Path | str = DEFAULT_DATABASE_PATH,
) -> str:
    normalized_username = _normalize_username(username)
    if len(password) < PASSWORD_MIN_LENGTH:
        raise ValueError(
            f"Password must be at least {PASSWORD_MIN_LENGTH} characters."
        )
    if len(password) > PASSWORD_MAX_LENGTH:
        raise ValueError(
            f"Password must be no more than {PASSWORD_MAX_LENGTH} characters."
        )

    salt = secrets.token_hex(16)
    password_hash = hash_password(password, salt)
    try:
        with closing(sqlite3.connect(db_path)) as connection:
            with connection:
                connection.execute(
                    """
                    INSERT INTO users (username, password_salt, password_hash)
                    VALUES (?, ?, ?)
                    """,
                    (normalized_username, salt, password_hash),
                )
    except sqlite3.IntegrityError as exc:
        raise UsernameAlreadyExistsError(
            "That username is already registered."
        ) from exc
    return normalized_username


def authenticate_user(
    username: str,
    password: str,
    db_path: Path | str = DEFAULT_DATABASE_PATH,
) -> bool:
    normalized_username = username.strip().lower()
    if len(normalized_username) > 32 or len(password) > PASSWORD_MAX_LENGTH:
        hash_password(password[:PASSWORD_MAX_LENGTH], DUMMY_SALT)
        return False

    with closing(sqlite3.connect(db_path)) as connection:
        row = connection.execute(
            "SELECT password_salt, password_hash FROM users WHERE username = ?",
            (normalized_username,),
        ).fetchone()

    if row is None:
        hash_password(password, DUMMY_SALT)
        return False
    return verify_password(password, row[0], row[1])
