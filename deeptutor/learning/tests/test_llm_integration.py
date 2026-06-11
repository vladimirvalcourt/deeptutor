"""Integration tests for the Mastery Path LLM boundary (``_call_llm``).

The capability owns no pedagogy math; this file pins down the one place it
touches the model: the bounded-retry / graceful-skip wrapper ``_call_llm`` and
the JSON helper ``_safe_json``. RAG was removed in the Mastery Path refactor,
so there is no retrieval/injection to cover here anymore.

``_call_llm`` patches the module-level ``complete`` symbol; the new signature is
``_call_llm(system_prompt, user_message, progress, stage_name, stream, *, timeout=None)``
and it returns ``str | None`` (``None`` on skip/exhaustion) — it never raises.
"""

import asyncio
from contextlib import asynccontextmanager
import inspect
from unittest.mock import AsyncMock, patch

import pytest

from deeptutor.capabilities.mastery_path import MasteryPathCapability
from deeptutor.learning.models import LearningProgress


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


def _progress() -> LearningProgress:
    return LearningProgress(book_id="llm_book")


class TestCallLLM:
    """``_call_llm`` calls the real LLM factory and returns its response."""

    @pytest.mark.asyncio
    async def test_call_llm_calls_complete(self):
        cap = MasteryPathCapability()
        progress = _progress()
        stream = FakeStream()
        with patch(
            "deeptutor.capabilities.mastery_path.complete",
            new_callable=AsyncMock,
        ) as mock_complete:
            mock_complete.return_value = "LLM response"
            result = await cap._call_llm("system", "user", progress, "explain", stream)
            mock_complete.assert_called_once()
            # complete is called with the prompt + system prompt by keyword.
            kwargs = mock_complete.call_args.kwargs
            assert kwargs["prompt"] == "user"
            assert kwargs["system_prompt"] == "system"
            assert result == "LLM response"

    @pytest.mark.asyncio
    async def test_call_llm_success_clears_failure_state(self):
        """A successful call clears any prior failure bookkeeping for the stage."""
        cap = MasteryPathCapability()
        progress = _progress()
        progress.stage_failure_counts["explain"] = 1
        progress.stage_failure_notes["explain"] = "prior timeout"
        stream = FakeStream()
        with patch(
            "deeptutor.capabilities.mastery_path.complete",
            new_callable=AsyncMock,
            return_value="ok",
        ):
            result = await cap._call_llm("system", "user", progress, "explain", stream)
        assert result == "ok"
        assert "explain" not in progress.stage_failure_counts
        assert "explain" not in progress.stage_failure_notes

    def test_call_llm_is_async(self):
        cap = MasteryPathCapability()
        assert hasattr(cap, "_call_llm")
        assert inspect.iscoroutinefunction(cap._call_llm)


class TestCallLLMFailureHandling:
    """On failure ``_call_llm`` degrades gracefully — bounded retry then a
    ``None`` return — rather than raising or returning an error payload."""

    @pytest.mark.asyncio
    async def test_call_llm_returns_none_on_persistent_error(self):
        """When ``complete`` always raises, ``_call_llm`` returns None (does not
        raise, does not return an error JSON) and records the failure."""
        cap = MasteryPathCapability()
        progress = _progress()
        stream = FakeStream()
        with patch(
            "deeptutor.capabilities.mastery_path.complete",
            new_callable=AsyncMock,
            side_effect=Exception("Network down"),
        ) as mock_complete:
            result = await cap._call_llm("system", "user", progress, "explain", stream)
        assert result is None
        # Bounded retry: exactly _STAGE_MAX_FAILURES attempts this turn.
        assert mock_complete.call_count == MasteryPathCapability._STAGE_MAX_FAILURES
        # Failure bookkeeping captured for the cross-turn cumulative gate.
        assert progress.stage_failure_counts.get("explain", 0) >= 1
        assert progress.stage_failure_notes.get("explain") == "Network down"

    @pytest.mark.asyncio
    async def test_call_llm_skips_without_calling_when_cumulative_exhausted(self):
        """Once cumulative failures hit the threshold, the stage is skipped on
        the next turn without touching the model at all."""
        cap = MasteryPathCapability()
        progress = _progress()
        progress.stage_failure_counts["explain"] = (
            MasteryPathCapability._STAGE_MAX_CUMULATIVE_FAILURES
        )
        stream = FakeStream()
        with patch(
            "deeptutor.capabilities.mastery_path.complete",
            new_callable=AsyncMock,
            return_value="should not be called",
        ) as mock_complete:
            result = await cap._call_llm("system", "user", progress, "explain", stream)
        assert result is None
        mock_complete.assert_not_called()
        # The student sees a "已多次失败" skip notice.
        content = [t for kind, t in stream.events if kind == "content"]
        assert any("多次失败" in t for t in content)

    @pytest.mark.asyncio
    async def test_call_llm_handles_timeout(self):
        """A call slower than the timeout is retried then skipped, not awaited
        forever — ``asyncio.wait_for`` bounds each attempt."""
        cap = MasteryPathCapability()
        progress = _progress()
        stream = FakeStream()

        async def _hang(*args, **kwargs):
            await asyncio.sleep(10)
            return "too late"

        with patch(
            "deeptutor.capabilities.mastery_path.complete",
            side_effect=_hang,
        ):
            result = await cap._call_llm(
                "system", "user", progress, "explain", stream, timeout=0.01
            )
        assert result is None
        assert progress.stage_failure_counts.get("explain", 0) >= 1

    @pytest.mark.asyncio
    async def test_call_llm_retry_recovers_on_second_attempt(self):
        """A transient failure followed by success returns the response and
        clears the failure record."""
        cap = MasteryPathCapability()
        progress = _progress()
        stream = FakeStream()
        with patch(
            "deeptutor.capabilities.mastery_path.complete",
            new_callable=AsyncMock,
            side_effect=[Exception("flaky"), "recovered"],
        ) as mock_complete:
            result = await cap._call_llm("system", "user", progress, "explain", stream)
        assert result == "recovered"
        assert mock_complete.call_count == 2
        assert "explain" not in progress.stage_failure_counts


class TestSafeJson:
    """``_safe_json`` parses LLM JSON, falling back to a default on garbage."""

    def test_valid_json(self):
        cap = MasteryPathCapability()
        assert cap._safe_json('{"key": "value"}', {}) == {"key": "value"}

    def test_invalid_json_fallback(self):
        cap = MasteryPathCapability()
        assert cap._safe_json("not json", {"fallback": True}) == {"fallback": True}

    def test_extracts_from_markdown_fence(self):
        cap = MasteryPathCapability()
        fenced = '```json\n{"questions": []}\n```'
        assert cap._safe_json(fenced, {}) == {"questions": []}

    def test_non_dict_response_uses_default(self):
        """A JSON array (non-dict) is not a valid stage payload -> default."""
        cap = MasteryPathCapability()
        assert cap._safe_json("[1, 2, 3]", {"questions": []}) == {"questions": []}
