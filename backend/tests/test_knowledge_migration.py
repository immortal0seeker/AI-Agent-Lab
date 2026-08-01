from pathlib import Path

from alembic import command
from alembic.config import Config
import pytest
from pytest import MonkeyPatch
from sqlalchemy import create_engine, inspect, text

from app.core.config import get_settings


BACKEND_ROOT = Path(__file__).parents[1]
PLAN3_TABLES = {
    "knowledge_bases",
    "documents",
    "document_chunks",
    "rag_queries",
}


def migration_config(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> tuple[Config, str]:
    database_url = f"sqlite:///{tmp_path / 'knowledge-migration.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    config = Config()
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    return config, database_url


def test_upgrade_head_creates_plan3_knowledge_schema(
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

    assert PLAN3_TABLES <= set(inspector.get_table_names())
    assert {
        column["name"]
        for column in inspector.get_columns("knowledge_bases")
    } == {
        "id",
        "name",
        "description",
        "embedding_provider",
        "embedding_model",
        "vector_store",
        "vector_collection_name",
        "created_at",
        "updated_at",
    }
    assert {
        column["name"] for column in inspector.get_columns("documents")
    } == {
        "id",
        "knowledge_base_id",
        "filename",
        "original_filename",
        "file_type",
        "file_path",
        "file_size",
        "file_hash",
        "parse_status",
        "chunk_status",
        "embedding_status",
        "error_message",
        "metadata_json",
        "created_at",
        "updated_at",
    }
    assert {
        column["name"] for column in inspector.get_columns("document_chunks")
    } == {
        "id",
        "document_id",
        "knowledge_base_id",
        "chunk_index",
        "content",
        "token_count",
        "char_count",
        "heading",
        "page_number",
        "metadata_json",
        "vector_id",
        "created_at",
    }
    assert {
        column["name"] for column in inspector.get_columns("rag_queries")
    } == {
        "id",
        "conversation_id",
        "knowledge_base_id",
        "query",
        "retrieved_chunks_json",
        "answer_message_id",
        "latency_ms",
        "created_at",
    }

    assert {
        constraint["name"]
        for constraint in inspector.get_check_constraints("knowledge_bases")
    } == {"ck_knowledge_bases_name_not_blank"}
    assert {
        constraint["name"]
        for constraint in inspector.get_check_constraints("documents")
    } == {
        "ck_documents_chunk_status",
        "ck_documents_embedding_status",
        "ck_documents_file_hash_length",
        "ck_documents_file_size_non_negative",
        "ck_documents_file_type",
        "ck_documents_parse_status",
    }
    assert {
        constraint["name"]
        for constraint in inspector.get_check_constraints("document_chunks")
    } == {
        "ck_document_chunks_char_count_non_negative",
        "ck_document_chunks_chunk_index_non_negative",
        "ck_document_chunks_page_number_positive",
        "ck_document_chunks_token_count_non_negative",
    }
    assert {
        constraint["name"]
        for constraint in inspector.get_check_constraints("rag_queries")
    } == {
        "ck_rag_queries_answer_requires_conversation",
        "ck_rag_queries_latency_ms_non_negative",
    }

    assert {
        constraint["name"]
        for constraint in inspector.get_unique_constraints("documents")
    } == {
        "uq_documents_id_knowledge_base_id",
        "uq_documents_knowledge_base_id_file_hash",
    }
    assert {
        constraint["name"]
        for constraint in inspector.get_unique_constraints("document_chunks")
    } == {"uq_document_chunks_document_id_chunk_index"}

    assert {index["name"] for index in inspector.get_indexes("documents")} == {
        "ix_documents_knowledge_base_id",
    }
    assert {
        index["name"] for index in inspector.get_indexes("document_chunks")
    } == {
        "ix_document_chunks_document_id",
        "ix_document_chunks_knowledge_base_id",
    }
    assert {
        index["name"] for index in inspector.get_indexes("rag_queries")
    } == {
        "ix_rag_queries_answer_message_id",
        "ix_rag_queries_conversation_id",
        "ix_rag_queries_knowledge_base_id",
    }

    document_foreign_key = inspector.get_foreign_keys("documents")[0]
    assert document_foreign_key["referred_table"] == "knowledge_bases"
    assert document_foreign_key["options"]["ondelete"] == "RESTRICT"

    chunk_foreign_key = inspector.get_foreign_keys("document_chunks")[0]
    assert chunk_foreign_key["constrained_columns"] == [
        "document_id",
        "knowledge_base_id",
    ]
    assert chunk_foreign_key["referred_columns"] == [
        "id",
        "knowledge_base_id",
    ]
    assert chunk_foreign_key["options"]["ondelete"] == "CASCADE"

    rag_foreign_keys = {
        tuple(foreign_key["constrained_columns"]): foreign_key
        for foreign_key in inspector.get_foreign_keys("rag_queries")
    }
    assert rag_foreign_keys[("conversation_id",)]["referred_table"] == (
        "conversations"
    )
    assert (
        rag_foreign_keys[("conversation_id",)]["options"]["ondelete"]
        == "CASCADE"
    )
    assert rag_foreign_keys[("knowledge_base_id",)]["referred_table"] == (
        "knowledge_bases"
    )
    assert (
        rag_foreign_keys[("knowledge_base_id",)]["options"]["ondelete"]
        == "CASCADE"
    )
    answer_foreign_key = rag_foreign_keys[
        ("answer_message_id", "conversation_id")
    ]
    assert answer_foreign_key["referred_table"] == "messages"
    assert answer_foreign_key["referred_columns"] == [
        "id",
        "conversation_id",
    ]
    assert answer_foreign_key["options"].get(
        "ondelete",
        "NO ACTION",
    ) == "NO ACTION"
    assert rag_foreign_keys[("answer_message_id",)]["referred_table"] == (
        "messages"
    )
    assert rag_foreign_keys[("answer_message_id",)]["options"][
        "ondelete"
    ] == "SET NULL"

    engine.dispose()


def test_hash_uniqueness_migration_fails_closed_on_duplicate_groups(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    config, database_url = migration_config(tmp_path, monkeypatch)
    command.upgrade(config, "20260726_0005")
    engine = create_engine(database_url)
    knowledge_base_id = "11111111111141118111111111111111"
    duplicate_hash = "d" * 64
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO knowledge_bases "
                "(id, name, vector_store, created_at, updated_at) "
                "VALUES (:id, :name, :vector_store, :created_at, :updated_at)"
            ),
            {
                "id": knowledge_base_id,
                "name": "Duplicate migration KB",
                "vector_store": "qdrant",
                "created_at": "2026-08-01 00:00:00",
                "updated_at": "2026-08-01 00:00:00",
            },
        )
        for index in (1, 2):
            connection.execute(
                text(
                    "INSERT INTO documents "
                    "(id, knowledge_base_id, filename, original_filename, "
                    "file_type, file_path, file_size, file_hash, parse_status, "
                    "chunk_status, embedding_status, metadata_json, created_at, "
                    "updated_at) VALUES "
                    "(:id, :knowledge_base_id, :filename, :original_filename, "
                    ":file_type, :file_path, :file_size, :file_hash, "
                    ":parse_status, :chunk_status, :embedding_status, "
                    ":metadata_json, :created_at, :updated_at)"
                ),
                {
                    "id": f"{index}" * 32,
                    "knowledge_base_id": knowledge_base_id,
                    "filename": f"private-{index}.txt",
                    "original_filename": f"private-{index}.txt",
                    "file_type": "txt",
                    "file_path": f"private/path/{index}.txt",
                    "file_size": 1,
                    "file_hash": duplicate_hash,
                    "parse_status": "uploaded",
                    "chunk_status": "pending",
                    "embedding_status": "pending",
                    "metadata_json": "{}",
                    "created_at": "2026-08-01 00:00:00",
                    "updated_at": "2026-08-01 00:00:00",
                },
            )

    try:
        with pytest.raises(RuntimeError) as caught:
            command.upgrade(config, "head")
    finally:
        get_settings.cache_clear()
        engine.dispose()

    assert str(caught.value) == (
        "Plan 3 document hash uniqueness migration found "
        "1 duplicate group(s); review them manually."
    )
    assert "private" not in str(caught.value)
    assert duplicate_hash not in str(caught.value)


def test_downgrade_to_plan2_removes_only_plan3_tables(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    config, database_url = migration_config(tmp_path, monkeypatch)
    try:
        command.upgrade(config, "head")
        command.downgrade(config, "20260720_0004")
    finally:
        get_settings.cache_clear()

    engine = create_engine(database_url)
    tables = set(inspect(engine).get_table_names())

    assert PLAN3_TABLES.isdisjoint(tables)
    assert {
        "conversations",
        "messages",
        "llm_calls",
        "agent_runs",
        "tool_calls",
    } <= tables

    engine.dispose()
