"""End-to-end Mastery Path flow test.

Walks one module / one knowledge point through the full state machine the
``MasteryPathCapability`` drives:

    DIAGNOSTIC -> EXPLAIN -> FEYNMAN_CHECK -> PRACTICE
               -> ERROR_DIAGNOSIS -> REVIEW -> COMPLETED

The LLM is mocked at the handler level (``cap._call_llm``) so each stage gets a
canned response in call order; grading/mastery/scheduling run for real through
``LearningService``.
"""

from contextlib import asynccontextmanager
import json
from unittest.mock import AsyncMock

import pytest

from deeptutor.capabilities.mastery_path import MasteryPathCapability
from deeptutor.learning.models import (
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


def _make_cap(tmp_path):
    """Build a capability wired to a real service/store/scheduler over tmp_path."""
    store = LearningStore(root=tmp_path)
    service = LearningService(store)
    scheduler = SpacedRepetitionScheduler()
    cap = MasteryPathCapability(service=service, scheduler=scheduler, store=store)
    return cap, service, store


def _single_kp_progress() -> LearningProgress:
    kp = KnowledgePoint(id="kp1", name="Photosynthesis", type=KnowledgeType.CONCEPT, module_id="m1")
    mod = LearningModule(id="m1", name="Biology", order=0, knowledge_points=[kp])
    progress = LearningProgress(book_id="e2e_book")
    progress.modules = [mod]
    progress.current_module_id = "m1"
    progress.current_kp_index = 0
    progress.current_stage = LearningStage.DIAGNOSTIC
    progress.knowledge_types["kp1"] = KnowledgeType.CONCEPT
    return progress


@pytest.mark.asyncio
async def test_e2e_diagnostic_to_completed(tmp_path):
    """Full happy-path flow from DIAGNOSTIC through COMPLETED, 1 module / 1 KP."""
    cap, service, _store = _make_cap(tmp_path)
    progress = _single_kp_progress()
    stream = FakeStream()

    # Canned LLM responses, in stage-handler call order.
    diag_data = json.dumps(
        {
            "questions": [
                {
                    "id": "dq1",
                    "question": "What is photosynthesis?",
                    "answer": "photosynthesis",
                    "type": "short",
                }
            ],
        }
    )
    practice_data = json.dumps(
        {
            "questions": [
                {
                    "id": "pq1",
                    "question": "Define photosynthesis.",
                    "answer": "photosynthesis",
                    "type": "short",
                    "knowledge_point_id": "kp1",
                }
            ],
        }
    )

    cap._call_llm = AsyncMock(
        side_effect=[
            diag_data,  # 1. DIAGNOSTIC quiz
            "Explain content",  # 2. EXPLAIN
            json.dumps({"passed": True, "feedback": "good", "gap": ""}),  # 3. FEYNMAN_CHECK judge
            practice_data,  # 4. PRACTICE quiz
            "Review content",  # 5. REVIEW
        ]
    )

    # Student inputs: diagnostic answer, feynman explanation, practice answer.
    stream.inputs = [
        "photosynthesis",  # diagnostic question
        "Plants convert sunlight to energy",  # feynman explanation
        "photosynthesis",  # practice question
    ]

    # DIAGNOSTIC -> EXPLAIN
    assert progress.current_stage == LearningStage.DIAGNOSTIC
    await cap._run_diagnostic(progress, stream)
    assert progress.current_stage == LearningStage.EXPLAIN
    assert progress.diagnostic is not None
    assert progress.diagnostic.total_questions == 1
    assert progress.diagnostic.correct_count == 1

    # EXPLAIN -> FEYNMAN_CHECK
    await cap._run_explain(progress, stream)
    assert progress.current_stage == LearningStage.FEYNMAN_CHECK

    # FEYNMAN_CHECK -> PRACTICE (single KP, passed=True -> _advance_after_kp -> PRACTICE)
    await cap._run_feynman_check(progress, stream)
    assert progress.current_stage == LearningStage.PRACTICE
    # Passing Feynman seeds mastery at the pass floor.
    assert progress.mastery_levels["kp1"] == pytest.approx(
        MasteryPathCapability._FEYNMAN_PASS_MASTERY
    )

    # PRACTICE -> ERROR_DIAGNOSIS
    await cap._run_practice(progress, stream)
    assert progress.current_stage == LearningStage.ERROR_DIAGNOSIS

    # ERROR_DIAGNOSIS -> REVIEW (practice answer was correct, no active error records)
    await cap._run_error_diagnosis(progress, stream)
    assert progress.current_stage == LearningStage.REVIEW

    # REVIEW -> COMPLETED (no next module)
    await cap._run_review(progress, stream)
    assert progress.current_stage == LearningStage.COMPLETED

    # ERROR_DIAGNOSIS makes no LLM call when there are no errors, so 5 total.
    assert cap._call_llm.call_count == 5

    # Both quizzes graded in-turn: diagnostic + practice = 2 recorded attempts.
    assert len(progress.quiz_attempts) == 2
    qids = {a.question_id for a in progress.quiz_attempts}
    assert qids == {"dq1", "pq1"}
    assert all(a.is_correct for a in progress.quiz_attempts)
    # Practice question was attributed to kp1; diagnostic carries no KP.
    by_qid = {a.question_id: a for a in progress.quiz_attempts}
    assert by_qid["pq1"].knowledge_point_id == "kp1"

    # Review stage initialized the repetition state + queue for the module KP.
    assert "kp1" in progress.repetition_states
    assert any(t.knowledge_point_id == "kp1" for t in progress.review_queue)


@pytest.mark.asyncio
async def test_e2e_wrong_practice_opens_error_record_and_diagnosis(tmp_path):
    """A wrong practice answer opens an error record, and ERROR_DIAGNOSIS then
    fires an LLM classification that updates the record's error type."""
    cap, service, _store = _make_cap(tmp_path)
    progress = _single_kp_progress()
    # Jump straight to PRACTICE so the test stays focused on the error path.
    progress.current_stage = LearningStage.PRACTICE
    stream = FakeStream()

    practice_data = json.dumps(
        {
            "questions": [
                {
                    "id": "pq1",
                    "question": "Define photosynthesis.",
                    "answer": "photosynthesis",
                    "type": "short",
                    "knowledge_point_id": "kp1",
                }
            ],
        }
    )
    diagnosis_data = json.dumps(
        {
            "diagnoses": [
                {
                    "question_id": "pq1",
                    "error_type": "deviation",
                    "ai_confirmation": "misread the prompt",
                }
            ],
        }
    )
    cap._call_llm = AsyncMock(side_effect=[practice_data, diagnosis_data])

    # Wrong answer -> error record opened (application error from non-blank wrong answer).
    stream.inputs = ["a totally wrong answer"]

    await cap._run_practice(progress, stream)
    assert progress.current_stage == LearningStage.ERROR_DIAGNOSIS
    assert len(progress.error_records) == 1
    rec = progress.error_records[0]
    assert rec.question_id == "pq1"
    assert rec.knowledge_point_id == "kp1"
    assert rec.status == "active"

    await cap._run_error_diagnosis(progress, stream)
    assert progress.current_stage == LearningStage.REVIEW
    # LLM diagnosis overwrote the coarse error_type and recorded its confirmation.
    assert rec.error_type.value == "deviation"
    assert rec.ai_confirmation == "misread the prompt"
    assert cap._call_llm.call_count == 2


@pytest.mark.asyncio
async def test_e2e_error_diagnosis_skips_gracefully_when_llm_unavailable(tmp_path):
    """When the LLM is unavailable (``_call_llm`` returns None), ERROR_DIAGNOSIS
    marks active records unavailable and still advances to REVIEW."""
    cap, service, _store = _make_cap(tmp_path)
    progress = _single_kp_progress()
    progress.current_stage = LearningStage.PRACTICE
    stream = FakeStream()

    practice_data = json.dumps(
        {
            "questions": [
                {
                    "id": "pq1",
                    "question": "Define photosynthesis.",
                    "answer": "photosynthesis",
                    "type": "short",
                    "knowledge_point_id": "kp1",
                }
            ],
        }
    )
    # Practice produces a quiz; error diagnosis LLM call is skipped (None).
    cap._call_llm = AsyncMock(side_effect=[practice_data, None])
    stream.inputs = ["wrong"]

    await cap._run_practice(progress, stream)
    assert len(progress.error_records) == 1

    await cap._run_error_diagnosis(progress, stream)
    assert progress.current_stage == LearningStage.REVIEW
    assert progress.error_records[0].ai_confirmation == "error_diagnosis_unavailable"


@pytest.mark.asyncio
async def test_e2e_multi_kp_walks_each_kp_then_practices(tmp_path):
    """With two KPs in one module, the per-KP loop should run EXPLAIN+FEYNMAN
    twice before reaching PRACTICE."""
    cap, service, _store = _make_cap(tmp_path)
    kp1 = KnowledgePoint(id="kp1", name="A", type=KnowledgeType.CONCEPT, module_id="m1")
    kp2 = KnowledgePoint(id="kp2", name="B", type=KnowledgeType.CONCEPT, module_id="m1")
    mod = LearningModule(id="m1", name="Mod", order=0, knowledge_points=[kp1, kp2])
    progress = LearningProgress(book_id="multi_book")
    progress.modules = [mod]
    progress.current_module_id = "m1"
    progress.current_kp_index = 0
    progress.current_stage = LearningStage.EXPLAIN
    progress.knowledge_types["kp1"] = KnowledgeType.CONCEPT
    progress.knowledge_types["kp2"] = KnowledgeType.CONCEPT

    stream = FakeStream()
    passed = json.dumps({"passed": True, "feedback": "ok", "gap": ""})
    cap._call_llm = AsyncMock(
        side_effect=[
            "explain kp1",
            passed,  # KP1
            "explain kp2",
            passed,  # KP2
        ]
    )
    # Two feynman explanations.
    stream.inputs = ["explanation 1", "explanation 2"]

    # KP1: EXPLAIN -> FEYNMAN -> (more KPs) -> EXPLAIN
    await cap._run_explain(progress, stream)
    assert progress.current_stage == LearningStage.FEYNMAN_CHECK
    await cap._run_feynman_check(progress, stream)
    assert progress.current_stage == LearningStage.EXPLAIN
    assert progress.current_kp_index == 1

    # KP2: EXPLAIN -> FEYNMAN -> (no more KPs) -> PRACTICE
    await cap._run_explain(progress, stream)
    assert progress.current_stage == LearningStage.FEYNMAN_CHECK
    await cap._run_feynman_check(progress, stream)
    assert progress.current_stage == LearningStage.PRACTICE
    assert progress.mastery_levels["kp1"] == pytest.approx(0.6)
    assert progress.mastery_levels["kp2"] == pytest.approx(0.6)


@pytest.mark.asyncio
async def test_e2e_review_advances_to_next_module(tmp_path):
    """When a further module exists, REVIEW loops back to EXPLAIN on the next
    module rather than COMPLETED."""
    cap, service, _store = _make_cap(tmp_path)
    kp1 = KnowledgePoint(id="kp1", name="A", type=KnowledgeType.CONCEPT, module_id="m1")
    kp2 = KnowledgePoint(id="kp2", name="B", type=KnowledgeType.CONCEPT, module_id="m2")
    mod1 = LearningModule(id="m1", name="Mod1", order=0, knowledge_points=[kp1])
    mod2 = LearningModule(id="m2", name="Mod2", order=1, knowledge_points=[kp2])
    progress = LearningProgress(book_id="two_module_book")
    progress.modules = [mod1, mod2]
    progress.current_module_id = "m1"
    progress.current_kp_index = 0
    progress.current_stage = LearningStage.REVIEW
    progress.knowledge_types["kp1"] = KnowledgeType.CONCEPT
    progress.knowledge_types["kp2"] = KnowledgeType.CONCEPT

    stream = FakeStream()
    cap._call_llm = AsyncMock(return_value="Review content")

    await cap._run_review(progress, stream)
    assert progress.current_stage == LearningStage.EXPLAIN
    assert progress.current_module_id == "m2"
    assert progress.current_kp_index == 0


@pytest.mark.asyncio
async def test_e2e_explain_skip_advances_after_kp(tmp_path):
    """If the EXPLAIN LLM call is skipped (None), the handler should fall through
    to ``_advance_after_kp`` rather than wedging on FEYNMAN_CHECK."""
    cap, service, _store = _make_cap(tmp_path)
    progress = _single_kp_progress()
    progress.current_stage = LearningStage.EXPLAIN
    stream = FakeStream()

    cap._call_llm = AsyncMock(return_value=None)
    await cap._run_explain(progress, stream)
    # Single KP -> _advance_after_kp -> PRACTICE.
    assert progress.current_stage == LearningStage.PRACTICE
