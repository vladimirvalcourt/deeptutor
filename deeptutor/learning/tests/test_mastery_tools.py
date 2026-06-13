"""Tests for the Mastery Path tools — the seam between the chat-loop tutor and
the engine. They drive the full loop the tutor uses: build a path, read the
gate, pose + grade questions, assess qualitative objectives, with the active
path id injected server-side (never by the model)."""

from __future__ import annotations

import json

import pytest

from deeptutor.learning.storage import LearningStore
from deeptutor.tools.mastery_tool import (
    MasteryAssessTool,
    MasteryBuildTool,
    MasteryGradeTool,
    MasteryQuizTool,
    MasteryStatusTool,
)


@pytest.fixture
def path_id(tmp_path, monkeypatch):
    """Point the LearningStore at a temp workspace and yield a stable path id."""
    monkeypatch.setattr(LearningStore, "__init__", _store_init_factory(tmp_path))
    return "test_path"


def _store_init_factory(root):
    def _init(self, root_arg=None):  # mirrors LearningStore.__init__ signature
        from pathlib import Path

        self._root = Path(root) / "learning"
        self._root.mkdir(parents=True, exist_ok=True)

    return _init


async def _build_basic(path_id):
    build = MasteryBuildTool()
    return await build.execute(
        _mastery_path_id=path_id,
        mode="replace",
        modules=[
            {
                "name": "Module 1",
                "knowledge_points": [
                    {"name": "Truth tables", "type": "memory"},
                    {"name": "Why XOR matters", "type": "concept"},
                ],
            }
        ],
    )


# ── build ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_build_creates_path(path_id):
    result = await _build_basic(path_id)
    assert result.success
    payload = json.loads(result.content)
    assert payload["knowledge_points_added"] == 2
    assert payload["map"]["counts"]["total"] == 2


@pytest.mark.asyncio
async def test_build_rejects_empty_modules(path_id):
    result = await MasteryBuildTool().execute(_mastery_path_id=path_id, modules=[])
    assert result.success is False


@pytest.mark.asyncio
async def test_build_append_keeps_existing(path_id):
    await _build_basic(path_id)
    result = await MasteryBuildTool().execute(
        _mastery_path_id=path_id,
        mode="append",
        modules=[{"name": "Module 2", "knowledge_points": [{"name": "Adders", "type": "procedure"}]}],
    )
    payload = json.loads(result.content)
    assert payload["map"]["counts"]["total"] == 3  # 2 existing + 1 appended


@pytest.mark.asyncio
async def test_build_unknown_type_defaults_to_concept(path_id):
    result = await MasteryBuildTool().execute(
        _mastery_path_id=path_id,
        modules=[{"name": "M", "knowledge_points": [{"name": "Thing", "type": "nonsense"}]}],
    )
    kp = json.loads(result.content)["map"]["modules"][0]["knowledge_points"][0]
    assert kp["type"] == "concept"


# ── status ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_status_empty_path_asks_for_build(path_id):
    payload = json.loads((await MasteryStatusTool().execute(_mastery_path_id=path_id)).content)
    assert payload["status"] == "empty"


@pytest.mark.asyncio
async def test_status_points_at_first_objective(path_id):
    await _build_basic(path_id)
    payload = json.loads((await MasteryStatusTool().execute(_mastery_path_id=path_id)).content)
    assert payload["status"] == "active"
    assert payload["next"]["action"] == "probe"
    assert payload["next"]["knowledge_point_type"] == "memory"


@pytest.mark.asyncio
async def test_no_path_id_fails_closed():
    result = await MasteryStatusTool().execute(_mastery_path_id="")
    assert result.success is False


# ── quiz + grade: the deterministic objective gate ───────────────────────────


@pytest.mark.asyncio
async def test_quiz_then_grade_drives_memory_gate(path_id):
    await _build_basic(path_id)
    status = json.loads((await MasteryStatusTool().execute(_mastery_path_id=path_id)).content)
    kp_id = status["next"]["knowledge_point_id"]

    quiz, grade = MasteryQuizTool(), MasteryGradeTool()
    mastered = False
    for _ in range(3):
        await quiz.execute(
            _mastery_path_id=path_id,
            knowledge_point_id=kp_id,
            question="2+2?",
            expected_answer="4",
            question_type="short",
        )
        result = json.loads((await grade.execute(_mastery_path_id=path_id, answer="4")).content)
        assert result["is_correct"] is True
        mastered = result["mastered"]
    # 0.5 -> 0.8 -> 1.0 ≥ 0.9: mastered only after the third correct answer.
    assert mastered is True


@pytest.mark.asyncio
async def test_grade_without_pending_fails(path_id):
    await _build_basic(path_id)
    result = await MasteryGradeTool().execute(_mastery_path_id=path_id, answer="x")
    assert result.success is False


@pytest.mark.asyncio
async def test_quiz_unknown_kp_fails(path_id):
    await _build_basic(path_id)
    result = await MasteryQuizTool().execute(
        _mastery_path_id=path_id,
        knowledge_point_id="nope",
        question="?",
        expected_answer="x",
    )
    assert result.success is False


@pytest.mark.asyncio
async def test_wrong_answer_does_not_master(path_id):
    await _build_basic(path_id)
    status = json.loads((await MasteryStatusTool().execute(_mastery_path_id=path_id)).content)
    kp_id = status["next"]["knowledge_point_id"]
    await MasteryQuizTool().execute(
        _mastery_path_id=path_id, knowledge_point_id=kp_id, question="2+2?", expected_answer="4"
    )
    result = json.loads(
        (await MasteryGradeTool().execute(_mastery_path_id=path_id, answer="5")).content
    )
    assert result["is_correct"] is False
    assert result["mastered"] is False


# ── assess: the qualitative gate ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_assess_passes_concept(path_id):
    await _build_basic(path_id)
    # Drive past the memory objective so status reaches the concept one.
    status = json.loads((await MasteryStatusTool().execute(_mastery_path_id=path_id)).content)
    mem_kp = status["next"]["knowledge_point_id"]
    for _ in range(3):
        await MasteryQuizTool().execute(
            _mastery_path_id=path_id, knowledge_point_id=mem_kp, question="q", expected_answer="a"
        )
        await MasteryGradeTool().execute(_mastery_path_id=path_id, answer="a")

    status2 = json.loads((await MasteryStatusTool().execute(_mastery_path_id=path_id)).content)
    concept_kp = status2["next"]["knowledge_point_id"]
    assert status2["next"]["action"] == "probe"
    assert status2["next"]["knowledge_point_type"] == "concept"

    result = json.loads(
        (
            await MasteryAssessTool().execute(
                _mastery_path_id=path_id, knowledge_point_id=concept_kp, passed=True, feedback="ok"
            )
        ).content
    )
    assert result["mastered"] is True
    assert result["next"]["action"] == "complete"


@pytest.mark.asyncio
async def test_assess_rejects_quantitative_type(path_id):
    await _build_basic(path_id)
    status = json.loads((await MasteryStatusTool().execute(_mastery_path_id=path_id)).content)
    mem_kp = status["next"]["knowledge_point_id"]  # a memory objective
    result = await MasteryAssessTool().execute(
        _mastery_path_id=path_id, knowledge_point_id=mem_kp, passed=True
    )
    assert result.success is False
