from pathlib import Path

from alembic import command
from alembic.config import Config
from pytest import MonkeyPatch
from sqlalchemy import create_engine, inspect

from app.core.config import get_settings


BACKEND_ROOT = Path(__file__).parents[1]


def migration_config(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> tuple[Config, str]:
    database_url = f"sqlite:///{tmp_path / 'agent-migration.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    config = Config()
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    return config, database_url


def test_upgrade_head_creates_agent_persistence_schema(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    config, database_url = migration_config(tmp_path, monkeypatch)
    try:
        command.upgrade(config, "head")
    finally:
        get_settings.cache_clear()

    engine = create_engine(database_url)
    inspector = inspect(engine)
    assert {"agent_runs", "tool_calls"} <= set(inspector.get_table_names())
    assert {column["name"] for column in inspector.get_columns("agent_runs")} == {
        "id",
        "conversation_id",
        "user_message_id",
        "status",
        "goal",
        "final_answer",
        "error_message",
        "started_at",
        "ended_at",
        "latency_ms",
        "created_at",
    }
    assert {column["name"] for column in inspector.get_columns("tool_calls")} == {
        "id",
        "tool_call_id",
        "agent_run_id",
        "conversation_id",
        "tool_name",
        "arguments_json",
        "result_json",
        "status",
        "error_message",
        "started_at",
        "ended_at",
        "latency_ms",
        "created_at",
    }

    agent_foreign_keys = {
        tuple(foreign_key["constrained_columns"]): foreign_key
        for foreign_key in inspector.get_foreign_keys("agent_runs")
    }
    assert (
        agent_foreign_keys[("conversation_id",)]["options"]["ondelete"]
        == "CASCADE"
    )
    assert (
        agent_foreign_keys[("user_message_id",)]["options"]["ondelete"]
        == "SET NULL"
    )

    tool_foreign_key = inspector.get_foreign_keys("tool_calls")[0]
    assert tool_foreign_key["constrained_columns"] == [
        "agent_run_id",
        "conversation_id",
    ]
    assert tool_foreign_key["referred_columns"] == ["id", "conversation_id"]
    assert tool_foreign_key["options"]["ondelete"] == "CASCADE"

    assert {index["name"] for index in inspector.get_indexes("agent_runs")} == {
        "ix_agent_runs_conversation_id",
        "ix_agent_runs_user_message_id",
    }
    assert {index["name"] for index in inspector.get_indexes("tool_calls")} == {
        "ix_tool_calls_agent_run_id",
        "ix_tool_calls_conversation_id",
    }
    assert {
        constraint["name"]
        for constraint in inspector.get_unique_constraints("agent_runs")
    } == {"uq_agent_runs_id_conversation_id"}
    assert {
        constraint["name"]
        for constraint in inspector.get_unique_constraints("tool_calls")
    } == {"uq_tool_calls_agent_run_id_tool_call_id"}
    assert {
        constraint["name"]
        for constraint in inspector.get_check_constraints("agent_runs")
    } == {
        "ck_agent_runs_latency_ms_non_negative",
        "ck_agent_runs_status",
    }
    assert {
        constraint["name"]
        for constraint in inspector.get_check_constraints("tool_calls")
    } == {
        "ck_tool_calls_latency_ms_non_negative",
        "ck_tool_calls_status",
    }
    engine.dispose()


def test_downgrade_to_plan1_removes_only_agent_tables(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    config, database_url = migration_config(tmp_path, monkeypatch)
    try:
        command.upgrade(config, "head")
        command.downgrade(config, "20260712_0001")
    finally:
        get_settings.cache_clear()

    engine = create_engine(database_url)
    tables = set(inspect(engine).get_table_names())
    assert {"conversations", "messages", "llm_calls"} <= tables
    assert "agent_runs" not in tables
    assert "tool_calls" not in tables
    engine.dispose()
