from pathlib import Path
import subprocess
import sys

from app.core.config import Settings
from app.db.base import Base

EXPECTED_NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(column_0_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def test_settings_accepts_database_url(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'settings.db'}"

    settings = Settings(DATABASE_URL=database_url)

    assert settings.database_url == database_url


def test_sqlite_engine_enables_foreign_keys(tmp_path: Path) -> None:
    from app.db.session import create_db_engine

    engine = create_db_engine(f"sqlite:///{tmp_path / 'engine.db'}")

    with engine.connect() as connection:
        enabled = connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one()

    engine.dispose()
    assert enabled == 1


def test_importing_base_does_not_create_session_engine() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; import app.db.base; print('app.db.session' in sys.modules)",
        ],
        cwd=Path(__file__).parents[1],
        capture_output=True,
        text=True,
        check=True,
    )

    assert completed.stdout.strip() == "False"


def test_base_uses_stable_constraint_naming_convention() -> None:
    assert dict(Base.metadata.naming_convention) == EXPECTED_NAMING_CONVENTION
