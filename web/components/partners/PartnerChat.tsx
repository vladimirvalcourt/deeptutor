"use client";

/**
 * Web chat with a partner over `WS /api/v1/partners/{id}/ws`.
 *
 * The socket forwards every chat-loop StreamEvent verbatim (`stream_event`
 * frames carry the backend event's `to_dict()`, which IS the frontend
 * `StreamEvent` shape), so this reuses product chat's rendering wholesale:
 * `AssistantActivity` shows the live thinking/tool trace (open while
 * working, collapsed once answered) and the answer text is recomputed with
 * the same narration-demotion rules as chat.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import dynamic from "next/dynamic";
import { wsUrl } from "@/lib/api";
import { getPartnerHistory } from "@/lib/partners-api";
import type { StreamEvent } from "@/lib/unified-ws";
import {
  isNarrationMarker,
  recomputeAnswerContent,
  shouldAppendEventContent,
} from "@/lib/stream";
import { AssistantActivity } from "@/components/chat/home/TracePanels";
import { PartnerComposer } from "@/components/partners/PartnerComposer";
import PartnerAvatar from "@/components/partners/PartnerAvatar";

const AssistantResponse = dynamic(
  () => import("@/components/common/AssistantResponse"),
  { ssr: false },
);

interface ChatMsg {
  role: "user" | "assistant";
  content: string;
  /** Full turn event stream (live turns only; restored history has none). */
  events?: StreamEvent[];
  error?: boolean;
}

