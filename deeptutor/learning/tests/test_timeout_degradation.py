"""Tests for the LLM bounded-retry + per-stage graceful-degradation logic.

The Mastery Path capability funnels every model call through a single method,
``MasteryPathCapability._call_llm(system, user, progress, stage_name, stream,
*, timeout=None)``. That method owns the resilience policy:

  * up to ``_STAGE_MAX_FAILURES`` attempts per turn, then return ``None``;
  * a cross-turn cumulative gate (``_STAGE_MAX_CUMULATIVE_FAILURES``) that skips
    the call entirely once a stage has failed too often across turns;
  * bookkeeping in ``stage_failure_counts`` / ``stage_failure_notes`` that a
    successful call clears.

Each stage handler degrades by branching on a ``None`` return. These tests
exercise both halves: ``_call_llm`` itself (by patching the underlying
``complete``) and each handler's ``None`` branch (by stubbing ``cap._call_llm``
to return ``None`` directly).

RAG was removed, so there is no longer any RAG-timeout path to test.
"""

from contextlib import asynccontextmanager
import json
from unittest.mock import AsyncMock

import pytest

from deeptutor.capabilities.mastery_path import MasteryPathCapability
from deeptutor.learning.models import (
    ErrorRecord,
    ErrorType,
    KnowledgePoint,
    KnowledgeType,
    LearningModule,
    LearningProgress,
    LearningStage,
)
from deeptutor.learning.scheduler import SpacedRepetitionScheduler
from deeptutor.learning.service import LearningService
from deeptutor.learning.storage import LearningStore


class FakeStream:
    """Minimal StreamBus stand-in: records stage/content events and replays a
    queued list of student inputs for ``wait_for_input``."""

    def __init__(self) -> None:
        self.events: list[tuple[str, str]] = []
        self.inputs: list[str] = []
        self._input_idx = 0

    @asynccontextmanager
    async def stage(self, name, source="", metadata=None):
        self.events.append(("stage", name))
        yield

    async def content(self, text, source="", stage="", metadata=None):
        self.events.append(("content", text))

    async def wait_for_input(self, prompt, source="", timeout=None):
        if self._input_idx < len(self.inputs):
            val = self.inputs[self._input_idx]
            self._input_idx += 1
            return val
        return ""

    def content_texts(self) -> list[str]:
        return [t for kind, t in self.events if kind == "content"]


def _make_cap(tmp_path) -> MasteryPathCapability:
    """A real capability wired to a tmp-path store/service/scheduler."""
    store = LearningStore(root=tmp_path)
    service = LearningService(store)
    return MasteryPathCapability(
        service=service, scheduler=SpacedRepetitionScheduler(), store=store
    )


def _progress_with_module() -> LearningProgress:
    kp = KnowledgePoint(id="kp1", name="Test KP", type=KnowledgeType.MEMORY, module_id="m1")
    mod = LearningModule(id="m1", name="Test Module", order=0, knowledge_points=[kp])
    progress = LearningProgress(book_id="book1")
    progress.modules = [mod]
    progress.current_module_id = "m1"
    progress.knowledge_types["kp1"] = KnowledgeType.MEMORY
    progress.current_stage = LearningStage.EXPLAIN
    return progress


# ── _call_llm: bounded retry on failure ───────────────────────────────────


@pytest.mark.asyncio
async def test_call_llm_retries_then_returns_none_and_records_failure(tmp_path, monkeypatch):
    """Every attempt raising should exhaust _STAGE_MAX_FAILURES retries, return
    None, and record the failure count + note (no exception escapes)."""
    cap = _make_cap(tmp_path)
    import deeptutor.capabilities.mastery_path as mp_mod

    complete_mock = AsyncMock(side_effect=RuntimeError("LLM unavailable"))
    monkeypatch.setattr(mp_mod, "complete", complete_mock)

    progress = _progress_with_module()
    stream = FakeStream()

    result = await cap._call_llm("system", "user", progress, "explain", stream)

    assert result is None
    # One increment per failed attempt.
    assert complete_mock.call_count == MasteryPathCapability._STAGE_MAX_FAILURES
    assert progress.stage_failure_counts["explain"] == MasteryPathCapability._STAGE_MAX_FAILURES
    assert progress.stage_failure_notes["explain"]  # non-empty note recorded
    # The exhausted-retries degradation message is streamed.
    assert any("暂时不可用" in t for t in stream.content_texts())


