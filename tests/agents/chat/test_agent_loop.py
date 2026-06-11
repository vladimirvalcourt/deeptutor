from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from typing import Any

import pytest

from deeptutor.agents.chat.agent_loop import InlineThinkFilter
from deeptutor.agents.chat.agentic_pipeline import AgenticChatPipeline
from deeptutor.core.context import Attachment, UnifiedContext
from deeptutor.core.stream import StreamEvent, StreamEventType
from deeptutor.core.stream_bus import StreamBus
from deeptutor.core.tool_protocol import ToolResult


async def _collect_bus_events(bus: StreamBus) -> tuple[list[StreamEvent], asyncio.Task[Any]]:
    events: list[StreamEvent] = []

    async def _consume() -> None:
        async for event in bus.subscribe():
            events.append(event)

    consumer = asyncio.create_task(_consume())
    await asyncio.sleep(0)
    return events, consumer  # type: ignore[return-value]


def _llm_chunk(
    *,
    content: str | None = None,
    tool_calls: list[dict[str, Any]] | None = None,
) -> SimpleNamespace:
    delta_fields: dict[str, Any] = {"content": content}
    if tool_calls is not None:
        delta_fields["tool_calls"] = [
            SimpleNamespace(
                index=tc.get("index", i),
                id=tc.get("id"),
                function=SimpleNamespace(
                    name=tc.get("name"),
                    arguments=tc.get("arguments"),
                ),
            )
            for i, tc in enumerate(tool_calls)
        ]
    else:
        delta_fields["tool_calls"] = None
    return SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(**delta_fields))])


async def _async_llm_stream(chunks: list[SimpleNamespace]):
    for chunk in chunks:
        yield chunk


class _ScriptedChatClient:
    def __init__(self, scripted: list[list[SimpleNamespace]]) -> None:
        self._script = list(scripted)
        self.call_count = 0
        self.calls: list[dict[str, Any]] = []

        class _Completions:
            def __init__(self, parent: _ScriptedChatClient) -> None:
                self.parent = parent

            async def create(self, **kwargs):
                self.parent.call_count += 1
                self.parent.calls.append({**kwargs, "messages": list(kwargs.get("messages") or [])})
                if not self.parent._script:
                    raise RuntimeError("Scripted client exhausted")
                return _async_llm_stream(self.parent._script.pop(0))

        class _Chat:
            def __init__(self, parent: _ScriptedChatClient) -> None:
                self.completions = _Completions(parent)

        self.chat = _Chat(self)


class _Registry:
    def __init__(self) -> None:
        self.executed: list[dict[str, Any]] = []

    def deferred_tools(self):
        return []

    def build_prompt_text(self, _enabled, **_kwargs):
        return "- `web_search` - Search the web"

    def build_openai_schemas(self, _enabled):
        return [
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "Search",
                    "parameters": {
                        "type": "object",
                        "properties": {"query": {"type": "string"}},
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "ask_user",
                    "description": "Ask the user",
                    "parameters": {
                        "type": "object",
                        "properties": {"questions": {"type": "array"}},
                        "required": ["questions"],
                    },
                },
            },
        ]

    async def execute(self, name: str, **kwargs):
        self.executed.append({"name": name, "kwargs": kwargs})
        return ToolResult(
            content="tool answer",
            sources=[{"tool": name}],
            metadata={"tool": name},
            success=True,
        )


@pytest.fixture(autouse=True)
def _fake_llm_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "deeptutor.agents.chat.agentic_pipeline.get_llm_config",
        lambda: SimpleNamespace(
            binding="openai",
            model="gpt-test",
            api_key="k",
            base_url="u",
            api_version=None,
            extra_headers={},
            reasoning_effort=None,
        ),
    )


async def _run(pipeline: AgenticChatPipeline, context: UnifiedContext):
    bus = StreamBus()
    events, consumer = await _collect_bus_events(bus)
    await pipeline.run(context, bus)
    await asyncio.sleep(0)
    await bus.close()
    await consumer
    return events


def _contents(events: list[StreamEvent]) -> list[str]:
    return [e.content for e in events if e.type == StreamEventType.CONTENT]


def _call_roles(events: list[StreamEvent]) -> list[str]:
    """Ordered list of per-round call_role markers ('narration' | 'finish')."""
    return [
        str(e.metadata.get("call_role"))
        for e in events
        if e.type == StreamEventType.PROGRESS
        and e.metadata.get("call_state") == "complete"
        and "call_role" in e.metadata
    ]


