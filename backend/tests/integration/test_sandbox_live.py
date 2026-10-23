"""The sandbox, for real - owner: Dev 4.

These run the **actual container** under the **actual security profile** against the
**actual fixture**. No mocks. They skip themselves when Docker or the runner image
is absent:

    docker build -t axolotl-runner:latest runner/
    uv run pytest -m docker -q

This is the payoff test for the whole project. It proves, through production code,
that a plausible-looking modernisation which keeps every visible test green is still
caught by the held-out differential. If this passes, the core claim is real.
"""

import asyncio
from pathlib import Path

import pytest

from app.sandbox import runner, workspaces
from app.verification import comparison

pytestmark = pytest.mark.docker

FIXTURE = Path(__file__).resolve().parents[3] / "demo" / "legacy_orders"
HELD_OUT = Path(__file__).resolve().parents[3] / "demo" / "challenge_cases" / "held_out.json"
VISIBLE = FIXTURE / "tests" / "cases.json"


def runner_ready() -> bool:
    try:
        return bool(asyncio.run(runner.runner_status())["available"])
    except Exception:  # noqa: BLE001
        return False


pytestmark = [
    pytest.mark.docker,
    pytest.mark.skipif(
        not FIXTURE.is_dir(), reason="demo fixture not present"
    ),
    pytest.mark.skipif(
        not runner_ready(),
        reason="sandbox runner unavailable; build it with "
               "`docker build -t axolotl-runner:latest runner/`",
    ),
]


@pytest.fixture
def candidate(monkeypatch, tmp_path):
    """A writable copy of the fixture, as the orchestrator would make."""
    monkeypatch.setattr(workspaces, "workspace_root", lambda: tmp_path)

    import app.ingestion as ingestion_module

    monkeypatch.setattr(ingestion_module, "snapshot_path", lambda repo_id: FIXTURE)
    return tmp_path


def bankers_rounding(source: str) -> str:
    """A plausible 'modernisation': use Python's native banker's rounding."""
    return source.replace("ROUND_HALF_UP", "ROUND_HALF_EVEN")


# --------------------------------------------------------------------------
# the profile actually holds
# --------------------------------------------------------------------------

async def test_the_container_has_no_network():
    result = await runner._run_in_container(
        mounts=[runner.Mount(FIXTURE, "/code")],
        command=["python", "-c",
                 "import socket;socket.create_connection(('1.1.1.1',53),timeout=3)"],
    )
    assert result.exit_code != 0, "the sandbox reached the network"


async def test_the_code_mount_is_read_only():
    result = await runner._run_in_container(
        mounts=[runner.Mount(FIXTURE, "/code")],
        command=["python", "-c", "open('/code/pwned.py','w').write('x')"],
    )
    assert result.exit_code != 0, "/code was writable"
    assert not (FIXTURE / "pwned.py").exists()


async def test_tmp_is_writable_so_gates_can_work():
    result = await runner._run_in_container(
        mounts=[runner.Mount(FIXTURE, "/code")],
        command=["python", "-c", "open('/tmp/ok','w').write('x');print('wrote')"],
    )
    assert result.exit_code == 0
    assert "wrote" in result.stdout


# --------------------------------------------------------------------------
# the gates
# --------------------------------------------------------------------------

async def test_the_compile_gate_passes_the_baseline():
    assert (await runner.run_compileall(FIXTURE)).exit_code == 0


async def test_the_compile_gate_fails_a_broken_tree(candidate, tmp_path):
    from app.models.contracts import FilePatch, PatchProposal

    ws = await workspaces.create_workspace("run_c", "repo_c")
    broken = (FIXTURE / "pricing.py").read_text(encoding="utf-8") + "\ndef oops(:\n    pass\n"
    # apply_patch would refuse this, so write it directly: the point is that the
    # compile gate is a real check and not a rubber stamp.
    (Path(ws.root) / "pricing.py").write_text(broken, encoding="utf-8")
    del FilePatch, PatchProposal

    assert (await runner.run_compileall(Path(ws.root))).exit_code != 0


