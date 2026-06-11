"""Tests for the Feynman-check retry limit in the Mastery Path capability."""

from contextlib import asynccontextmanager
import json
from unittest.mock import AsyncMock

import pytest

from deeptutor.capabilities.mastery_path import MasteryPathCapability
from deeptutor.learning.models import (
    KnowledgePoint,
    LearningModule,
    LearningProgress,
    LearningStage,
)
from deeptutor.learning.service import LearningService
from deeptutor.learning.storage import LearningStore


class FakeStream:
    """Minimal StreamBus mock for capability testing."""

    def __init__(self, user_inputs: list[str] | None = None):
        self._inputs = list(user_inputs or [])
        self._input_idx = 0
        self.events: list[str] = []

    @asynccontextmanager
    async def stage(self, name, source="", metadata=None):
        self.events.append(f"stage:{name}")
        yield

    async def content(self, text, source="", stage="", metadata=None):
        self.events.append(text)

    async def wait_for_input(self, prompt, source="", stage="", timeout=None):
        if self._input_idx < len(self._inputs):
            val = self._inputs[self._input_idx]
            self._input_idx += 1
            return val
        return ""


def _make_progress(kp_id="kp1", kp_name="Test KP") -> LearningProgress:
    progress = LearningProgress(book_id="testbook")
    progress.modules = [
        LearningModule(
            id="m1",
            name="M1",
            order=0,
            knowledge_points=[
                KnowledgePoint(id=kp_id, name=kp_name, type="concept", module_id="m1")
            ],
        )
    ]
    progress.current_module_id = "m1"
    progress.current_kp_index = 0
    progress.current_stage = LearningStage.FEYNMAN_CHECK
    return progress


def _make_capability(llm_response: str | None) -> MasteryPathCapability:
    """Build a capability without touching the filesystem (no LearningStore root)
    and with the LLM mocked at the handler level via ``_call_llm``."""
    cap = MasteryPathCapability.__new__(MasteryPathCapability)
    store = LearningStore.__new__(LearningStore)
    store._root = None  # not used: these tests never save to disk
    cap._store = store
    cap._service = LearningService(store)
    cap._scheduler = None  # the Feynman path never touches the scheduler
    # Mock the single LLM entry point so no network/JSON contract is exercised.
    cap._call_llm = AsyncMock(return_value=llm_response)
    # save() is a no-op so the in-memory progress isn't flushed to a missing root.
    cap._service.save = lambda progress: None
    return cap


@pytest.mark.asyncio
async def test_feynman_3_failures_marks_weak_and_advances_to_practice():
    """After 3 consecutive Feynman failures the KP is marked weak and, since the
    module has a single KP, the stage advances to PRACTICE (was PRACTICE_QUIZ)."""
    failed_response = json.dumps({"passed": False, "feedback": "not quite", "gap": ""})
    progress = _make_progress()

    # Fail 3 times. A fresh capability per turn mirrors the per-turn lifecycle.
    for _ in range(3):
        cap = _make_capability(failed_response)
        stream = FakeStream(user_inputs=["my explanation"])
        await cap._run_feynman_check(progress, stream)

    # Single KP exhausted -> _advance_after_kp lands on PRACTICE.
    assert progress.current_stage == LearningStage.PRACTICE
    # Mastery marked as weak.
    assert progress.mastery_levels["kp1"] == 0.0
    # Retry counter reached the cap.
    assert progress.feynman_retries["kp1"] == MasteryPathCapability._FEYNMAN_MAX_RETRIES


@pytest.mark.asyncio
async def test_feynman_failure_loops_back_to_explain():
    """A failure below the retry cap loops back to EXPLAIN and bumps the counter."""
    failed_response = json.dumps({"passed": False, "feedback": "no", "gap": ""})
    progress = _make_progress()

    cap = _make_capability(failed_response)
    stream = FakeStream(user_inputs=["my explanation"])
    await cap._run_feynman_check(progress, stream)

    assert progress.feynman_retries["kp1"] == 1
    assert progress.current_stage == LearningStage.EXPLAIN


@pytest.mark.asyncio
async def test_feynman_pass_resets_counter_and_sets_mastery():
    """Passing the Feynman check resets the retry counter, sets the pass-level
    mastery floor, and advances past the per-KP loop."""
    failed_response = json.dumps({"passed": False, "feedback": "no", "gap": ""})
    passed_response = json.dumps({"passed": True, "feedback": "good", "gap": ""})

    progress = _make_progress()

    # Fail twice (stays below the cap, loops to EXPLAIN each time).
    for _ in range(2):
        cap = _make_capability(failed_response)
        stream = FakeStream(user_inputs=["my explanation"])
        await cap._run_feynman_check(progress, stream)

    assert progress.feynman_retries["kp1"] == 2
    assert progress.current_stage == LearningStage.EXPLAIN

    # Pass on the 3rd attempt.
    cap = _make_capability(passed_response)
    stream = FakeStream(user_inputs=["my explanation"])
    await cap._run_feynman_check(progress, stream)

    # Counter reset, mastery floored at the pass level, single KP -> PRACTICE.
    assert progress.feynman_retries["kp1"] == 0
    assert progress.mastery_levels["kp1"] == MasteryPathCapability._FEYNMAN_PASS_MASTERY
    assert progress.current_stage == LearningStage.PRACTICE


@pytest.mark.asyncio
async def test_feynman_blank_answer_skips_kp_without_calling_llm():
    """A blank explanation advances past the KP without grading and without an
    LLM call (the per-KP loop must not wedge on an empty answer)."""
    cap = _make_capability(json.dumps({"passed": True, "feedback": "", "gap": ""}))
    progress = _make_progress()
    stream = FakeStream(user_inputs=[""])

    await cap._run_feynman_check(progress, stream)

    cap._call_llm.assert_not_awaited()
    # Single KP exhausted -> PRACTICE; no retry recorded, no mastery set.
    assert progress.current_stage == LearningStage.PRACTICE
    assert "kp1" not in progress.feynman_retries
    assert "kp1" not in progress.mastery_levels


@pytest.mark.asyncio
async def test_feynman_llm_skip_preserves_explanation_and_retries():
    """When ``_call_llm`` returns None (stage skipped/degraded), the student's
    explanation is preserved and the turn counts as a (non-passing) retry rather
    than stalling — below the cap it loops back to EXPLAIN."""
    cap = _make_capability(None)
    progress = _make_progress()
    stream = FakeStream(user_inputs=["my explanation"])

    await cap._run_feynman_check(progress, stream)

    # Explanation retained for a later turn; treated as a failed attempt.
    assert progress.feynman_explanations["kp1"] == "my explanation"
    assert progress.feynman_retries["kp1"] == 1
    assert progress.current_stage == LearningStage.EXPLAIN
