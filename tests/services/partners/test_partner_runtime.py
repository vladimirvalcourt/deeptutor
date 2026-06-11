"""PartnerRunner: chat-loop event mapping, tool config, session persistence."""

from __future__ import annotations

from typing import Any

import pytest

from deeptutor.core.stream import StreamEvent, StreamEventType
from deeptutor.partners.bus.events import InboundMessage
from deeptutor.partners.bus.queue import MessageBus
from deeptutor.services.partners.manager import PartnerConfig
from deeptutor.services.partners.runtime import PartnerRunner
from deeptutor.services.partners.sessions import PartnerSessionStore


def _event(
    event_type: StreamEventType,
    *,
    content: str = "",
    source: str = "chat",
    metadata: dict[str, Any] | None = None,
) -> StreamEvent:
    return StreamEvent(type=event_type, source=source, content=content, metadata=metadata or {})


def _narration_round(call_id: str, text: str) -> list[StreamEvent]:
    return [
        _event(StreamEventType.CONTENT, content=text, metadata={"call_id": call_id}),
        _event(
            StreamEventType.PROGRESS,
            metadata={
                "trace_kind": "call_status",
                "call_state": "complete",
                "call_role": "narration",
                "call_id": call_id,
            },
        ),
    ]


def _finish(text: str) -> list[StreamEvent]:
    return [
        _event(StreamEventType.CONTENT, content=text, metadata={"call_id": "c-finish"}),
        _event(StreamEventType.RESULT, metadata={"response": text}),
        _event(StreamEventType.DONE),
    ]


class _FakeOrchestrator:
    """Yields a scripted event sequence instead of running the chat loop."""

    script: list[StreamEvent] = []
    # Optional queue of per-turn scripts; when non-empty, each handle() call
    # pops the next one (lets tests model a failed turn + a backup retry).
    scripts: list[list[StreamEvent]] = []
    seen_contexts: list[Any] = []
    activated_selections: list[Any] = []

    def __init__(self) -> None:
        pass

    async def handle(self, context):
        type(self).seen_contexts.append(context)
        script = type(self).scripts.pop(0) if type(self).scripts else type(self).script
        for event in script:
            yield event


@pytest.fixture
def fake_orchestrator(monkeypatch):
    import deeptutor.runtime.orchestrator as orch_mod
    from deeptutor.services.model_selection import runtime as selection_runtime

    _FakeOrchestrator.script = []
    _FakeOrchestrator.scripts = []
    _FakeOrchestrator.seen_contexts = []
    _FakeOrchestrator.activated_selections = []
    monkeypatch.setattr(orch_mod, "ChatOrchestrator", _FakeOrchestrator)

    def _record_activate(selection):
        _FakeOrchestrator.activated_selections.append(selection)
        return (None, None)

    monkeypatch.setattr(selection_runtime, "activate_llm_selection", _record_activate)
    monkeypatch.setattr(selection_runtime, "reset_llm_selection", lambda token: None)
    return _FakeOrchestrator


def _runner(partners_root, config: PartnerConfig | None = None) -> PartnerRunner:
    from deeptutor.partners.config.paths import get_partner_sessions_dir

    config = config or PartnerConfig(name="Ada")
    bus = MessageBus()
    store = PartnerSessionStore(get_partner_sessions_dir("ada"))
    return PartnerRunner("ada", config, bus, store)


def _msg(content: str = "hello", channel: str = "telegram") -> InboundMessage:
    return InboundMessage(channel=channel, sender_id="42", chat_id="42", content=content)


