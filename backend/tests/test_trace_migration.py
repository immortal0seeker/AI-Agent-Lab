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
    database_url = f"sqlite:///{tmp_path / 'trace-migration.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    config = Config()
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    return config, database_url


def test_upgrade_head_creates_trace_foundation_schema(
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

    assert {"trace_runs", "trace_steps"} <= set(inspector.get_table_names())
    assert {column["name"] for column in inspector.get_columns("trace_runs")} == {
        "id",
        "run_type",
        "conversation_id",
        "agent_run_id",
        "user_message_id",
        "title",
        "input_text",
        "output_text",
        "status",
        "provider",
        "model",
        "total_input_tokens",
        "total_output_tokens",
        "total_tokens",
        "estimated_cost",
        "latency_ms",
        "error_message",
        "metadata_json",
        "started_at",
        "ended_at",
        "created_at",
    }
    assert {column["name"] for column in inspector.get_columns("trace_steps")} == {
        "id",
        "trace_run_id",
        "step_index",
        "step_type",
        "name",
        "status",
        "input_json",
        "output_json",
        "error_message",
        "latency_ms",
        "started_at",
        "ended_at",
        "created_at",
    }

    trace_run_foreign_keys = {
        tuple(item["constrained_columns"]): item
        for item in inspector.get_foreign_keys("trace_runs")
    }
    assert trace_run_foreign_keys[("conversation_id",)]["options"]["ondelete"] == (
        "SET NULL"
    )
    assert trace_run_foreign_keys[("agent_run_id",)]["options"]["ondelete"] == (
        "SET NULL"
    )
    assert trace_run_foreign_keys[("user_message_id",)]["options"]["ondelete"] == (
        "SET NULL"
    )
    assert trace_run_foreign_keys[("agent_run_id", "conversation_id")][
        "options"
    ].get("ondelete", "NO ACTION") == "NO ACTION"
    assert trace_run_foreign_keys[("user_message_id", "conversation_id")][
        "options"
    ].get("ondelete", "NO ACTION") == "NO ACTION"

    trace_step_foreign_keys = {
        tuple(item["constrained_columns"]): item
        for item in inspector.get_foreign_keys("trace_steps")
    }
    assert trace_step_foreign_keys[("trace_run_id",)]["options"]["ondelete"] == (
        "CASCADE"
    )
    assert {item["name"] for item in inspector.get_indexes("trace_runs")} == {
        "ix_trace_runs_agent_run_id",
        "ix_trace_runs_conversation_id",
        "ix_trace_runs_user_message_id",
    }
    assert {item["name"] for item in inspector.get_indexes("trace_steps")} == {
        "ix_trace_steps_trace_run_id",
    }
    assert {
        item["name"]
        for item in inspector.get_unique_constraints("trace_steps")
    } == {"uq_trace_steps_trace_run_id_step_index"}
    assert {
        item["name"] for item in inspector.get_check_constraints("trace_runs")
    } == {
        "ck_trace_runs_estimated_cost_non_negative",
        "ck_trace_runs_input_text_not_blank",
        "ck_trace_runs_latency_ms_non_negative",
        "ck_trace_runs_run_type",
        "ck_trace_runs_status",
        "ck_trace_runs_total_input_tokens_non_negative",
        "ck_trace_runs_total_output_tokens_non_negative",
        "ck_trace_runs_total_tokens_non_negative",
    }
    assert {
        item["name"] for item in inspector.get_check_constraints("trace_steps")
    } == {
        "ck_trace_steps_latency_ms_non_negative",
        "ck_trace_steps_name_not_blank",
        "ck_trace_steps_status",
        "ck_trace_steps_step_index_positive",
        "ck_trace_steps_step_type",
    }
    engine.dispose()


def test_trace_migration_downgrade_and_reupgrade_lifecycle(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    config, database_url = migration_config(tmp_path, monkeypatch)
    try:
        command.upgrade(config, "head")
        command.downgrade(config, "20260801_0007")

        engine = create_engine(database_url)
        downgraded_tables = set(inspect(engine).get_table_names())
        engine.dispose()
        assert "trace_runs" not in downgraded_tables
        assert "trace_steps" not in downgraded_tables
        assert {"knowledge_bases", "documents", "rag_queries"} <= downgraded_tables

        command.upgrade(config, "head")
        command.check(config)
    finally:
        get_settings.cache_clear()

    engine = create_engine(database_url)
    upgraded_tables = set(inspect(engine).get_table_names())
    engine.dispose()
    assert {"trace_runs", "trace_steps"} <= upgraded_tables