@pytest.mark.asyncio
async def test_call_llm_success_clears_prior_failures(tmp_path, monkeypatch):
    """A successful call clears any prior failure count + note for the stage."""
    cap = _make_cap(tmp_path)
    import deeptutor.capabilities.mastery_path as mp_mod

    monkeypatch.setattr(mp_mod, "complete", AsyncMock(return_value="ok response"))

    progress = _progress_with_module()
    progress.stage_failure_counts["explain"] = 2
    progress.stage_failure_notes["explain"] = "previous timeout"
    stream = FakeStream()

    result = await cap._call_llm("system", "user", progress, "explain", stream)

    assert result == "ok response"
    assert "explain" not in progress.stage_failure_counts
    assert "explain" not in progress.stage_failure_notes


@pytest.mark.asyncio
async def test_call_llm_cumulative_gate_skips_without_calling(tmp_path, monkeypatch):
    """Once cumulative failures hit the threshold, _call_llm returns None
    without calling the model and streams the 'multiple failures' message."""
    cap = _make_cap(tmp_path)
    import deeptutor.capabilities.mastery_path as mp_mod

    complete_mock = AsyncMock(return_value="should not be called")
    monkeypatch.setattr(mp_mod, "complete", complete_mock)

    progress = _progress_with_module()
    progress.stage_failure_counts["explain"] = MasteryPathCapability._STAGE_MAX_CUMULATIVE_FAILURES
    stream = FakeStream()

    result = await cap._call_llm("system", "user", progress, "explain", stream)

    assert result is None
    complete_mock.assert_not_called()
    assert any("多次失败" in t for t in stream.content_texts())


@pytest.mark.asyncio
async def test_call_llm_below_cumulative_gate_still_retries(tmp_path, monkeypatch):
    """Below the cumulative gate, a flaky stage still attempts its retries and
    accumulates further failures."""
    cap = _make_cap(tmp_path)
    import deeptutor.capabilities.mastery_path as mp_mod

    complete_mock = AsyncMock(side_effect=RuntimeError("LLM unavailable"))
    monkeypatch.setattr(mp_mod, "complete", complete_mock)

    progress = _progress_with_module()
    progress.stage_failure_counts["explain"] = 2  # below threshold of 4
    stream = FakeStream()

    result = await cap._call_llm("system", "user", progress, "explain", stream)

    assert result is None
    assert complete_mock.call_count == MasteryPathCapability._STAGE_MAX_FAILURES
    assert progress.stage_failure_counts["explain"] > 2


@pytest.mark.asyncio
async def test_call_llm_timeout_counts_as_failure(tmp_path, monkeypatch):
    """A model call that exceeds the per-call timeout is treated as a failure
    and folds into the retry/skip bookkeeping."""
    import asyncio

    cap = _make_cap(tmp_path)
    import deeptutor.capabilities.mastery_path as mp_mod

    async def _slow(*args, **kwargs):
        await asyncio.sleep(10)
        return "too late"

    monkeypatch.setattr(mp_mod, "complete", _slow)

    progress = _progress_with_module()
    stream = FakeStream()

    # Tiny timeout so the wait_for fires immediately.
    result = await cap._call_llm("system", "user", progress, "diagnostic", stream, timeout=0.01)

    assert result is None
    assert progress.stage_failure_counts["diagnostic"] == MasteryPathCapability._STAGE_MAX_FAILURES


# ── Stage handlers degrade on a None LLM result ────────────────────────────


@pytest.mark.asyncio
async def test_explain_skip_advances_after_kp(tmp_path):
    """When EXPLAIN's LLM call is skipped (None), the handler advances via
    _advance_after_kp rather than to FEYNMAN_CHECK. With a single KP that lands
    on PRACTICE."""
    cap = _make_cap(tmp_path)
    cap._call_llm = AsyncMock(return_value=None)
    progress = _progress_with_module()
    progress.current_stage = LearningStage.EXPLAIN
    stream = FakeStream()

    await cap._run_explain(progress, stream)

    # Single KP -> _advance_after_kp goes to PRACTICE, not FEYNMAN_CHECK.
    assert progress.current_stage == LearningStage.PRACTICE


