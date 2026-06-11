"""Mastery Path capability — structured mastery-based learning over a turn stream.

Drives a small state machine inside the agent/turn loop::

    diagnostic -> (per knowledge point: explain -> feynman_check)
               -> practice -> error_diagnosis -> review -> completed

Each handler makes at most one LLM call, optionally runs an interactive
question loop (blocking on the stream for the student's answer), updates the
persisted ``LearningProgress``, and advances the stage. Grading and mastery
math live in ``LearningService`` / ``grading`` / ``mastery`` — this file only
orchestrates the conversation; it owns no pedagogy arithmetic.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from deeptutor.core.capability_protocol import BaseCapability, CapabilityManifest
from deeptutor.core.context import UnifiedContext
from deeptutor.core.stream_bus import StreamBus
from deeptutor.learning import prompts
from deeptutor.learning.models import (
    DiagnosticResult,
    ErrorType,
    KnowledgeType,
    LearningProgress,
    LearningStage,
)
from deeptutor.learning.scheduler import SpacedRepetitionScheduler
from deeptutor.learning.service import LearningService
from deeptutor.learning.storage import LearningStore
from deeptutor.services.llm import complete
from deeptutor.utils.json_parser import parse_json_response

from ._i18n import StatusI18n

logger = logging.getLogger(__name__)

# Answer-bearing keys stripped from a question before it is streamed to the
# client, and read back to grade the student's answer in-turn.
_ANSWER_KEYS = ("answer", "correct_answer", "explanation", "solution")
_INPUT_TIMEOUT = 120


class MasteryPathCapability(BaseCapability):
    manifest = CapabilityManifest(
        name="mastery_path",
        description="Mastery Path: structured mastery-based learning with spaced repetition",
        # Single source of truth: the stages ARE the LearningStage enum.
        stages=[s.value for s in LearningStage],
        tools_used=[],
    )

    _FEYNMAN_MAX_RETRIES = 3
    _FEYNMAN_PASS_MASTERY = 0.6
    _LLM_TIMEOUT_SECONDS = 60
    _ERROR_DIAGNOSIS_TIMEOUT_SECONDS = 45
    _STAGE_MAX_FAILURES = 2
    _STAGE_MAX_CUMULATIVE_FAILURES = 4

    def __init__(
        self,
        service: LearningService | None = None,
        scheduler: SpacedRepetitionScheduler | None = None,
        store: LearningStore | None = None,
    ) -> None:
        if service is not None:
            self._service = service
            self._store = service._store
        else:
            self._store = store or LearningStore()
            self._service = LearningService(self._store)
        self._scheduler = scheduler or SpacedRepetitionScheduler()

    # ── State-machine entry ──────────────────────────────────────────────

    async def run(self, context: UnifiedContext, stream: StreamBus) -> None:
        language = getattr(context, "language", "zh") or "zh"
        status = StatusI18n(self.manifest.name, language)
        self._active_status = status
        localized_prompts = prompts.get_learning_prompts(language)
        progress = self._service.get_or_create(self._resolve_book_id(context))
        stage = progress.current_stage

        if stage == LearningStage.COMPLETED:
            async with stream.stage("completed", source=self.manifest.name):
                await stream.content(
                    status.t("completed", "学习流程已完成。"), source=self.manifest.name
                )
            return

        if not any(mod.knowledge_points for mod in progress.modules):
            async with stream.stage("blocked", source=self.manifest.name):
                await stream.content(
                    status.t(
                        "blocked_no_modules",
                        "请先创建至少一个包含知识点的学习模块，再开始 Mastery Path。",
                    ),
                    source=self.manifest.name,
                )
            return

        handler = self._STAGE_HANDLERS.get(stage)
        if handler is None:
            return
        try:
            await handler(self, progress, stream, localized_prompts, status)
        except Exception as exc:
            logger.error("Stage %s failed: %s", stage, exc, exc_info=True)
            async with stream.stage("error", source=self.manifest.name):
                await stream.content(
                    status.t("stage_failed", "阶段执行失败，进度已保存，下次将继续此阶段。"),
                    source=self.manifest.name,
                )
        finally:
            self._service.save(progress)

    # ── Context / lookup helpers ─────────────────────────────────────────

    @staticmethod
    def _resolve_book_id(context: UnifiedContext) -> str:
        book_id = getattr(context, "book_id", None)
        if book_id:
            return book_id
        refs = (getattr(context, "metadata", {}) or {}).get("book_references", [])
        if refs:
            ref = refs[0]
            return ref if isinstance(ref, str) else (ref.get("book_id") or ref.get("id", "default"))
        return getattr(context, "session_id", "default")

    def _current_knowledge_points(self, progress: LearningProgress) -> list:
        if not progress.modules:
            return []
        for mod in progress.modules:
            if mod.id == progress.current_module_id:
                return mod.knowledge_points
        return progress.modules[0].knowledge_points

    def _current_kp(self, progress: LearningProgress):
        kps = self._current_knowledge_points(progress)
        if kps and progress.current_kp_index < len(kps):
            return kps[progress.current_kp_index]
        return None

    @staticmethod
    def _safe_json(text: str, default: dict) -> dict:
        result = parse_json_response(text, fallback=default)
        return result if isinstance(result, dict) else default

    @staticmethod
    def _is_passed(value: Any) -> bool:
        return value is True or str(value).lower() in ("true", "1", "yes")

    @staticmethod
    def _prompt(localized_prompts: dict[str, Any], path: str, default: str) -> str:
        value: Any = localized_prompts
        for part in path.split("."):
            if not isinstance(value, dict):
                return default
            value = value.get(part)
        return value if isinstance(value, str) and value else default

    @staticmethod
    def _default_status() -> StatusI18n:
        return StatusI18n("mastery_path", "zh")

    @staticmethod
    def _default_prompts() -> dict[str, Any]:
        return prompts.get_learning_prompts("zh")

    # ── LLM call with bounded retry + graceful per-stage skip ────────────

    async def _call_llm(
        self,
        system_prompt: str,
        user_message: str,
        progress: LearningProgress,
        stage_name: str,
        stream: StreamBus,
        *,
        status: StatusI18n | None = None,
        timeout: float | None = None,
    ) -> str | None:
        """Call the LLM with bounded retry. Returns ``None`` when the stage is
        skipped — either it already failed too many times across turns, or
        every retry this turn failed — so the caller can degrade gracefully
        instead of wedging the state machine on a flaky model."""
        status = (
            status or getattr(self, "_active_status", None) or StatusI18n(self.manifest.name, "zh")
        )
        if progress.stage_failure_counts.get(stage_name, 0) >= self._STAGE_MAX_CUMULATIVE_FAILURES:
            await stream.content(
                status.t(
                    "stage_skipped", "阶段 {stage_name} 已多次失败，跳过。", stage_name=stage_name
                ),
                source=self.manifest.name,
                metadata={"type": "stage_skipped", "stage": stage_name},
            )
            return None
        for attempt in range(self._STAGE_MAX_FAILURES):
            try:
                response = await asyncio.wait_for(
                    complete(prompt=user_message, system_prompt=system_prompt),
                    timeout=timeout or self._LLM_TIMEOUT_SECONDS,
                )
                progress.stage_failure_counts.pop(stage_name, None)
                progress.stage_failure_notes.pop(stage_name, None)
                return response
            except Exception as exc:
                progress.stage_failure_counts[stage_name] = (
                    progress.stage_failure_counts.get(stage_name, 0) + 1
                )
                progress.stage_failure_notes[stage_name] = str(exc)
                if attempt < self._STAGE_MAX_FAILURES - 1:
                    continue
                await stream.content(
                    status.t(
                        "stage_degraded",
                        "阶段 {stage_name} 暂时不可用，已记录并跳过。",
                        stage_name=stage_name,
                    ),
                    source=self.manifest.name,
                    metadata={"type": "stage_degraded", "stage": stage_name},
                )
        return None

    # ── Question helpers ─────────────────────────────────────────────────

    @staticmethod
    def _question_id(item: Any, prefix: str, index: int) -> str:
        if isinstance(item, dict):
            return str(item.get("question_id") or item.get("id") or f"{prefix}_{index}")
        return f"{prefix}_{index}"

    @classmethod
    def _extract_answers(cls, data: dict, prefix: str) -> dict[str, str]:
        """Map question_id -> expected answer, accepting either a parallel
        ``answers`` array or inline answer keys on each question."""
        items = data.get("questions") or data.get("exercises") or []
        parallel = data.get("answers", [])
        answers: dict[str, str] = {}
        for i, item in enumerate(items):
            qid = cls._question_id(item, prefix, i)
            if isinstance(item, dict):
                for key in _ANSWER_KEYS:
                    if key in item:
                        answers[qid] = str(item[key])
                        break
            if qid not in answers and i < len(parallel):
                answers[qid] = str(parallel[i])
        return answers

    @staticmethod
    def _strip_answer(question: Any) -> Any:
        if not isinstance(question, dict):
            return question
        return {k: v for k, v in question.items() if k not in _ANSWER_KEYS}

    @classmethod
    def _attribute_kps(cls, data: dict, kps: list, prefix: str) -> dict[str, str]:
        """Map question_id -> knowledge_point_id from LLM-supplied labels,
        distributing un-attributed questions round-robin across module KPs
        instead of biasing every question toward the first."""

        def norm(value: Any) -> str:
            return str(value or "").strip().lower()

        label_to_id: dict[str, str] = {}
        for kp in kps:
            label_to_id[norm(kp.id)] = kp.id
            label_to_id[norm(kp.name)] = kp.id
        items = data.get("questions") or data.get("exercises") or []
        result: dict[str, str] = {}
        for i, item in enumerate(items):
            qid = cls._question_id(item, prefix, i)
            resolved = ""
            if isinstance(item, dict):
                raw = (
                    item.get("knowledge_point_id")
                    or item.get("knowledge_point")
                    or item.get("knowledge_point_name")
                    or item.get("kp_id")
                    or item.get("kp")
                    or ""
                )
                resolved = label_to_id.get(norm(raw), "")
            if not resolved and kps:
                resolved = kps[i % len(kps)].id
            result[qid] = resolved
        return result

    async def _run_quiz(
        self,
        progress: LearningProgress,
        stream: StreamBus,
        data: dict,
        *,
        prefix: str,
        attribute_kps: bool,
        status: StatusI18n | None = None,
    ) -> tuple[int, int]:
        """Stream each question (answers stripped), block for the student's
        answer, and grade it via ``LearningService.grade_and_record``. Returns
        ``(correct_count, total)``. Answers are kept in memory for the turn —
        nothing is persisted server-side because grading happens in-turn."""
        items = data.get("questions") or data.get("exercises") or []
        status = status or self._default_status()
        answers = self._extract_answers(data, prefix)
        kps = self._current_knowledge_points(progress)
        kp_map = self._attribute_kps(data, kps, prefix) if attribute_kps else {}
        default_kp = kps[0].id if (attribute_kps and kps) else ""
        correct = 0
        for i, item in enumerate(items):
            qid = self._question_id(item, prefix, i)
            await stream.content(
                json.dumps(
                    {"question": self._strip_answer(item), "question_id": qid}, ensure_ascii=False
                ),
                source=self.manifest.name,
            )
            user_answer = await stream.wait_for_input(
                status.t("answer_prompt", "请回答"),
                source=self.manifest.name,
                timeout=_INPUT_TIMEOUT,
            )
            if self._service.grade_and_record(
                progress,
                question_id=qid,
                knowledge_point_id=kp_map.get(qid, "") or default_kp,
                module_id=progress.current_module_id or "",
                user_answer=user_answer,
                expected_answer=answers.get(qid, ""),
                scheduler=self._scheduler,
            ):
                correct += 1
        return correct, len(items)

    # ── Stage handlers ───────────────────────────────────────────────────

    async def _run_diagnostic(
        self,
        progress: LearningProgress,
        stream: StreamBus,
        localized_prompts: dict[str, Any] | None = None,
        status: StatusI18n | None = None,
    ) -> None:
        localized_prompts = localized_prompts or self._default_prompts()
        status = status or self._default_status()
        self._active_status = status
        async with stream.stage("diagnostic", source=self.manifest.name):
            await stream.content(
                status.t("diagnostic_generating", "正在生成诊断题..."), source=self.manifest.name
            )
            response = await self._call_llm(
                self._prompt(localized_prompts, "diagnostic.system", prompts.DIAGNOSTIC_SYSTEM),
                self._prompt(localized_prompts, "diagnostic.user", prompts.DIAGNOSTIC_USER),
                progress,
                "diagnostic",
                stream,
            )
            if response is None:
                progress.diagnostic = DiagnosticResult()
            else:
                data = self._safe_json(response, {"questions": [], "answers": []})
                correct, total = await self._run_quiz(
                    progress,
                    stream,
                    data,
                    prefix="diag",
                    attribute_kps=False,
                    status=status,
                )
                progress.diagnostic = DiagnosticResult(total_questions=total, correct_count=correct)
            self._service.advance_stage(progress, LearningStage.EXPLAIN)

    async def _run_explain(
        self,
        progress: LearningProgress,
        stream: StreamBus,
        localized_prompts: dict[str, Any] | None = None,
        status: StatusI18n | None = None,
    ) -> None:
        localized_prompts = localized_prompts or self._default_prompts()
        status = status or self._default_status()
        self._active_status = status
        async with stream.stage("explain", source=self.manifest.name):
            kp = self._current_kp(progress)
            default_kp = status.t("current_knowledge_point", "当前知识点")
            await stream.content(
                status.t("explain_generating", "正在生成讲解内容..."), source=self.manifest.name
            )
            response = await self._call_llm(
                self._prompt(localized_prompts, "explain.system", prompts.EXPLAIN_SYSTEM),
                self._prompt(localized_prompts, "explain.user", prompts.EXPLAIN_USER).format(
                    knowledge_point=kp.name if kp else default_kp
                ),
                progress,
                "explain",
                stream,
            )
            if response is None:
                self._advance_after_kp(progress)
                return
            await stream.content(response, source=self.manifest.name)
            self._service.advance_stage(progress, LearningStage.FEYNMAN_CHECK)

    async def _run_feynman_check(
        self,
        progress: LearningProgress,
        stream: StreamBus,
        localized_prompts: dict[str, Any] | None = None,
        status: StatusI18n | None = None,
    ) -> None:
        localized_prompts = localized_prompts or self._default_prompts()
        status = status or self._default_status()
        self._active_status = status
        async with stream.stage("feynman_check", source=self.manifest.name):
            kp = self._current_kp(progress)
            kp_name = kp.name if kp else status.t("current_knowledge_point", "当前知识点")
            kp_id = kp.id if kp else ""

            await stream.content(
                status.t(
                    "feynman_instruction",
                    '请用自己的话解释"{kp_name}"，就像教一个高中生一样。',
                    kp_name=kp_name,
                ),
                source=self.manifest.name,
            )
            explanation = await stream.wait_for_input(
                status.t("feynman_input_prompt", "请输入你的解释"),
                source=self.manifest.name,
                timeout=_INPUT_TIMEOUT,
            )
            if not explanation.strip():
                self._advance_after_kp(progress)
                return

            await stream.content(
                status.t("feynman_evaluating", "正在评估你的解释..."), source=self.manifest.name
            )
            response = await self._call_llm(
                self._prompt(localized_prompts, "feynman.system", prompts.FEYNMAN_SYSTEM),
                self._prompt(localized_prompts, "feynman.user", prompts.FEYNMAN_USER).format(
                    knowledge_point=kp_name
                )
                + "\n"
                + status.t(
                    "student_explanation_label",
                    "学生解释：{explanation}",
                    explanation=explanation,
                ),
                progress,
                "feynman_check",
                stream,
            )
            if response is None:
                if kp_id:
                    progress.feynman_explanations[kp_id] = explanation
                result = {
                    "passed": False,
                    "feedback": status.t(
                        "feynman_unavailable_feedback",
                        "未评估（评估服务暂时不可用）",
                    ),
                    "gap": "",
                }
            else:
                result = self._safe_json(response, {"passed": False, "feedback": "", "gap": ""})

            await stream.content(json.dumps(result, ensure_ascii=False), source=self.manifest.name)
            if self._is_passed(result.get("passed")):
                progress.feynman_retries[kp_id] = 0
                progress.feynman_explanations.pop(kp_id, None)
                if kp_id:
                    progress.mastery_levels[kp_id] = max(
                        progress.mastery_levels.get(kp_id, 0.0), self._FEYNMAN_PASS_MASTERY
                    )
                self._advance_after_kp(progress)
                return

            retries = progress.feynman_retries.get(kp_id, 0) + 1
            progress.feynman_retries[kp_id] = retries
            if retries >= self._FEYNMAN_MAX_RETRIES:
                if kp_id:
                    progress.mastery_levels[kp_id] = 0.0
                await stream.content(
                    status.t(
                        "feynman_weak_skipped",
                        "该知识点已尝试 {retries} 次，标记为薄弱并跳过。",
                        retries=retries,
                    ),
                    source=self.manifest.name,
                )
                self._advance_after_kp(progress)
            else:
                await stream.content(
                    status.t(
                        "feynman_retry_feedback",
                        "反馈：{feedback}（第 {retries}/{max_retries} 次重试）",
                        feedback=result.get(
                            "feedback",
                            status.t("feynman_retry_default", "请重新学习"),
                        ),
                        retries=retries,
                        max_retries=self._FEYNMAN_MAX_RETRIES,
                    ),
                    source=self.manifest.name,
                )
                self._service.advance_stage(progress, LearningStage.EXPLAIN)

    async def _run_practice(
        self,
        progress: LearningProgress,
        stream: StreamBus,
        localized_prompts: dict[str, Any] | None = None,
        status: StatusI18n | None = None,
    ) -> None:
        localized_prompts = localized_prompts or self._default_prompts()
        status = status or self._default_status()
        self._active_status = status
        async with stream.stage("practice", source=self.manifest.name):
            kps = self._current_knowledge_points(progress)
            await stream.content(
                status.t("practice_generating", "正在生成练习题..."), source=self.manifest.name
            )
            response = await self._call_llm(
                self._prompt(localized_prompts, "practice.system", prompts.PRACTICE_SYSTEM),
                self._prompt(localized_prompts, "practice.user", prompts.PRACTICE_USER).format(
                    knowledge_points=", ".join(kp.name for kp in kps)
                ),
                progress,
                "practice",
                stream,
            )
            if response is None:
                self._service.advance_stage(progress, LearningStage.ERROR_DIAGNOSIS)
                return
            data = self._safe_json(response, {"questions": []})
            prefix = (
                f"{progress.current_module_id}_practice"
                if progress.current_module_id
                else "practice"
            )
            correct, total = await self._run_quiz(
                progress,
                stream,
                data,
                prefix=prefix,
                attribute_kps=True,
                status=status,
            )
            if total:
                pct = correct / total * 100
                tail = (
                    status.t("practice_tail_good", " 表现不错，继续加油！")
                    if pct >= 70
                    else status.t("practice_tail_review", " 建议回顾相关知识点。")
                )
                await stream.content(
                    status.t(
                        "practice_complete",
                        "练习完成！正确 {correct}/{total} 题（{pct:.0f}%）。{tail}",
                        correct=correct,
                        total=total,
                        pct=pct,
                        tail=tail,
                    ),
                    source=self.manifest.name,
                )
            self._service.advance_stage(progress, LearningStage.ERROR_DIAGNOSIS)

    async def _run_error_diagnosis(
        self,
        progress: LearningProgress,
        stream: StreamBus,
        localized_prompts: dict[str, Any] | None = None,
        status: StatusI18n | None = None,
    ) -> None:
        localized_prompts = localized_prompts or self._default_prompts()
        status = status or self._default_status()
        self._active_status = status
        async with stream.stage("error_diagnosis", source=self.manifest.name):
            active = [r for r in progress.error_records if r.status in ("active", "retrying")]
            if not active:
                await stream.content(
                    status.t("no_errors_skip", "没有待诊断的错题，跳过。"),
                    source=self.manifest.name,
                )
                self._service.advance_stage(progress, LearningStage.REVIEW)
                return
            await stream.content(
                status.t("error_diagnosis_generating", "正在生成错误诊断..."),
                source=self.manifest.name,
            )
            error_context = json.dumps(
                [
                    {
                        "question_id": r.question_id,
                        "error_type": r.error_type.value if r.error_type else "",
                        "self_attribution": r.self_attribution,
                    }
                    for r in active
                ],
                ensure_ascii=False,
            )
            response = await self._call_llm(
                self._prompt(
                    localized_prompts,
                    "error_diagnosis.system",
                    prompts.ERROR_DIAGNOSIS_SYSTEM,
                ),
                self._prompt(
                    localized_prompts,
                    "error_diagnosis.user",
                    prompts.ERROR_DIAGNOSIS_USER,
                )
                + f"\n{status.t('error_context_label', '错题记录')}：{error_context}",
                progress,
                "error_diagnosis",
                stream,
                timeout=self._ERROR_DIAGNOSIS_TIMEOUT_SECONDS,
            )
            if response is None:
                for rec in active:
                    rec.ai_confirmation = status.t(
                        "error_diagnosis_unavailable",
                        "error_diagnosis_unavailable",
                    )
                self._service.advance_stage(progress, LearningStage.REVIEW)
                return
            data = self._safe_json(response, {"diagnoses": []})
            by_qid = {r.question_id: r for r in active}
            for diag in data.get("diagnoses", []):
                rec = by_qid.get(diag.get("question_id", ""))
                if rec is None:
                    continue
                new_type = diag.get("error_type", "")
                if new_type:
                    try:
                        rec.error_type = ErrorType(new_type)
                    except (ValueError, KeyError):
                        pass
                rec.ai_confirmation = diag.get("ai_confirmation", "")
            await stream.content(response, source=self.manifest.name)
            self._service.advance_stage(progress, LearningStage.REVIEW)

    async def _run_review(
        self,
        progress: LearningProgress,
        stream: StreamBus,
        localized_prompts: dict[str, Any] | None = None,
        status: StatusI18n | None = None,
    ) -> None:
        localized_prompts = localized_prompts or self._default_prompts()
        status = status or self._default_status()
        self._active_status = status
        async with stream.stage("review", source=self.manifest.name):
            self._init_repetition_states(progress)
            progress.review_queue = self._scheduler.build_review_queue(progress)
            await stream.content(
                status.t("review_generating", "正在生成复习内容..."), source=self.manifest.name
            )
            response = await self._call_llm(
                self._prompt(localized_prompts, "review.system", prompts.REVIEW_SYSTEM),
                self._prompt(localized_prompts, "review.user", prompts.REVIEW_USER),
                progress,
                "review",
                stream,
            )
            await stream.content(
                response
                or status.t(
                    "review_fallback",
                    "请回顾之前的学习内容，重点复习薄弱知识点。",
                ),
                source=self.manifest.name,
            )
            if self._advance_to_next_module(progress):
                self._service.advance_stage(progress, LearningStage.EXPLAIN)
            else:
                self._service.advance_stage(progress, LearningStage.COMPLETED)

    # ── Loop topology ────────────────────────────────────────────────────

    def _advance_after_kp(self, progress: LearningProgress) -> None:
        """Move to the next knowledge point's EXPLAIN, or to PRACTICE once the
        current module's knowledge points are exhausted."""
        kps = self._current_knowledge_points(progress)
        if progress.current_kp_index + 1 < len(kps):
            progress.current_kp_index += 1
            self._service.advance_stage(progress, LearningStage.EXPLAIN)
        else:
            self._service.advance_stage(progress, LearningStage.PRACTICE)

    def _advance_to_next_module(self, progress: LearningProgress) -> bool:
        ids = [m.id for m in progress.modules]
        if not progress.current_module_id or progress.current_module_id not in ids:
            return False
        idx = ids.index(progress.current_module_id)
        if idx + 1 < len(ids):
            progress.current_module_id = ids[idx + 1]
            progress.current_kp_index = 0
            return True
        return False

    def _init_repetition_states(self, progress: LearningProgress) -> None:
        for mod in progress.modules:
            if mod.id != progress.current_module_id:
                continue
            for kp in mod.knowledge_points:
                if kp.id not in progress.repetition_states:
                    kp_type = progress.knowledge_types.get(kp.id, KnowledgeType.MEMORY)
                    progress.repetition_states[kp.id] = self._scheduler.get_initial_state(kp_type)

    _STAGE_HANDLERS = {
        LearningStage.DIAGNOSTIC: _run_diagnostic,
        LearningStage.EXPLAIN: _run_explain,
        LearningStage.FEYNMAN_CHECK: _run_feynman_check,
        LearningStage.PRACTICE: _run_practice,
        LearningStage.ERROR_DIAGNOSIS: _run_error_diagnosis,
        LearningStage.REVIEW: _run_review,
    }


__all__ = ["MasteryPathCapability"]