def _result(events: list[StreamEvent]) -> StreamEvent:
    return [e for e in events if e.type == StreamEventType.RESULT][-1]


class TestInlineThinkFilter:
    @staticmethod
    def _run(chunks: list[str]) -> list[tuple[str, str]]:
        f = InlineThinkFilter()
        out: list[tuple[str, str]] = []
        for c in chunks:
            out.extend(f.feed(c))
        out.extend(f.flush())
        return out

    @staticmethod
    def _join(segments: list[tuple[str, str]], kind: str) -> str:
        return "".join(text for k, text in segments if k == kind)

    def test_plain_content_passes_through(self) -> None:
        segs = self._run(["hello ", "world"])
        assert self._join(segs, "content") == "hello world"
        assert self._join(segs, "thinking") == ""

    def test_think_block_split_to_thinking(self) -> None:
        segs = self._run(["<think>plan</think>answer"])
        assert self._join(segs, "thinking") == "plan"
        assert self._join(segs, "content") == "answer"

    def test_tag_split_across_chunks(self) -> None:
        segs = self._run(["before<thi", "nk>inner</th", "ink>after"])
        assert self._join(segs, "content") == "beforeafter"
        assert self._join(segs, "thinking") == "inner"

    def test_unclosed_think_stays_thinking(self) -> None:
        # Interrupted stream: an opened think block never closes — its text
        # must never surface as content (mirrors clean_thinking_tags).
        segs = self._run(["<think>only reasoning, no answer"])
        assert self._join(segs, "content") == ""
        assert "only reasoning" in self._join(segs, "thinking")

    def test_thinking_variant_tag(self) -> None:
        segs = self._run(["<thinking>x</thinking>y"])
        assert self._join(segs, "thinking") == "x"
        assert self._join(segs, "content") == "y"

    def test_non_think_tags_untouched(self) -> None:
        segs = self._run(["a <b>bold</b> ", "and a < b comparison"])
        assert self._join(segs, "content") == "a <b>bold</b> and a < b comparison"

    def test_multiple_think_blocks(self) -> None:
        segs = self._run(["<think>1</think>mid<think>2</think>end"])
        assert self._join(segs, "content") == "midend"
        assert self._join(segs, "thinking") == "12"