@pytest.mark.asyncio
async def test_practice_skip_advances_to_error_diagnosis(tmp_path):
    """When PRACTICE's LLM call is skipped (None), advance straight to
    ERROR_DIAGNOSIS without running a quiz."""
    cap = _make_cap(tmp_path)
    cap._call_llm = AsyncMock(return_value=None)
    progress = _progress_with_module()
    progress.current_stage = LearningStage.PRACTICE
    stream = FakeStream()

    await cap._run_practice(progress, stream)

    assert progress.current_stage == LearningStage.ERROR_DIAGNOSIS
    # No quiz ran, so no attempts were recorded.
    assert progress.quiz_attempts == []


@pytest.mark.asyncio
async def test_diagnostic_skip_sets_empty_result_and_advances(tmp_path):
    """When DIAGNOSTIC's LLM call is skipped (None), an empty DiagnosticResult
    is stored and the stage advances to EXPLAIN."""
    cap = _make_cap(tmp_path)
    cap._call_llm = AsyncMock(return_value=None)
    progress = _progress_with_module()
    progress.current_stage = LearningStage.DIAGNOSTIC
    stream = FakeStream()

    await cap._run_diagnostic(progress, stream)

    assert progress.current_stage == LearningStage.EXPLAIN
    assert progress.diagnostic is not None
    assert progress.diagnostic.total_questions == 0
    assert progress.diagnostic.correct_count == 0


@pytest.mark.asyncio
async def test_feynman_skip_persists_unevaluated_explanation(tmp_path):
    """When FEYNMAN_CHECK's LLM judge is skipped (None) and the student gave a
    non-blank explanation, the explanation is persisted as unevaluated and the
    '未评估' feedback is streamed."""
    cap = _make_cap(tmp_path)
    cap._call_llm = AsyncMock(return_value=None)
    progress = _progress_with_module()
    progress.current_stage = LearningStage.FEYNMAN_CHECK
    stream = FakeStream()
    stream.inputs = ["My explanation of the concept"]

    await cap._run_feynman_check(progress, stream)

    # The unevaluated explanation is preserved for next time.
    assert progress.feynman_explanations.get("kp1") == "My explanation of the concept"
    assert any("未评估" in t for t in stream.content_texts())
    # A skipped judge is a non-pass: it counts as a retry, then advances.
    assert progress.current_stage != LearningStage.FEYNMAN_CHECK


@pytest.mark.asyncio
async def test_feynman_blank_skips_judge_and_advances(tmp_path):
    """A blank explanation short-circuits FEYNMAN_CHECK: no LLM judge, advance
    via _advance_after_kp."""
    cap = _make_cap(tmp_path)
    cap._call_llm = AsyncMock(return_value="should not be called")
    progress = _progress_with_module()
    progress.current_stage = LearningStage.FEYNMAN_CHECK
    stream = FakeStream()
    stream.inputs = [""]  # blank

    await cap._run_feynman_check(progress, stream)

    cap._call_llm.assert_not_called()
    # Single KP -> _advance_after_kp -> PRACTICE.
    assert progress.current_stage == LearningStage.PRACTICE


@pytest.mark.asyncio
async def test_feynman_pass_clears_explanation_and_seeds_mastery(tmp_path):
    """A passing judge clears any prior unevaluated explanation and seeds
    mastery at the Feynman pass floor."""
    cap = _make_cap(tmp_path)
    cap._call_llm = AsyncMock(
        return_value=json.dumps({"passed": True, "feedback": "很好", "gap": ""})
    )
    progress = _progress_with_module()
    progress.current_stage = LearningStage.FEYNMAN_CHECK
    progress.feynman_explanations["kp1"] = "previous unevaluated explanation"
    stream = FakeStream()
    stream.inputs = ["My explanation"]

    await cap._run_feynman_check(progress, stream)

    assert "kp1" not in progress.feynman_explanations
    assert progress.mastery_levels["kp1"] == pytest.approx(
        MasteryPathCapability._FEYNMAN_PASS_MASTERY
    )
    # Single KP, passed -> _advance_after_kp -> PRACTICE.
    assert progress.current_stage == LearningStage.PRACTICE


