"""Tests for skills runtime injection and platform routes."""

from __future__ import annotations

from pathlib import Path

from engine.config import get_pipeline_stages_config
from engine.graph.hitl_evidence import build_hitl_payload
from engine.graph.node import NodeSpec, SharedMemory
from engine.skills.context import set_skill_filter
from engine.skills.discovery import build_skills_prompt_section, discover_skills


def test_default_pipeline_stages_when_unconfigured(monkeypatch, tmp_path):
    monkeypatch.setattr("engine.config.ENGINE_CONFIG_FILE", tmp_path / "missing.json")
    stages = get_pipeline_stages_config()
    types = [s["type"] for s in stages]
    assert "input_validation" in types
    assert "rate_limit" in types


def test_discover_example_skills():
    engine_root = Path(__file__).resolve().parents[2]
    skills = discover_skills(engine_root)
    names = {s.name for s in skills}
    assert "agreement-review" in names
    assert "supervisor-delegation" in names


def test_build_skills_prompt_section_includes_names():
    engine_root = Path(__file__).resolve().parents[2]
    section = build_skills_prompt_section(engine_root)
    assert "agreement-review" in section
    assert "load_skill" in section


def test_skill_filter_limits_prompt():
    engine_root = Path(__file__).resolve().parents[2]
    set_skill_filter(["supervisor-delegation"])
    section = build_skills_prompt_section(engine_root)
    assert "supervisor-delegation" in section
    assert "agreement-review" not in section
    set_skill_filter(None)


def test_hitl_evidence_payload():
    memory = SharedMemory()
    memory.write("contract_text", "Sample agreement body")
    spec = NodeSpec(
        id="human_review",
        name="Human Review",
        description="Review step",
        node_type="event_loop",
        input_keys=["contract_text"],
        output_keys=["extracted_terms"],
    )
    memory.write("extracted_terms", '{"party":"Acme"}')
    evidence, audit = build_hitl_payload(
        node_id="human_review",
        node_spec=spec,
        memory=memory,
        prompt="Approve extraction?",
    )
    assert len(evidence) == 2
    assert audit["evidence_count"] == 2


def test_google_calendar_provider_authorize_url():
    from engine.credentials.oauth2.google_calendar_provider import GoogleCalendarOAuth2Provider

    provider = GoogleCalendarOAuth2Provider(client_id="id", client_secret="secret")
    url = provider.get_authorization_url(state="abc", redirect_uri="http://localhost/cb")
    assert "accounts.google.com" in url
    assert "calendar" in url