export default function PartnerChat({
  partnerId,
  partnerName,
  emoji,
  color,
  avatar,
}: {
  partnerId: string;
  partnerName: string;
  emoji?: string;
  color?: string;
  avatar?: string;
}) {
  const { t } = useTranslation();
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [connected, setConnected] = useState(false);
  // Live turn snapshot for rendering. The authoritative accumulator is a
  // local variable inside the socket effect (event handlers may mutate it
  // freely); every frame publishes a fresh snapshot object here.
  const [draft, setDraft] = useState<{
    events: StreamEvent[];
    content: string;
  } | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const sessionIdRef = useRef<string>("");

  useEffect(() => {
    if (!sessionIdRef.current) {
      sessionIdRef.current = `web-${Math.random().toString(36).slice(2, 10)}`;
    }
  }, []);

  const scrollToBottom = useCallback((behavior: ScrollBehavior = "smooth") => {
    requestAnimationFrame(() => {
      scrollRef.current?.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior,
      });
    });
  }, []);

  // Restore recent history (all sessions merged → the partner's memory feel).
  useEffect(() => {
    let cancelled = false;
    void getPartnerHistory(partnerId, { limit: 60 })
      .then((history) => {
        if (cancelled) return;
        setMessages(
          history
            .filter((m) => m.role === "user" || m.role === "assistant")
            .map((m) => ({
              role: m.role as "user" | "assistant",
              content: m.content,
            })),
        );
        requestAnimationFrame(() => scrollToBottom("instant"));
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [partnerId, scrollToBottom]);

  useEffect(() => {
    const ws = new WebSocket(wsUrl(`/api/v1/partners/${partnerId}/ws`));
    wsRef.current = ws;
    ws.onopen = () => setConnected(true);

    // Authoritative live-turn accumulator. Lives in the effect scope so
    // socket handlers can mutate it cheaply; renders see snapshots only.
    let live: { events: StreamEvent[]; content: string } | null = null;
    const publish = () => {
      setDraft(live ? { events: [...live.events], content: live.content } : null);
    };

    ws.onmessage = (e) => {
      const data = JSON.parse(e.data) as {
        type: string;
        content?: string;
        event?: StreamEvent;
      };
      if (data.type === "stream_event" && data.event) {
        const event = data.event;
        live ??= { events: [], content: "" };
        live.events.push(event);
        if (shouldAppendEventContent(event)) {
          live.content += event.content;
        } else if (isNarrationMarker(event)) {
          // A round resolved as narration — its streamed text belongs to
          // the trace, not the answer. Same demotion rule as product chat.
          live.content = recomputeAnswerContent(live.events);
        }
        publish();
        scrollToBottom();
      } else if (data.type === "content") {
        // Authoritative final text from the runner (covers terminator /
        // ask_user fallbacks the client-side recompute can't know about).
        const finished = live;
        live = null;
        setMessages((msgs) => [
          ...msgs,
          {
            role: "assistant",
            content: data.content || finished?.content || "",
            events: finished?.events.length ? finished.events : undefined,
          },
        ]);
        publish();
        scrollToBottom();
      } else if (data.type === "done") {
        setStreaming(false);
        live = null;
        publish();
      } else if (data.type === "proactive") {
        setMessages((msgs) => [
          ...msgs,
          { role: "assistant", content: data.content ?? "" },
        ]);
        scrollToBottom();
      } else if (data.type === "error") {
        setMessages((msgs) => [
          ...msgs,
          { role: "assistant", content: data.content ?? "Error", error: true },
        ]);
        live = null;
        publish();
        setStreaming(false);
      }
    };

    ws.onclose = () => {
      setConnected(false);
      setStreaming(false);
    };

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [partnerId, scrollToBottom]);

  const handleSend = useCallback(
    (content: string) => {
      if (
        streaming ||
        !wsRef.current ||
        wsRef.current.readyState !== WebSocket.OPEN
      )
        return;
      wsRef.current.send(
        JSON.stringify({ content, session_id: sessionIdRef.current }),
      );
      setMessages((msgs) => [...msgs, { role: "user", content }]);
      setDraft({ events: [], content: "" });
      setStreaming(true);
      scrollToBottom();
    },
    [streaming, scrollToBottom],
  );

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div ref={scrollRef} className="min-h-0 flex-1 overflow-y-auto px-1 py-4">
        {messages.length === 0 && !draft ? (
          <div className="flex h-full flex-col items-center justify-center gap-3 text-center">
            <PartnerAvatar name={partnerName} emoji={emoji} color={color} image={avatar} size={56} />
            <div>
              <p className="text-[15px] font-medium text-[var(--foreground)]">
                {partnerName}
              </p>
              <p className="mt-1 max-w-sm text-[12.5px] text-[var(--muted-foreground)]">
                {t("Say hello — this conversation shares the same memory your partner has on its connected channels.")}
              </p>
            </div>
          </div>
        ) : (
          <div className="mx-auto flex max-w-2xl flex-col gap-5">
            {messages.map((msg, i) =>
              msg.role === "user" ? (
                <div key={i} className="flex justify-end">
                  <div className="max-w-[75%] whitespace-pre-wrap rounded-2xl bg-[var(--secondary)] px-4 py-2.5 text-[14px] leading-relaxed text-[var(--foreground)] shadow-sm">
                    {msg.content}
                  </div>
                </div>
              ) : (
                <div key={i} className="flex items-start gap-2.5">
                  <PartnerAvatar
                    name={partnerName}
                    emoji={emoji}
                    color={color}
                    size={26}
                  />
                  <div className="min-w-0 flex-1">
                    {msg.events && msg.events.length > 0 && (
                      <AssistantActivity
                        events={msg.events}
                        isStreaming={false}
                        content={msg.content}
                        className="mb-1.5"
                        agentName={partnerName}
                        showMark={false}
                        headerClassName="min-h-[26px]"
                      />
                    )}
                    {msg.error ? (
                      <p className="text-[13px] text-[var(--destructive)]">
                        {msg.content}
                      </p>
                    ) : (
                      <AssistantResponse content={msg.content} />
                    )}
                  </div>
                </div>
              ),
            )}

            {draft && (
              <div className="flex items-start gap-2.5">
                <PartnerAvatar
                  name={partnerName}
                  emoji={emoji}
                  color={color}
                  size={26}
                />
                <div className="min-w-0 flex-1">
                  <AssistantActivity
                    events={draft.events}
                    isStreaming
                    content={draft.content}
                    className="mb-1.5"
                    agentName={partnerName}
                    showMark={false}
                    headerClassName="min-h-[26px]"
                  />
                  {draft.content ? (
                    <AssistantResponse content={draft.content} />
                  ) : null}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      <div className="mx-auto w-full max-w-2xl px-1 pb-4">
        {!connected && (
          <p className="mb-1 text-center text-[11px] text-[var(--muted-foreground)]">
            {t("Connecting…")}
          </p>
        )}
        <PartnerComposer onSend={handleSend} disabled={streaming || !connected} />
      </div>
    </div>
  );
}
