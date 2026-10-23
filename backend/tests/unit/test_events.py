"""Event journal unit tests - owner: Dev 2. SHARED_CONTRACTS §7.

Only the pure helpers are covered here. `append_event` and `list_events` need a real
Atlas connection and belong in tests/integration once MONGODB_URI is configured.
"""

from app.orchestration.events import (
    EXCERPT_LIMIT_BYTES,
    REDACTED,
    redact,
    sanitise,
    truncate,
)

# Deliberately NOT shaped like real credentials: these are only ever compared as
# opaque strings, and a realistic-looking key here would trip secret scanners and
# teach people that committing key-shaped text is fine.
SECRET_URI = "mongodb+srv://EXAMPLE-NOT-A-REAL-CONNECTION-STRING/axolotl"
SECRET_KEY = "EXAMPLE-NOT-A-REAL-GEMINI-KEY-0000000000"


def test_a_secret_in_a_string_is_replaced():
    payload = redact(f"connecting to {SECRET_URI} now", [SECRET_URI])
    assert SECRET_URI not in payload
    assert REDACTED in payload


def test_secrets_are_stripped_from_nested_payloads():
    payload = {
        "message": f"failed against {SECRET_URI}",
        "nested": {"key": SECRET_KEY},
        "items": [{"uri": SECRET_URI}, "harmless"],
    }
    cleaned = redact(payload, [SECRET_URI, SECRET_KEY])
    rendered = repr(cleaned)
    assert SECRET_URI not in rendered
    assert SECRET_KEY not in rendered
    assert "harmless" in rendered


def test_secrets_are_stripped_from_dict_keys_too():
    cleaned = redact({SECRET_KEY: "value"}, [SECRET_KEY])
    assert SECRET_KEY not in repr(cleaned)


def test_short_strings_are_never_treated_as_secrets():
    """A 3-character 'secret' would mangle ordinary prose."""
    assert redact("the cat sat on the mat", ["cat"]) == "the cat sat on the mat"


def test_redaction_leaves_innocent_payloads_alone():
    payload = {"unit_id": "unit_pricing", "attempt": 2, "ok": True, "ratio": 0.5}
    assert redact(payload, [SECRET_URI]) == payload


def test_non_string_values_survive_redaction():
    payload = {"count": 3, "flag": False, "nothing": None, "items": [1, 2, 3]}
    assert redact(payload, [SECRET_URI]) == payload


def test_long_excerpts_are_capped_and_marked():
    long_text = "x" * (EXCERPT_LIMIT_BYTES * 2)
    capped = truncate(long_text)
    assert len(capped.encode("utf-8")) <= EXCERPT_LIMIT_BYTES + len("... [truncated]")
    assert capped.endswith("... [truncated]")


def test_short_excerpts_are_untouched():
    assert truncate("a short log line") == "a short log line"


def test_truncation_does_not_split_a_multibyte_character():
    text = "é" * EXCERPT_LIMIT_BYTES  # 2 bytes each
    capped = truncate(text)
    assert isinstance(capped, str)
    assert "�" not in capped


def test_truncation_reaches_into_nested_payloads():
    payload = {"log": "y" * (EXCERPT_LIMIT_BYTES * 2), "items": ["z" * 5000]}
    capped = truncate(payload)
    assert capped["log"].endswith("... [truncated]")
    assert capped["items"][0].endswith("... [truncated]")


def test_sanitise_redacts_and_truncates_together():
    payload = {"log": SECRET_URI + "a" * (EXCERPT_LIMIT_BYTES * 2)}
    cleaned = sanitise(payload, [SECRET_URI])
    assert SECRET_URI not in cleaned["log"]
    assert cleaned["log"].endswith("... [truncated]")


def test_a_secret_past_the_truncation_point_is_still_removed():
    """Redaction must run before truncation, or half a secret survives."""
    payload = {"log": "a" * (EXCERPT_LIMIT_BYTES - 10) + SECRET_URI}
    cleaned = sanitise(payload, [SECRET_URI])
    assert SECRET_URI not in cleaned["log"]
    assert "mongodb+srv://EXAMPLE" not in cleaned["log"]


def test_sanitise_handles_a_missing_payload():
    assert sanitise(None) == {}


def test_sanitise_without_configured_secrets_still_truncates():
    """With an empty .env there is nothing to redact, but caps still apply."""
    cleaned = sanitise({"log": "a" * (EXCERPT_LIMIT_BYTES * 2)})
    assert cleaned["log"].endswith("... [truncated]")


def test_bytes_cannot_smuggle_a_secret_past_redaction():
    """Bytes bypass both the string branch and truncate(), so a secret inside one
    would be stored verbatim."""
    payload = {"blob": SECRET_URI.encode("utf-8")}
    cleaned = sanitise(payload, [SECRET_URI])
    assert SECRET_URI not in str(cleaned)
    assert "bytes omitted" in cleaned["blob"]


def test_bytes_nested_in_a_list_are_handled_too():
    cleaned = sanitise({"items": [b"abc", "fine"]}, [SECRET_URI])
    assert "bytes omitted" in str(cleaned["items"][0])
    assert cleaned["items"][1] == "fine"


async def test_list_all_events_pages_past_the_thousand_event_ceiling(monkeypatch):
    """The report picks the LAST snapshot_accepted. Read through a 1000-event
    ceiling, a long run would publish an intermediate revision as the verified one.
    """
    from datetime import UTC, datetime

    from app.models.contracts import RunEvent
    from app.orchestration import events as events_module

    total = 2500

    async def fake_list_events(run_id, after_sequence=0, limit=200):
        page = []
        seq = after_sequence + 1
        while seq <= total and len(page) < limit:
            page.append(RunEvent(
                run_id=run_id, sequence=seq, timestamp=datetime.now(UTC),
                event_type="snapshot_accepted" if seq == total else "agent_turn",
                payload={"revision": f"rev_{seq}"},
            ))
            seq += 1
        return page

    monkeypatch.setattr(events_module, "list_events", fake_list_events)

    everything = await events_module.list_all_events("run_long")

    assert len(everything) == total
    assert everything[-1].sequence == total
    accepted = [e for e in everything if e.event_type == "snapshot_accepted"]
    assert accepted[-1].payload["revision"] == f"rev_{total}"


async def test_list_all_events_handles_an_empty_journal(monkeypatch):
    from app.orchestration import events as events_module

    async def empty(run_id, after_sequence=0, limit=200):
        return []

    monkeypatch.setattr(events_module, "list_events", empty)
    assert await events_module.list_all_events("run_x") == []