class TestTurnExecution:
    @pytest.mark.asyncio
    async def test_returns_finish_text_and_persists_session(self, partners_root, fake_orchestrator):
        fake_orchestrator.script = _narration_round("c1", "let me check") + _finish(
            "The answer is 4."
        )
        runner = _runner(partners_root)

        final = await runner.process_message(_msg("what is 2+2?"))
        assert final == "The answer is 4."

        history = runner.store.conversation_history("telegram:42")
        assert history == [
            {"role": "user", "content": "what is 2+2?"},
            {"role": "assistant", "content": "The answer is 4."},
        ]

    @pytest.mark.asyncio
    async def test_narration_streams_as_progress_outbound(self, partners_root, fake_orchestrator):
        fake_orchestrator.script = _narration_round("c1", "exploring…") + _finish("done")
        runner = _runner(partners_root)

        await runner.process_message(_msg())
        progress = await runner.bus.outbound.get()
        assert progress.content == "exploring…"
        assert progress.metadata["_progress"] is True
        assert progress.metadata["_tool_hint"] is False

    @pytest.mark.asyncio
    async def test_tool_calls_stream_as_hints_by_default(self, partners_root, fake_orchestrator):
        fake_orchestrator.script = [
            _event(
                StreamEventType.TOOL_CALL,
                content="rag",
                metadata={"args": {"query": "hello world", "_internal": "x"}},
            ),
            *_finish("done"),
        ]
        runner = _runner(partners_root)

        await runner.process_message(_msg())
        hint = await runner.bus.outbound.get()
        assert hint.metadata["_tool_hint"] is True
        assert hint.content.startswith("⚙ rag(")
        assert "hello world" in hint.content
        assert "_internal" not in hint.content

    @pytest.mark.asyncio
    async def test_send_progress_flag_off_suppresses_narration(
        self, partners_root, fake_orchestrator
    ):
        fake_orchestrator.script = _narration_round("c1", "exploring…") + _finish("done")
        config = PartnerConfig(
            name="Ada", channels={"telegram": {"send_progress": False}}
        )
        runner = _runner(partners_root, config)

        await runner.process_message(_msg())
        assert runner.bus.outbound.empty()

    @pytest.mark.asyncio
    async def test_web_channel_never_emits_progress_outbound(
        self, partners_root, fake_orchestrator
    ):
        fake_orchestrator.script = _narration_round("c1", "exploring…") + _finish("done")
        runner = _runner(partners_root)

        await runner.process_message(_msg(channel="web"))
        assert runner.bus.outbound.empty()

    @pytest.mark.asyncio
    async def test_unresolved_ask_user_question_becomes_reply(
        self, partners_root, fake_orchestrator
    ):
        # An unresolved ask_user pause emits the question as a final-response
        # CONTENT event while RESULT carries an empty response.
        fake_orchestrator.script = [
            _event(
                StreamEventType.CONTENT,
                content="Which topic do you mean?",
                metadata={"call_id": "f1", "call_kind": "llm_final_response"},
            ),
            _event(StreamEventType.RESULT, metadata={"response": ""}),
            _event(StreamEventType.DONE),
        ]
        runner = _runner(partners_root)

        final = await runner.process_message(_msg())
        assert final == "Which topic do you mean?"

    @pytest.mark.asyncio
    async def test_backup_model_retries_failed_turn(self, partners_root, fake_orchestrator):
        primary = {"profile_id": "p1", "model_id": "m1"}
        backup = {"profile_id": "p2", "model_id": "m2"}
        fake_orchestrator.scripts = [
            # Turn 1 (primary): hard failure, no answer.
            [
                _event(StreamEventType.ERROR, content="rate limited"),
                _event(StreamEventType.RESULT, metadata={"response": ""}),
                _event(StreamEventType.DONE),
            ],
            # Turn 2 (backup): succeeds.
            _finish("backup answer"),
        ]
        config = PartnerConfig(name="Ada", llm_selection=primary, backup_llm_selection=backup)
        runner = _runner(partners_root, config)

        final = await runner.process_message(_msg())
        assert final == "backup answer"
        assert fake_orchestrator.activated_selections == [primary, backup]

    @pytest.mark.asyncio
    async def test_no_backup_returns_error_text(self, partners_root, fake_orchestrator):
        fake_orchestrator.script = [
            _event(StreamEventType.ERROR, content="rate limited"),
            _event(StreamEventType.RESULT, metadata={"response": ""}),
            _event(StreamEventType.DONE),
        ]
        runner = _runner(partners_root)

        final = await runner.process_message(_msg())
        assert "rate limited" in final
        assert len(fake_orchestrator.seen_contexts) == 1

    @pytest.mark.asyncio
    async def test_successful_turn_never_touches_backup(self, partners_root, fake_orchestrator):
        backup = {"profile_id": "p2", "model_id": "m2"}
        fake_orchestrator.script = _finish("first try works")
        config = PartnerConfig(name="Ada", backup_llm_selection=backup)
        runner = _runner(partners_root, config)

        final = await runner.process_message(_msg())
        assert final == "first try works"
        assert fake_orchestrator.activated_selections == [None]

    @pytest.mark.asyncio
    async def test_inbound_handler_publishes_reply_outbound(self, partners_root, fake_orchestrator):
        fake_orchestrator.script = _finish("reply text")
        runner = _runner(partners_root)

        await runner._handle_inbound(_msg())
        out = await runner.bus.outbound.get()
        assert out.channel == "telegram"
        assert out.chat_id == "42"
        assert out.content == "reply text"


