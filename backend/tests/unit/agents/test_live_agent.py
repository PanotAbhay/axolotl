"""Opt-in real Interactions tool-call handshake, no sandbox or database writes."""

import pytest

from app.agents.gemini_client import GeminiClient, function_result
from app.agents.prompts import SYSTEM
from app.agents.tools import TOOL_SCHEMAS
from app.config import get_settings

pytestmark = pytest.mark.live


async def test_live_interaction_tool_roundtrip():
    if not get_settings().gemini_api_key:
        pytest.skip("GEMINI_API_KEY is not configured")
    client = GeminiClient()
    try:
        turn = await client.turn(
            "Call get_repository_overview exactly once. Do not call any other tool.",
            instruction=SYSTEM,
            tools=TOOL_SCHEMAS,
        )
        assert turn.calls and turn.calls[0].name == "get_repository_overview"
        assert len(turn.calls) == 1
        reply = await client.turn(
            [function_result(turn.calls[0], {"name": "tool-handshake", "module_count": 0})],
            instruction=SYSTEM + " Reply with a brief acknowledgement; do not call more tools.",
            tools=TOOL_SCHEMAS,
            previous_id=turn.id,
        )
        assert reply.text.strip()
        assert reply.id != turn.id
        print(f"Model {client.model}: tool call parsed and result acknowledged.")
    finally:
        await client.close()


async def test_live_structured_plan():
    """Synthetic plan input exercises the real model; no database is written."""
    from datetime import UTC, datetime

    from app.agents import propose_plan
    from app.agents.contexts import PlanContext
    from app.models.contracts import (
        GraphPayload,
        MigrationTarget,
        MigrationUnit,
        RepositoryRecord,
    )

    if not get_settings().gemini_api_key:
        pytest.skip("GEMINI_API_KEY is not configured")
    unit = MigrationUnit(
        unit_id="unit_board",
        module_ids=["module_board"],
        file_paths=["board.py"],
        depends_on_unit_ids=[],
        dependant_unit_ids=[],
    )
    ctx = PlanContext(
        repository=RepositoryRecord(
            repository_id="repo_live_plan",
            name="plan-handshake",
            snapshot_hash="sha256:synthetic-plan-input",
            origin="demo_fixture",
            executable=True,
            file_count=1,
            module_count=1,
            symbol_count=1,
            test_file_count=0,
            analysis_status="ok",
            created_at=datetime.now(UTC),
        ),
        graph=GraphPayload(
            repository_id="repo_live_plan",
            snapshot_hash="sha256:synthetic-plan-input",
            nodes=[],
            edges=[],
        ),
        units=[unit],
        target=MigrationTarget(
            target_id="modern_python3",
            label="Python 3",
            supported=True,
            description="Preserve observable behaviour",
        ),
        module_summaries={"module_board": "board.py: render_board(board)"},
    )
    plan = await propose_plan(ctx)
    assert plan.suggested_order == ["unit_board"]
    assert plan.interaction_id
    assert plan.rationale
    print("Real model returned a valid structured plan for synthetic test input.")
