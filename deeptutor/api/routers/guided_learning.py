"""Guided Learning API Router."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from deeptutor.learning.models import (
    ErrorType,
    KnowledgePoint,
    LearningModule,
    LearningStage,
    QuizAttempt,
)
from deeptutor.learning.scheduler import SpacedRepetitionScheduler
from deeptutor.learning.service import LearningService
from deeptutor.learning.storage import LearningStore

router = APIRouter()


def _grade_answer(user_answer: str, expected_answer: str) -> bool:
    """Simple comparison. For short answers, do fuzzy match."""
    if not expected_answer:
        return False
    user = user_answer.strip().lower()
    expected = expected_answer.strip().lower()
    if user == expected:
        return True
    # Allow substring match for long expected answers
    if len(expected) > 10 and expected in user:
        return True
    return False


def _classify_error(user_answer: str, expected_answer: str) -> ErrorType | None:
    """Basic classification. Full AI-based classification in error_diagnosis stage."""
    user = user_answer.strip().lower()
    if not user:
        return ErrorType.METACOGNITIVE  # blank = didn't know
    return ErrorType.APPLICATION_ERROR  # default: wrong application


def get_learning_service() -> LearningService:
    # Create a fresh store + service per request to avoid object-level race conditions.
    store = LearningStore()
    return LearningService(store)


def get_scheduler() -> SpacedRepetitionScheduler:
    # Stateless; safe to instantiate per request.
    return SpacedRepetitionScheduler()


# ── Request models ───────────────────────────────────────────────────────────


class AnswerRequest(BaseModel):
    question_id: str
    knowledge_point_id: str
    module_id: str = ""
    user_answer: str = ""
    self_attribution: str = ""


class InitModulesRequest(BaseModel):
    modules: list[dict]  # list of LearningModule-compatible dicts


class ChapterImport(BaseModel):
    title: str
    knowledge_points: list[str] = []


class ImportFromBookRequest(BaseModel):
    chapters: list[ChapterImport]


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.get("/progress")
async def list_all_progress():
    service = get_learning_service()
    return service.list_progress()


@router.get("/progress/{book_id}")
async def get_progress(book_id: str):
    if not book_id or ".." in book_id or "/" in book_id or "\\" in book_id or ":" in book_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Invalid book_id")
    service = get_learning_service()
    progress = service.get_or_create(book_id)
    return progress.model_dump()


@router.post("/progress/{book_id}/answer")
async def submit_answer(book_id: str, body: AnswerRequest):
    if not book_id or ".." in book_id or "/" in book_id or "\\" in book_id or ":" in book_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Invalid book_id")
    service = get_learning_service()
    scheduler = get_scheduler()

    progress = service.get_or_create(book_id)

    # Look up expected answer from server-side store
    store = LearningStore()
    all_answers = store.load_question_answers(book_id)
    expected_answer = all_answers.get(body.question_id, "")
    if not expected_answer:
        raise HTTPException(status_code=400, detail=f"No stored answer for question_id={body.question_id}")

    # Server-side grading
    is_correct = _grade_answer(body.user_answer, expected_answer)

    # Classify error type if wrong
    error_type = None
    if not is_correct:
        error_type = _classify_error(body.user_answer, expected_answer)

    attempt = QuizAttempt(
        question_id=body.question_id,
        knowledge_point_id=body.knowledge_point_id,
        module_id=body.module_id,
        is_correct=is_correct,
        user_answer=body.user_answer,
        error_type=error_type,
        self_attribution=body.self_attribution,
    )
    service.record_quiz_attempt(progress, attempt)

    # Update spaced repetition state
    kp_type = progress.knowledge_types.get(attempt.knowledge_point_id)
    if kp_type is not None:
        state = progress.repetition_states.get(attempt.knowledge_point_id)
        if state is None:
            # Auto-create initial repetition state for new knowledge points
            state = scheduler.get_initial_state(kp_type)
            progress.repetition_states[attempt.knowledge_point_id] = state
        scheduler.schedule_next(state, kp_type, attempt.is_correct)
        progress.review_queue = scheduler.build_review_queue(progress)

    # Update mastery from graded result
    mastery = service.calculate_mastery(progress, attempt.knowledge_point_id)
    service.update_mastery(progress, attempt.knowledge_point_id, mastery)

    service.save(progress)
    return progress.model_dump()


@router.get("/progress/{book_id}/reviews")
async def get_reviews(book_id: str):
    if not book_id or ".." in book_id or "/" in book_id or "\\" in book_id or ":" in book_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Invalid book_id")
    service = get_learning_service()
    scheduler = get_scheduler()

    progress = service.get_or_create(book_id)
    tasks = scheduler.get_due_tasks(progress)
    return {"tasks": [t.model_dump() for t in tasks]}


@router.post("/progress/{book_id}/init-modules")
async def init_modules(book_id: str, body: InitModulesRequest):
    if not book_id or ".." in book_id or "/" in book_id or "\\" in book_id or ":" in book_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Invalid book_id")
    service = get_learning_service()
    progress = service.get_or_create(book_id)
    modules = []
    for i, m in enumerate(body.modules):
        kps_data = m.get("knowledge_points", [])
        try:
            kps = [KnowledgePoint(**kp) for kp in kps_data]
        except PydanticValidationError as exc:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid knowledge_point data in modules[{i}]: {exc.errors()}",
            ) from exc
        # Remove knowledge_points from m to avoid duplicate argument to LearningModule
        m_clean = {k: v for k, v in m.items() if k != "knowledge_points"}
        try:
            modules.append(LearningModule(knowledge_points=kps, **m_clean))
        except PydanticValidationError as exc:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid module data in modules[{i}]: {exc.errors()}",
            ) from exc
    service.init_modules(progress, modules)
    progress.current_module_id = modules[0].id if modules else ""
    progress.current_kp_index = 0
    # NOTE: init_modules always resets to module 0. For incremental module addition,
    # use the merge logic in LearningService.init_modules() which preserves position.
    service.save(progress)
    return {"status": "ok", "module_count": len(modules)}


@router.post("/progress/{book_id}/import-from-book")
async def import_from_book(book_id: str, body: ImportFromBookRequest):
    if not book_id or ".." in book_id or "/" in book_id or "\\" in book_id or ":" in book_id:
        raise HTTPException(status_code=400, detail="Invalid book_id")
    service = get_learning_service()
    progress = service.get_or_create(book_id)
    modules = []
    for i, ch in enumerate(body.chapters):
        kps = [
            KnowledgePoint(id=f"{book_id}_ch{i}_kp{j}", name=kp_name, type="concept", module_id=f"{book_id}_ch{i}")
            for j, kp_name in enumerate(ch.knowledge_points)
        ]
        modules.append(LearningModule(
            id=f"{book_id}_ch{i}",
            name=ch.title or f"Chapter {i+1}",
            order=i,
            pass_threshold=0.7,
            knowledge_points=kps,
        ))
    service.init_modules(progress, modules)
    progress.current_module_id = modules[0].id if modules else ""
    progress.current_kp_index = 0
    service.save(progress)
    return {"status": "ok", "module_count": len(modules)}


@router.delete("/progress/{book_id}")
async def delete_progress(book_id: str):
    if not book_id or ".." in book_id or "/" in book_id or "\\" in book_id or ":" in book_id:
        raise HTTPException(status_code=400, detail="Invalid book_id")
    store = LearningStore()
    if not store.exists(book_id):
        raise HTTPException(status_code=404, detail="Progress not found")
    store.delete(book_id)
    return {"status": "ok"}


@router.post("/progress/{book_id}/redo")
async def redo_progress(book_id: str):
    if not book_id or ".." in book_id or "/" in book_id or "\\" in book_id or ":" in book_id:
        raise HTTPException(status_code=400, detail="Invalid book_id")
    store = LearningStore()
    progress = store.load(book_id)
    if progress is None:
        raise HTTPException(status_code=404, detail="Progress not found")
    progress.current_stage = LearningStage.DIAGNOSTIC_PHASE1
    progress.mastery_levels = {}
    progress.quiz_attempts = []
    progress.error_records = []
    progress.repetition_states = {}
    progress.review_queue = []
    progress.diagnostic = None
    progress.current_kp_index = 0
    progress.current_module_id = progress.modules[0].id if progress.modules else ""
    store.save(progress)
    # Clear stored question answers so fresh questions are generated on redo
    qpath = store._questions_path(book_id)
    if qpath.exists():
        qpath.unlink()
    return {"status": "ok"}


class NotebookRecordInput(BaseModel):
    id: str
    type: str = "note"
    title: str = ""
    output: str = ""


class GenerateFromNotebookRequest(BaseModel):
    notebook_id: str
    records: list[NotebookRecordInput]


@router.post("/progress/{book_id}/generate-from-notebook")
async def generate_from_notebook(book_id: str, body: GenerateFromNotebookRequest):
    if not book_id or ".." in book_id or "/" in book_id or "\\" in book_id or ":" in book_id:
        raise HTTPException(status_code=400, detail="Invalid book_id")
    if not body.records:
        raise HTTPException(status_code=400, detail="No records provided")

    records_text = "\n\n".join(
        f"[{r.type}] {r.title}: {r.output[:500]}"
        for r in body.records[:20]
    )
    from deeptutor.services.llm import complete
    prompt = f"""根据以下笔记本记录，提取知识点并组织为学习模块。