class TestContextAssembly:
    @pytest.mark.asyncio
    async def test_context_carries_soul_tools_and_metadata(self, partners_root, fake_orchestrator):
        from deeptutor.services.partners.workspace import write_soul

        write_soul("ada", "# Soul\nBe kind.")
        fake_orchestrator.script = _finish("ok")
        config = PartnerConfig(
            name="Ada",
            language="zh",
            enabled_tools=["web_search"],
            mcp_tools=["mcp_github_search"],
        )
        runner = _runner(partners_root, config)

        await runner.process_message(
            InboundMessage(
                channel="telegram",
                sender_id="42",
                chat_id="42",
                content="hello",
                metadata={
                    "message_id": "m-1",
                    "thread_ts": "111.222",
                    "_cron_job_id": "cron-1",
                    "_wants_stream": True,
                },
            )
        )
        context = fake_orchestrator.seen_contexts[0]
        assert context.persona_context == "# Soul\nBe kind."
        assert context.enabled_tools == ["web_search"]
        assert context.metadata["mcp_tools_filter"] == ["mcp_github_search"]
        assert context.metadata["channel_metadata"] == {
            "message_id": "m-1",
            "thread_ts": "111.222",
        }
        assert context.metadata["cron_job_id"] == "cron-1"
        assert context.language == "zh"
        assert context.active_capability == "chat"
        assert context.metadata["partner_id"] == "ada"
        assert context.metadata["agent_identity"]["name"] == "Ada"
        assert "wait_for_user_reply" not in context.metadata

    @pytest.mark.asyncio
    async def test_default_tools_resolve_to_full_toggleable_set(
        self, partners_root, fake_orchestrator
    ):
        from deeptutor.agents._shared.tool_composition import default_optional_tools

        fake_orchestrator.script = _finish("ok")
        runner = _runner(partners_root)  # enabled_tools=None

        await runner.process_message(_msg())
        context = fake_orchestrator.seen_contexts[0]
        assert context.enabled_tools == default_optional_tools()
        assert "mcp_tools_filter" not in context.metadata

    @pytest.mark.asyncio
    async def test_history_feeds_next_turn(self, partners_root, fake_orchestrator):
        fake_orchestrator.script = _finish("first reply")
        runner = _runner(partners_root)
        await runner.process_message(_msg("first question"))

        fake_orchestrator.script = _finish("second reply")
        await runner.process_message(_msg("second question"))

        context = fake_orchestrator.seen_contexts[-1]
        assert {"role": "user", "content": "first question"} in context.conversation_history
        assert {
            "role": "assistant",
            "content": "first reply",
        } in context.conversation_history
