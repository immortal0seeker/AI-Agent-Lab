import importlib
import json

import pytest


def load_trace_types():
    try:
        return importlib.import_module("app.observability.trace_types")
    except ModuleNotFoundError:
        pytest.fail("Trace type contracts are not implemented", pytrace=False)


def test_trace_enum_values_are_stable_strings() -> None:
    trace_types = load_trace_types()

    assert [item.value for item in trace_types.TraceRunType] == [
        "chat",
        "agent",
        "rag_query",
        "rag_chat",
        "evaluation",
        "tool",
    ]
    assert [item.value for item in trace_types.TraceStatus] == [
        "pending",
        "running",
        "completed",
        "failed",
        "cancelled",
    ]
    assert [item.value for item in trace_types.TraceStepType] == [
        "build_context",
        "llm_call",
        "tool_call",
        "rag_retrieve",
        "query_rewrite",
        "bm25_search",
        "vector_search",
        "hybrid_fusion",
        "parent_child_expand",
        "rerank",
        "build_prompt",
        "final_answer",
        "eval_metric",
    ]


def test_trace_enums_serialize_as_json_strings() -> None:
    trace_types = load_trace_types()
    payload = {
        "run_type": trace_types.TraceRunType.RAG_QUERY,
        "status": trace_types.TraceStatus.RUNNING,
        "step_type": trace_types.TraceStepType.RAG_RETRIEVE,
    }

    assert json.loads(json.dumps(payload)) == {
        "run_type": "rag_query",
        "status": "running",
        "step_type": "rag_retrieve",
    }