每个模块包含：name（模块名）、knowledge_points（知识点列表，每个有 name 和 type）。
type 可选：memory / concept / procedure / design。
返回 JSON: {{"modules": [{{"name": "...", "knowledge_points": [{{"name": "...", "type": "concept"}}]}}]}}

笔记本记录：
{records_text}"""
    response = await complete(prompt=prompt, system_prompt="你是学习模块规划助手。只输出 JSON。")
    import json
    try:
        data = json.loads(response)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="LLM returned invalid JSON")

    modules_raw = data.get("modules", [])
    if not isinstance(modules_raw, list):
        raise HTTPException(status_code=502, detail="LLM returned invalid structure: modules is not a list")
    service = get_learning_service()
    progress = service.get_or_create(book_id)
    modules = []
    for i, m in enumerate(modules_raw):
        if not isinstance(m, dict) or "name" not in m:
            continue
        kps = []
        for j, kp in enumerate(m.get("knowledge_points", [])):
            if not isinstance(kp, dict) or "name" not in kp:
                continue
            kps.append(KnowledgePoint(
                id=f"{book_id}_nb{i}_kp{j}",
                name=kp["name"],
                type=kp.get("type", "concept"),
                module_id=f"{book_id}_nb{i}",
            ))
        modules.append(LearningModule(
            id=f"{book_id}_nb{i}",
            name=m.get("name", f"模块 {i+1}"),
            order=i,
            pass_threshold=0.7,
            knowledge_points=kps,
        ))
    service.init_modules(progress, modules)
    progress.current_module_id = modules[0].id if modules else ""
    progress.current_kp_index = 0
    service.save(progress)
    return {"status": "ok", "module_count": len(modules), "modules": [m.model_dump() for m in modules]}
