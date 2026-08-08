from pathlib import Path

from alembic import command
from alembic.config import Config
from pytest import MonkeyPatch
from sqlalchemy import create_engine, inspect

from app.core.config import get_settings


BACKEND_ROOT = Path(__file__).parents[1]
PREVIOUS_REVISION = "20260802_0008"


def migration_config(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> tuple[Config, str]:
    database_url = f"sqlite:///{tmp_path / 'retrieval-migration.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    config = Config()
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    return config, database_url


def test_upgrade_head_creates_retrieval_audit_schema(
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

    assert {"rag_retrieval_runs", "rag_retrieval_candidates"} <= set(
        inspector.get_table_names()
    )
    assert {
        column["name"]
        for column in inspector.get_columns("rag_retrieval_runs")
    } == {
        "id",
        "trace_run_id",
        "knowledge_base_id",
        "strategy_name",
        "original_query",
        "rewritten_query",
        "top_k",
        "candidate_count",
        "selected_count",
        "score_threshold",
        "latency_ms",
        "metadata_filter_json",
        "strategy_config_json",
        "created_at",
    }
    assert {
        column["name"]
        for column in inspector.get_columns("rag_retrieval_candidates")
    } == {
        "id",
        "retrieval_run_id",
        "chunk_id",
        "document_id",
        "rank",
        "final_rank",
        "source",
        "dense_score",
        "sparse_score",
        "fused_score",
        "rerank_score",
        "selected",
        "content_preview",
        "metadata_json",
        "created_at",
    }

    run_foreign_keys = inspector.get_foreign_keys("rag_retrieval_runs")
    assert len(run_foreign_keys) == 1
    assert run_foreign_keys[0]["constrained_columns"] == ["trace_run_id"]
    assert run_foreign_keys[0]["referred_table"] == "trace_runs"
    assert run_foreign_keys[0]["options"]["ondelete"] == "CASCADE"

    candidate_foreign_keys = inspector.get_foreign_keys(
        "rag_retrieval_candidates"
    )
    assert len(candidate_foreign_keys) == 1
    assert candidate_foreign_keys[0]["constrained_columns"] == [
        "retrieval_run_id"
    ]
    assert candidate_foreign_keys[0]["referred_table"] == "rag_retrieval_runs"
    assert candidate_foreign_keys[0]["options"]["ondelete"] == "CASCADE"

    assert {
        item["name"] for item in inspector.get_indexes("rag_retrieval_runs")
    } == {
        "ix_rag_retrieval_runs_knowledge_base_id",
        "ix_rag_retrieval_runs_trace_run_id",
    }
    assert {
        item["name"]
        for item in inspector.get_indexes("rag_retrieval_candidates")
    } == {
        "ix_rag_retrieval_candidates_chunk_id",
        "ix_rag_retrieval_candidates_document_id",
        "ix_rag_retrieval_candidates_retrieval_run_id",
    }
    assert {
        item["name"]
        for item in inspector.get_unique_constraints(
            "rag_retrieval_candidates"
        )
    } == {
        "uq_rag_retrieval_candidates_retrieval_run_id_final_rank",
        "uq_rag_retrieval_candidates_retrieval_run_id_rank",
    }
    assert {
        item["name"]
        for item in inspector.get_check_constraints("rag_retrieval_runs")
    } == {
        "ck_rag_retrieval_runs_candidate_count_range",
        "ck_rag_retrieval_runs_latency_ms_non_negative",
        "ck_rag_retrieval_runs_original_query_not_blank",
        "ck_rag_retrieval_runs_selected_count_not_above_candidate_count",
        "ck_rag_retrieval_runs_selected_count_range",
        "ck_rag_retrieval_runs_strategy_name_not_blank",
        "ck_rag_retrieval_runs_top_k_range",
    }
    assert {
        item["name"]
        for item in inspector.get_check_constraints(
            "rag_retrieval_candidates"
        )
    } == {
        "ck_rag_retrieval_candidates_content_preview_max_length",
        "ck_rag_retrieval_candidates_content_preview_not_blank",
        "ck_rag_retrieval_candidates_final_rank_positive",
        "ck_rag_retrieval_candidates_rank_positive",
        "ck_rag_retrieval_candidates_source",
    }
    engine.dispose()


def test_retrieval_migration_downgrade_and_reupgrade_lifecycle(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    config, database_url = migration_config(tmp_path, monkeypatch)
    try:
        command.upgrade(config, "head")
        command.downgrade(config, PREVIOUS_REVISION)

        engine = create_engine(database_url)
        downgraded_tables = set(inspect(engine).get_table_names())
        engine.dispose()
        assert "rag_retrieval_runs" not in downgraded_tables
        assert "rag_retrieval_candidates" not in downgraded_tables
        assert {"trace_runs", "trace_steps"} <= downgraded_tables

        command.upgrade(config, "head")
        command.check(config)
    finally:
        get_settings.cache_clear()

    engine = create_engine(database_url)
    upgraded_tables = set(inspect(engine).get_table_names())
    engine.dispose()
    assert {"rag_retrieval_runs", "rag_retrieval_candidates"} <= (
        upgraded_tables
    )
