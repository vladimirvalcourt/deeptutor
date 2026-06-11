"""Tests for the ERROR_DIAGNOSIS stage of the Mastery Path capability.

The stage classifies each active/retrying error record via a single LLM call
and then advances to REVIEW. When the model is unavailable (``_call_llm``
returns ``None``) it must degrade gracefully: mark every active record as
``error_diagnosis_unavailable`` and still advance, never wedge the loop.
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
from deeptutor.learning.service import LearningService
from deeptutor.learning.storage import LearningStore


class FakeStream:
    def __init__(self) -> None:
        self.events: list[tuple[str, str]] = []

    @asynccontextmanager
    async def stage(self, name, source="", metadata=None):
        self.events.append(("stage", name))
        yield

    async def content(self, text, source="", stage="", metadata=None):
        self.events.append(("content", text))


def _make_capability() -> MasteryPathCapability:
    """Build a capability with an in-memory (no-root) store so ``save`` is a
    no-op file-wise, and stub the single LLM seam to a default skip (None)."""
    cap = MasteryPathCapability.__new__(MasteryPathCapability)
    cap._store = LearningStore.__new__(LearningStore)
    cap._store._root = None
    cap._service = LearningService(cap._store)
    cap._scheduler = None
    cap._call_llm = AsyncMock(return_value=None)
    return cap


def _make_progress(*, error_records=None) -> LearningProgress:
    progress = LearningProgress(book_id="book1")
    progress.current_stage = LearningStage.ERROR_DIAGNOSIS
    progress.current_module_id = "m1"
    progress.modules = [
        LearningModule(
            id="m1",
            name="Module 1",
            order=0,
            knowledge_points=[
                KnowledgePoint(id="kp1", name="KP1", type=KnowledgeType.CONCEPT, module_id="m1")
            ],
        )
    ]
    if error_records is None:
        error_records = [
            ErrorRecord(
                id="er1",
                question_id="q1",
                knowledge_point_id="kp1",
                module_id="m1",
                error_type=ErrorType.APPLICATION_ERROR,
                status="active",
            )
        ]
    progress.error_records.extend(error_records)
    return progress


@pytest.mark.asyncio
async def test_error_diagnosis_llm_skip_advances_to_review_and_marks_unavailable():
    """When the LLM is unavailable (``_call_llm`` -> None), every active record
    is flagged unavailable, its prior error_type is preserved, and the stage
    advances to REVIEW rather than wedging on the flaky model."""
    cap = _make_capability()
    cap._call_llm = AsyncMock(return_value=None)
    progress = _make_progress()
    stream = FakeStream()

    await cap._run_error_diagnosis(progress, stream)

    assert progress.current_stage == LearningStage.REVIEW
    assert progress.error_records[0].error_type == ErrorType.APPLICATION_ERROR
    assert progress.error_records[0].ai_confirmation == "error_diagnosis_unavailable"


@pytest.mark.asyncio
async def test_error_diagnosis_uses_extended_timeout():
    """The stage must call the LLM with the longer error-diagnosis budget."""
    cap = _make_capability()
    call_llm = AsyncMock(return_value=None)
    cap._call_llm = call_llm
    progress = _make_progress()
    stream = FakeStream()

    await cap._run_error_diagnosis(progress, stream)

    assert call_llm.await_count == 1
    assert call_llm.await_args.kwargs["timeout"] == cap._ERROR_DIAGNOSIS_TIMEOUT_SECONDS


@pytest.mark.asyncio
async def test_error_diagnosis_no_active_records_skips_to_review():
    """With no active/retrying records there is nothing to diagnose: skip the
    LLM entirely and advance to REVIEW."""
    cap = _make_capability()
    call_llm = AsyncMock(return_value=None)
    cap._call_llm = call_llm
    graduated = ErrorRecord(
        id="er0",
        question_id="q0",
        knowledge_point_id="kp1",
        module_id="m1",
        error_type=ErrorType.APPLICATION_ERROR,
        status="graduated",
    )
    progress = _make_progress(error_records=[graduated])
    stream = FakeStream()

    await cap._run_error_diagnosis(progress, stream)

    assert progress.current_stage == LearningStage.REVIEW
    call_llm.assert_not_awaited()
    assert graduated.ai_confirmation == ""


@pytest.mark.asyncio
async def test_error_diagnosis_applies_llm_diagnoses():
    """A successful diagnosis reclassifies the error_type and records the AI
    confirmation on the matching record, then advances to REVIEW."""
    cap = _make_capability()
    diagnoses = {
        "diagnoses": [
            {
                "question_id": "q1",
                "error_type": "structural",
                "ai_confirmation": "concept gap in prerequisites",
            }
        ]
    }
    cap._call_llm = AsyncMock(return_value=json.dumps(diagnoses, ensure_ascii=False))
    progress = _make_progress()
    stream = FakeStream()

    await cap._run_error_diagnosis(progress, stream)

    assert progress.current_stage == LearningStage.REVIEW
    rec = progress.error_records[0]
    assert rec.error_type == ErrorType.KNOWLEDGE_STRUCTURAL
    assert rec.ai_confirmation == "concept gap in prerequisites"


@pytest.mark.asyncio
async def test_error_diagnosis_ignores_invalid_error_type():
    """A bogus error_type label leaves the existing classification intact while
    still recording any AI confirmation."""
    cap = _make_capability()
    diagnoses = {
        "diagnoses": [
            {
                "question_id": "q1",
                "error_type": "not_a_real_type",
                "ai_confirmation": "kept original type",
            }
        ]
    }
    cap._call_llm = AsyncMock(return_value=json.dumps(diagnoses, ensure_ascii=False))
    progress = _make_progress()
    stream = FakeStream()

    await cap._run_error_diagnosis(progress, stream)

    rec = progress.error_records[0]
    assert rec.error_type == ErrorType.APPLICATION_ERROR
    assert rec.ai_confirmation == "kept original type"


@pytest.mark.asyncio
async def test_error_diagnosis_diagnoses_retrying_records():
    """``retrying`` records are active for diagnosis just like ``active`` ones."""
    cap = _make_capability()
    cap._call_llm = AsyncMock(return_value=None)
    retrying = ErrorRecord(
        id="er2",
        question_id="q2",
        knowledge_point_id="kp1",
        module_id="m1",
        error_type=ErrorType.APPLICATION_ERROR,
        status="retrying",
    )
    progress = _make_progress(error_records=[retrying])
    stream = FakeStream()

    await cap._run_error_diagnosis(progress, stream)

    assert progress.current_stage == LearningStage.REVIEW
    assert retrying.ai_confirmation == "error_diagnosis_unavailable"
