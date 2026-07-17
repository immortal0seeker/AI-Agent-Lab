from pathlib import Path

from alembic import command
from alembic.config import Config
from pytest import MonkeyPatch
from sqlalchemy import create_engine, inspect

from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).parents[1]


def migration_config() -> Config:
    config = Config()
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    return config


def test_upgrade_head_creates_initial_schema(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    database_path = tmp_path / "migration.db"
    database_url = f"sqlite:///{database_path}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()

    try:
        command.upgrade(migration_config(), "head")
    finally:
        get_settings.cache_clear()

    engine = create_engine(database_url)
    inspector = inspect(engine)

    assert {
        "alembic_version",
        "conversations",
        "messages",
        "llm_calls",
    } <= set(inspector.get_table_names())

    message_foreign_key = inspector.get_foreign_keys("messages")[0]
    llm_call_foreign_keys = {
        foreign_key["referred_table"]: foreign_key
        for foreign_key in inspector.get_foreign_keys("llm_calls")
    }

    assert message_foreign_key["options"]["ondelete"] == "CASCADE"
    assert llm_call_foreign_keys["conversations"]["options"]["ondelete"] == "CASCADE"
    assert llm_call_foreign_keys["messages"]["options"]["ondelete"] == "SET NULL"

    assert inspector.get_pk_constraint("conversations")["name"] == "pk_conversations"
    assert message_foreign_key["name"] == "fk_messages_conversation_id_conversations"
    assert (
        llm_call_foreign_keys["conversations"]["name"]
        == "fk_llm_calls_conversation_id_conversations"
    )
    assert (
        llm_call_foreign_keys["messages"]["name"]
        == "fk_llm_calls_message_id_messages"
    )

    assert {index["name"] for index in inspector.get_indexes("messages")} == {
        "ix_messages_conversation_id",
    }
    assert {index["name"] for index in inspector.get_indexes("llm_calls")} == {
        "ix_llm_calls_conversation_id",
        "ix_llm_calls_message_id",
    }

    engine.dispose()


def test_downgrade_base_removes_initial_schema(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    database_path = tmp_path / "downgrade.db"
    database_url = f"sqlite:///{database_path}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()

    try:
        config = migration_config()
        command.upgrade(config, "head")
        command.downgrade(config, "base")
    finally:
        get_settings.cache_clear()

    engine = create_engine(database_url)
    tables = set(inspect(engine).get_table_names())

    assert "conversations" not in tables
    assert "messages" not in tables
    assert "llm_calls" not in tables

    engine.dispose()