@pytest.mark.asyncio
async def test_inline_think_streams_to_trace_not_bubble(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Providers that inline <think> in the content channel: think text must
    stream as thinking events; only the post-think text is user content."""
    registry = _Registry()
    client = _ScriptedChatClient(
        [
            [
                _llm_chunk(content="<think>let me "),
                _llm_chunk(content="reason</think>"),
                _llm_chunk(content="The answer."),
            ]
        ]
    )
    pipeline = AgenticChatPipeline(language="en")
    pipeline.registry = registry
    monkeypatch.setattr(pipeline, "_compose_enabled_tools", lambda _context: [])
    monkeypatch.setattr(pipeline, "_build_openai_client", lambda: client)

    events = await _run(pipeline, UnifiedContext(session_id="s1", user_message="Hi"))

    assert _contents(events) == ["The answer."]
    thinking = "".join(e.content for e in events if e.type == StreamEventType.THINKING)
    assert "let me reason" in thinking
    result = _result(events)
    assert result.metadata["response"] == "The answer."
    assert result.metadata["completed"] is True


@pytest.mark.asyncio
async def test_empty_finish_gets_one_nudge_then_recovers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A tool-less round that is ALL internal reasoning must not finalize as
    an empty answer: the loop nudges once and the model recovers."""
    registry = _Registry()
    client = _ScriptedChatClient(
        [
            # Round 1: the model "finishes" with nothing but think text.
            [_llm_chunk(content="<think>I wrote a whole script here</think>")],
            # Round 2 (after the nudge): a real answer.
            [_llm_chunk(content="Here is the real answer.")],
        ]
    )
    pipeline = AgenticChatPipeline(language="en")
    pipeline.registry = registry
    monkeypatch.setattr(pipeline, "_compose_enabled_tools", lambda _context: [])
    monkeypatch.setattr(pipeline, "_build_openai_client", lambda: client)

    events = await _run(pipeline, UnifiedContext(session_id="s1", user_message="Make a PDF"))

    assert client.call_count == 2
    # The nudge round keeps the raw think text in-conversation and appends
    # the nudge instruction as the trailing user message.
    second_round = client.calls[1]["messages"]
    assert second_round[-1]["role"] == "user"
    assert "internal reasoning" in second_round[-1]["content"]
    assert any(
        m.get("role") == "assistant" and "whole script" in str(m.get("content"))
        for m in second_round
    )
    result = _result(events)
    assert result.metadata["response"] == "Here is the real answer."
    assert result.metadata["completed"] is True


@pytest.mark.asyncio
async def test_finish_first_round_no_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    """A request that needs no exploration: the first round emits no tool
    calls, so it IS the finish — one LLM call, streamed straight to the user."""
    registry = _Registry()
    client = _ScriptedChatClient([[_llm_chunk(content="A direct answer.")]])
    pipeline = AgenticChatPipeline(language="en")
    pipeline.registry = registry
    monkeypatch.setattr(pipeline, "_compose_enabled_tools", lambda _context: [])
    monkeypatch.setattr(pipeline, "_build_openai_client", lambda: client)

    events = await _run(pipeline, UnifiedContext(session_id="s1", user_message="Hello"))

    assert client.call_count == 1
    # The finish round's text streams to the user, not the trace.
    assert _contents(events) == ["A direct answer."]
    assert _call_roles(events) == ["finish"]
    result = _result(events)
    assert result.metadata["engine"] == "agent_loop"
    assert result.metadata["completed"] is True
    assert result.metadata["response"] == "A direct answer."
    assert result.metadata["rounds"] == 1
    assert result.metadata["tool_steps"] == 0


@pytest.mark.asyncio
async def test_chat_ignores_answer_now_context(monkeypatch: pytest.MonkeyPatch) -> None:
    registry = _Registry()
    client = _ScriptedChatClient([[_llm_chunk(content="Normal agent-loop answer.")]])
    pipeline = AgenticChatPipeline(language="en")
    pipeline.registry = registry
    monkeypatch.setattr(pipeline, "_compose_enabled_tools", lambda _context: [])
    monkeypatch.setattr(pipeline, "_build_openai_client", lambda: client)

    events = await _run(
        pipeline,
        UnifiedContext(
            session_id="s1",
            user_message="Hello",
            config_overrides={
                "answer_now_context": {
                    "original_user_message": "Hello",
                    "partial_response": "old partial answer",
                    "events": [],
                },
            },
        ),
    )

    result = _result(events)
    assert result.metadata["engine"] == "agent_loop"
    assert "answer_now" not in result.metadata
    assert result.metadata["response"] == "Normal agent-loop answer."


@pytest.mark.asyncio
async def test_tool_round_then_finish(monkeypatch: pytest.MonkeyPatch) -> None:
    """A tool round (narration text + a tool call) is followed by a tool-less
    finish round whose text is the answer — two LLM calls, no respond pass."""
    registry = _Registry()
    client = _ScriptedChatClient(
        [
            # Round 1: preamble (narration) text + a tool call.
            [
                _llm_chunk(content="Searching."),
                _llm_chunk(
                    tool_calls=[
                        {
                            "id": "call-1",
                            "name": "web_search",
                            "arguments": json.dumps({"query": "Fourier transform"}),
                        }
                    ]
                ),
            ],
            # Round 2: the model sees the tool result in-protocol and finishes
            # by replying without tool calls.
            [_llm_chunk(content="Found what was needed.")],
        ]
    )
    pipeline = AgenticChatPipeline(language="en")
    pipeline.registry = registry
    monkeypatch.setattr(pipeline, "_compose_enabled_tools", lambda _context: ["web_search"])
    monkeypatch.setattr(pipeline, "_build_openai_client", lambda: client)

    events = await _run(
        pipeline,
        UnifiedContext(
            session_id="s1", user_message="Look up Fourier", enabled_tools=["web_search"]
        ),
    )

    assert client.call_count == 2
    assert registry.executed[0]["name"] == "web_search"
    assert registry.executed[0]["kwargs"]["query"] == "Fourier transform"
    # Both rounds' text streams to the user; the round roles distinguish them.
    assert _contents(events) == ["Searching.", "Found what was needed."]
    assert _call_roles(events) == ["narration", "finish"]
    # Round 2 sees the tool exchange in-protocol: the assistant tool_calls
    # message (with its preamble text) followed by the role=tool result.
    second_round = client.calls[1]["messages"]
    assistant_tc = [m for m in second_round if m.get("role") == "assistant" and m.get("tool_calls")]
    assert assistant_tc and assistant_tc[0]["tool_calls"][0]["function"]["name"] == "web_search"
    assert assistant_tc[0]["content"] == "Searching."
    tool_msgs = [m for m in second_round if m.get("role") == "tool"]
    assert tool_msgs and "tool answer" in tool_msgs[0]["content"]
    result = _result(events)
    assert result.metadata["tool_steps"] == 1
    assert result.metadata["rounds"] == 2
    # Only the finish round's text is the persisted answer.
    assert result.metadata["response"] == "Found what was needed."


@pytest.mark.asyncio
async def test_ask_user_available_every_round(monkeypatch: pytest.MonkeyPatch) -> None:
    """The single loop offers the full tool belt — including ask_user — on
    every round; there is no respond stage that narrows tools to ask_user."""
    registry = _Registry()
    client = _ScriptedChatClient([[_llm_chunk(content="Final answer.")]])
    pipeline = AgenticChatPipeline(language="en")
    pipeline.registry = registry
    monkeypatch.setattr(
        pipeline, "_compose_enabled_tools", lambda _context: ["web_search", "ask_user"]
    )
    monkeypatch.setattr(pipeline, "_build_openai_client", lambda: client)

    await _run(
        pipeline,
        UnifiedContext(
            session_id="s1",
            user_message="Quick question",
            enabled_tools=["web_search", "ask_user"],
        ),
    )

    loop_tools = {t["function"]["name"] for t in client.calls[0]["tools"]}
    assert loop_tools == {"web_search", "ask_user"}


@pytest.mark.asyncio
async def test_ask_user_pause_resumes_and_streams_interleaved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _PausingRegistry(_Registry):
        async def execute(self, name: str, **kwargs):
            self.executed.append({"name": name, "kwargs": kwargs})
            if name == "ask_user":
                return ToolResult(
                    content="Asked the user.",
                    success=True,
                    pause_for_user={"questions": [{"id": "q1", "prompt": "Which topic?"}]},
                )
            return await super().execute(name, **kwargs)

    registry = _PausingRegistry()
    client = _ScriptedChatClient(
        [
            # Round 1: a clarification (narration text + ask_user tool call).
            [
                _llm_chunk(content="Let me check one thing."),
                _llm_chunk(
                    tool_calls=[
                        {
                            "id": "call-1",
                            "name": "ask_user",
                            "arguments": json.dumps(
                                {"questions": [{"id": "q1", "prompt": "Which topic?"}]}
                            ),
                        }
                    ]
                ),
            ],
            # Round 2 finishes after the user's reply resumes the loop.
            [_llm_chunk(content="The answer.")],
        ]
    )
    pipeline = AgenticChatPipeline(language="en")
    pipeline.registry = registry
    monkeypatch.setattr(pipeline, "_compose_enabled_tools", lambda _context: ["ask_user"])
    monkeypatch.setattr(pipeline, "_build_openai_client", lambda: client)

    async def _waiter():
        return {"text": "Topic A"}

    events = await _run(
        pipeline,
        UnifiedContext(
            session_id="s1",
            user_message="Quick question",
            enabled_tools=["ask_user"],
            metadata={"wait_for_user_reply": _waiter},
        ),
    )

    assert client.call_count == 2
    assert _contents(events) == ["Let me check one thing.", "The answer."]
    assert _call_roles(events) == ["narration", "finish"]
    # The reply was substituted into the role=tool message in-protocol.
    final_round = client.calls[-1]["messages"]
    tool_msgs = [m for m in final_round if m.get("role") == "tool"]
    assert tool_msgs and "Topic A" in tool_msgs[-1]["content"]
    result = _result(events)
    # The persisted answer is the finish round's text.
    assert result.metadata["response"] == "The answer."
    assert result.metadata["completed"] is True


@pytest.mark.asyncio
async def test_unresolved_ask_user_halts_turn(monkeypatch: pytest.MonkeyPatch) -> None:
    class _PausingRegistry(_Registry):
        async def execute(self, name: str, **kwargs):
            self.executed.append({"name": name, "kwargs": kwargs})
            return ToolResult(
                content="Asked the user.",
                success=True,
                pause_for_user={"questions": [{"id": "q1", "prompt": "Which topic?"}]},
            )

    registry = _PausingRegistry()
    client = _ScriptedChatClient(
        [
            [
                _llm_chunk(
                    tool_calls=[
                        {
                            "id": "call-1",
                            "name": "ask_user",
                            "arguments": json.dumps({"questions": []}),
                        }
                    ]
                ),
            ],
            # No further scripted responses: with no wait_for_user_reply waiter
            # the loop must halt here instead of producing another answer.
        ]
    )
    pipeline = AgenticChatPipeline(language="en")
    pipeline.registry = registry
    monkeypatch.setattr(pipeline, "_compose_enabled_tools", lambda _context: ["ask_user"])
    monkeypatch.setattr(pipeline, "_build_openai_client", lambda: client)

    events = await _run(
        pipeline,
        UnifiedContext(session_id="s1", user_message="Help me study", enabled_tools=["ask_user"]),
    )

    assert client.call_count == 1
    assert _contents(events) == ["Which topic?"]
    result = _result(events)
    assert result.metadata["completed"] is False


@pytest.mark.asyncio
async def test_round_budget_forces_tool_less_finish(monkeypatch: pytest.MonkeyPatch) -> None:
    registry = _Registry()
    client = _ScriptedChatClient(
        [
            [
                _llm_chunk(
                    tool_calls=[
                        {
                            "id": "call-1",
                            "name": "web_search",
                            "arguments": json.dumps({"query": "step one"}),
                        }
                    ]
                ),
            ],
            [_llm_chunk(content="Best effort answer.")],
        ]
    )
    pipeline = AgenticChatPipeline(language="en")
    pipeline.registry = registry
    pipeline._max_rounds = 1
    monkeypatch.setattr(pipeline, "_compose_enabled_tools", lambda _context: ["web_search"])
    monkeypatch.setattr(pipeline, "_build_openai_client", lambda: client)

    events = await _run(
        pipeline,
        UnifiedContext(session_id="s1", user_message="Research this", enabled_tools=["web_search"]),
    )

    assert client.call_count == 2
    # The forced finish round disables tools and tells the model to answer now.
    assert "tools" not in client.calls[-1]
    forced_instruction = client.calls[-1]["messages"][-1]["content"]
    assert "round budget ran out" in forced_instruction
    result = _result(events)
    assert result.metadata["response"] == "Best effort answer."
    assert result.metadata["completed"] is True


def test_compose_enabled_tools_injects_rag_when_kb_selected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "deeptutor.services.memory.get_memory_store",
        lambda: SimpleNamespace(read_raw=lambda *_args, **_kwargs: ""),
    )
    monkeypatch.setattr(
        "deeptutor.services.notebook.get_notebook_manager",
        lambda: SimpleNamespace(list_notebooks=lambda: []),
    )
    pipeline = AgenticChatPipeline.__new__(AgenticChatPipeline)
    pipeline._deferred_loader = None
    pipeline._exec_enabled = False
    pipeline.registry = SimpleNamespace(
        get_enabled=lambda selected: [SimpleNamespace(name=n) for n in selected]
    )
    context = UnifiedContext(
        user_message="hi",
        enabled_tools=["web_search"],
        knowledge_bases=["kb-a"],
    )
    assert "rag" in pipeline._compose_enabled_tools(context)
    assert "web_search" in pipeline._compose_enabled_tools(context)


def test_augment_tool_kwargs_injects_geogebra_image() -> None:
    pipeline = AgenticChatPipeline.__new__(AgenticChatPipeline)
    pipeline.language = "zh"
    context = UnifiedContext(
        user_message="solve this triangle",
        attachments=[
            Attachment(
                type="image",
                base64="REAL_IMG_BYTES",
                filename="problem.png",
                mime_type="image/png",
            ),
        ],
        language="zh",
    )

    augmented = pipeline._augment_tool_kwargs(
        "geogebra_analysis",
        {"image_base64": "HALLUCINATED"},
        context,
    )

    assert augmented["image_base64"] == "data:image/png;base64,REAL_IMG_BYTES"
    assert augmented["language"] == "zh"


def test_build_llm_tool_schemas_kb_name_enum_matches_attached() -> None:
    pipeline = AgenticChatPipeline.__new__(AgenticChatPipeline)
    pipeline.registry = _Registry()

    schemas = pipeline._build_llm_tool_schemas(
        ["web_search"],
        UnifiedContext(knowledge_bases=["kb-a", "kb-b"]),
    )

    assert schemas[0]["function"]["parameters"]["additionalProperties"] is False