@pytest.mark.asyncio
async def test_error_diagnosis_skip_marks_records_unavailable(tmp_path):
    """When ERROR_DIAGNOSIS's LLM call is skipped (None), each active record is
    annotated 'error_diagnosis_unavailable' and the stage advances to REVIEW."""
    cap = _make_cap(tmp_path)
    cap._call_llm = AsyncMock(return_value=None)
    progress = _progress_with_module()
    progress.current_stage = LearningStage.ERROR_DIAGNOSIS
    progress.error_records = [
        ErrorRecord(
            id="er1",
            question_id="q1",
            knowledge_point_id="kp1",
            module_id="m1",
            error_type=ErrorType.APPLICATION_ERROR,
            status="active",
        )
    ]
    stream = FakeStream()

    await cap._run_error_diagnosis(progress, stream)

    assert progress.current_stage == LearningStage.REVIEW
    assert progress.error_records[0].ai_confirmation == "error_diagnosis_unavailable"


@pytest.mark.asyncio
async def test_error_diagnosis_passes_timeout_through(tmp_path, monkeypatch):
    """ERROR_DIAGNOSIS uses the dedicated, shorter timeout when it calls the
    model."""
    cap = _make_cap(tmp_path)
    captured: dict = {}

    async def _spy(system, user, progress, stage_name, stream, *, timeout=None):
        captured["timeout"] = timeout
        captured["stage_name"] = stage_name
        return None

    cap._call_llm = _spy
    progress = _progress_with_module()
    progress.current_stage = LearningStage.ERROR_DIAGNOSIS
    progress.error_records = [
        ErrorRecord(
            id="er1",
            question_id="q1",
            knowledge_point_id="kp1",
            module_id="m1",
            error_type=ErrorType.APPLICATION_ERROR,
            status="active",
        )
    ]
    stream = FakeStream()

    await cap._run_error_diagnosis(progress, stream)

    assert captured["stage_name"] == "error_diagnosis"
    assert captured["timeout"] == MasteryPathCapability._ERROR_DIAGNOSIS_TIMEOUT_SECONDS


@pytest.mark.asyncio
async def test_error_diagnosis_no_active_records_skips_llm(tmp_path):
    """With no active/retrying error records, ERROR_DIAGNOSIS makes no LLM call
    and advances to REVIEW."""
    cap = _make_cap(tmp_path)
    cap._call_llm = AsyncMock(return_value="should not be called")
    progress = _progress_with_module()
    progress.current_stage = LearningStage.ERROR_DIAGNOSIS
    progress.error_records = []
    stream = FakeStream()

    await cap._run_error_diagnosis(progress, stream)

    cap._call_llm.assert_not_called()
    assert progress.current_stage == LearningStage.REVIEW


@pytest.mark.asyncio
async def test_review_skip_uses_static_fallback_text(tmp_path):
    """When REVIEW's LLM call is skipped (None), a static fallback review prompt
    is streamed and the stage advances (COMPLETED for the last module)."""
    cap = _make_cap(tmp_path)
    cap._call_llm = AsyncMock(return_value=None)
    progress = _progress_with_module()
    progress.current_stage = LearningStage.REVIEW
    stream = FakeStream()

    await cap._run_review(progress, stream)

    assert progress.current_stage == LearningStage.COMPLETED
    assert any("请回顾" in t for t in stream.content_texts())
    # The review queue/states were still initialized despite the LLM skip.
    assert "kp1" in progress.repetition_states


@pytest.mark.asyncio
async def test_review_advances_to_next_module_explain(tmp_path):
    """When a next module exists, REVIEW loops back to EXPLAIN on the next
    module even when the LLM call is skipped."""
    cap = _make_cap(tmp_path)
    cap._call_llm = AsyncMock(return_value=None)
    progress = _progress_with_module()
    kp2 = KnowledgePoint(id="kp2", name="Second KP", type=KnowledgeType.MEMORY, module_id="m2")
    progress.modules.append(
        LearningModule(id="m2", name="Module 2", order=1, knowledge_points=[kp2])
    )
    progress.knowledge_types["kp2"] = KnowledgeType.MEMORY
    progress.current_stage = LearningStage.REVIEW
    stream = FakeStream()

    await cap._run_review(progress, stream)

    assert progress.current_stage == LearningStage.EXPLAIN
    assert progress.current_module_id == "m2"
    assert progress.current_kp_index == 0