async def test_the_existing_tests_gate_passes_the_baseline():
    result = await runner.run_pytest(FIXTURE)
    assert result.exit_code == 0, result.log_excerpt
    assert "12 passed" in result.stdout


# --------------------------------------------------------------------------
# the claim this project rests on
# --------------------------------------------------------------------------

async def test_the_fixtures_own_tests_pass_on_the_wrong_patch(candidate):
    """The gap that justifies the whole product.

    A patch that changes real behaviour sails through the visible test suite. If
    this ever starts failing, the demo's premise is gone and the held-out suite is
    no longer earning its keep.
    """
    ws = await workspaces.create_workspace("run_g", "repo_g")
    pricing = Path(ws.root) / "pricing.py"
    pricing.write_text(bankers_rounding(pricing.read_text(encoding="utf-8")),
                       encoding="utf-8")

    result = await runner.run_pytest(Path(ws.root))

    assert result.exit_code == 0, (
        "the visible tests now catch the rounding change; the held-out suite is no "
        "longer demonstrating anything the visible one does not"
    )


async def test_the_held_out_differential_catches_what_the_tests_miss(candidate):
    """End to end, through production code: baseline vs a banker's-rounding patch.

    Two real container runs and the real §5 comparison. This is the £0.01 moment.
    """
    # 1. the oracle, from the immutable baseline
    baseline_raw, baseline_result = await runner.run_behaviour_cases(FIXTURE, HELD_OUT)
    assert baseline_result.policy_clean
    baseline = {
        o["case_id"]: comparison.outcome_from_harness(o, o["case_id"])
        for o in baseline_raw if o.get("case_id")
    }
    assert len(baseline) == 10, f"expected 10 held-out cases, got {len(baseline)}"

    # 2. a plausible modernisation
    ws = await workspaces.create_workspace("run_d", "repo_d")
    pricing = Path(ws.root) / "pricing.py"
    pricing.write_text(bankers_rounding(pricing.read_text(encoding="utf-8")),
                       encoding="utf-8")

    # 3. the same cases against the candidate
    candidate_raw, _ = await runner.run_behaviour_cases(Path(ws.root), HELD_OUT)
    new = {
        o["case_id"]: comparison.outcome_from_harness(o, o["case_id"])
        for o in candidate_raw if o.get("case_id")
    }

    # 4. the real comparison
    comparisons = [
        comparison.compare(case_id, "held_out", baseline[case_id], new[case_id])
        for case_id in sorted(baseline)
        if case_id in new
    ]
    counts = comparison.summarise(comparisons)

    assert counts["mismatch"] >= 5, (
        f"the differential should catch this patch; got {counts}"
    )
    assert counts["match"] >= 1, (
        "every case mismatching would suggest the harness broke rather than the "
        "rounding changing"
    )

    # The penny, specifically.
    differences = [
        comparison.describe_difference(c)
        for c in comparisons if c.verdict == "mismatch"
    ]
    assert any("2.65" in d and "2.64" in d for d in differences), (
        f"expected the 2.65 -> 2.64 counterexample; saw {differences}"
    )


async def test_the_visible_cases_still_agree_on_the_baseline():
    """A sanity floor: the baseline must agree with itself, or everything above is
    measuring noise."""
    first_raw, _ = await runner.run_behaviour_cases(FIXTURE, VISIBLE)
    second_raw, _ = await runner.run_behaviour_cases(FIXTURE, VISIBLE)

    first = {o["case_id"]: comparison.outcome_from_harness(o, o["case_id"])
             for o in first_raw if o.get("case_id")}
    second = {o["case_id"]: comparison.outcome_from_harness(o, o["case_id"])
              for o in second_raw if o.get("case_id")}

    comparisons = [
        comparison.compare(c, "visible", first[c], second[c]) for c in sorted(first)
    ]
    counts = comparison.summarise(comparisons)
    assert counts["mismatch"] == 0, "the fixture is not deterministic"
    assert counts["match"] == 16
