"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Archive, Clock3, MessageSquareText, RefreshCw } from "lucide-react";
import { useTranslation } from "react-i18next";
import {
  getPartnerHistory,
  getPartnerSessions,
  type PartnerSessionInfo,
} from "@/lib/partners-api";

interface HistoryMessage {
  role: string;
  content: string;
  timestamp?: string;
  channel?: string;
}

function formatTime(value?: string) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export default function PartnerArchives({
  partnerId,
  onToast,
}: {
  partnerId: string;
  onToast: (message: string) => void;
}) {
  const { t } = useTranslation();
  const [sessions, setSessions] = useState<PartnerSessionInfo[]>([]);
  const [selectedKey, setSelectedKey] = useState("");
  const [messages, setMessages] = useState<HistoryMessage[]>([]);
  const [loadingSessions, setLoadingSessions] = useState(true);
  const [loadingMessages, setLoadingMessages] = useState(false);

  const selected = useMemo(
    () => sessions.find((session) => session.session_key === selectedKey) ?? null,
    [sessions, selectedKey],
  );

  const loadSessions = useCallback(async () => {
    setLoadingSessions(true);
    try {
      const next = await getPartnerSessions(partnerId);
      setSessions(next);
      setSelectedKey((current) => {
        if (current && next.some((session) => session.session_key === current)) {
          return current;
        }
        return next[0]?.session_key ?? "";
      });
    } catch (e) {
      onToast(e instanceof Error ? e.message : t("Load failed"));
    } finally {
      setLoadingSessions(false);
    }
  }, [partnerId, onToast, t]);

  useEffect(() => {
    void loadSessions();
  }, [loadSessions]);

  useEffect(() => {
    if (!selectedKey) {
      setMessages([]);
      return;
    }
    let cancelled = false;
    setLoadingMessages(true);
    void getPartnerHistory(partnerId, { sessionKey: selectedKey, limit: 200 })
      .then((history) => {
        if (!cancelled) setMessages(history);
      })
      .catch((e) => {
        if (!cancelled) {
          setMessages([]);
          onToast(e instanceof Error ? e.message : t("Load failed"));
        }
      })
      .finally(() => {
        if (!cancelled) setLoadingMessages(false);
      });
    return () => {
      cancelled = true;
    };
  }, [partnerId, selectedKey, onToast, t]);

  return (
    <div className="grid h-full min-h-0 grid-cols-1 gap-4 lg:grid-cols-[280px_minmax(0,1fr)]">
      <div className="min-h-0 border-r border-[var(--border)] pr-4 lg:overflow-y-auto">
        <div className="mb-3 flex items-center justify-between gap-2">
          <div>
            <h2 className="text-[13px] font-medium text-[var(--foreground)]">
              {t("Conversations")}
            </h2>
            <p className="text-[11.5px] text-[var(--muted-foreground)]">
              {sessions.length
                ? t("{{count}} session(s)", { count: sessions.length })
                : t("No sessions")}
            </p>
          </div>
          <button
            type="button"
            onClick={() => void loadSessions()}
            disabled={loadingSessions}
            title={t("Refresh")}
            className="inline-flex h-7 w-7 items-center justify-center rounded-md text-[var(--muted-foreground)] hover:bg-[var(--muted)] hover:text-[var(--foreground)] disabled:opacity-40"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loadingSessions ? "animate-spin" : ""}`} />
          </button>
        </div>

        <div className="space-y-2">
          {sessions.map((session) => (
            <button
              key={session.session_key}
              type="button"
              onClick={() => setSelectedKey(session.session_key)}
              className={`w-full rounded-lg border px-3 py-2 text-left transition-colors ${
                selectedKey === session.session_key
                  ? "border-[var(--ring)] bg-[var(--muted)]"
                  : "border-[var(--border)] hover:border-[var(--ring)]"
              }`}
            >
              <div className="flex items-center gap-2">
                {session.archived ? (
                  <Archive className="h-3.5 w-3.5 text-[var(--muted-foreground)]" />
                ) : (
                  <MessageSquareText className="h-3.5 w-3.5 text-[var(--muted-foreground)]" />
                )}
                <span className="min-w-0 flex-1 truncate text-[12.5px] font-medium text-[var(--foreground)]">
                  {session.archived ? t("Archived") : t("Current")}
                </span>
                <span className="text-[11px] text-[var(--muted-foreground)]">
                  {session.message_count}
                </span>
              </div>
              {session.last_message ? (
                <p className="mt-1 line-clamp-2 text-[11.5px] leading-snug text-[var(--muted-foreground)]">
                  {session.last_message}
                </p>
              ) : null}
              <div className="mt-1 flex items-center gap-1 text-[10.5px] text-[var(--muted-foreground)]">
                <Clock3 className="h-3 w-3" />
                {formatTime(session.updated_at)}
              </div>
            </button>
          ))}
          {!loadingSessions && sessions.length === 0 ? (
            <div className="rounded-lg border border-dashed border-[var(--border)] px-3 py-8 text-center text-[12px] text-[var(--muted-foreground)]">
              {t("No conversations yet")}
            </div>
          ) : null}
        </div>
      </div>

      <div className="min-h-0 overflow-y-auto">
        {selected ? (
          <div className="mx-auto max-w-2xl pb-4">
            <div className="sticky top-0 z-10 border-b border-[var(--border)] bg-[var(--background)] py-2">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <h3 className="text-[13px] font-medium text-[var(--foreground)]">
                    {selected.archived ? t("Archived conversation") : t("Current conversation")}
                  </h3>
                  <p className="text-[11.5px] text-[var(--muted-foreground)]">
                    {formatTime(selected.updated_at)}
                  </p>
                </div>
                <span className="rounded-md bg-[var(--muted)] px-2 py-1 text-[11px] text-[var(--muted-foreground)]">
                  {t("{{count}} messages", { count: selected.message_count })}
                </span>
              </div>
            </div>

            <div className="space-y-4 py-4">
              {loadingMessages ? (
                <p className="text-[12px] text-[var(--muted-foreground)]">
                  {t("Loading...")}
                </p>
              ) : (
                messages
                  .filter((message) => message.role === "user" || message.role === "assistant")
                  .map((message, index) => (
                    <div
                      key={`${message.timestamp ?? index}-${index}`}
                      className={message.role === "user" ? "flex justify-end" : "flex justify-start"}
                    >
                      <div
                        className={`max-w-[78%] whitespace-pre-wrap rounded-lg px-3 py-2 text-[13px] leading-relaxed ${
                          message.role === "user"
                            ? "bg-[var(--secondary)] text-[var(--foreground)]"
                            : "border border-[var(--border)] text-[var(--foreground)]"
                        }`}
                      >
                        {message.content}
                      </div>
                    </div>
                  ))
              )}
            </div>
          </div>
        ) : (
          <div className="flex h-full items-center justify-center text-[12px] text-[var(--muted-foreground)]">
            {t("Select a conversation")}
          </div>
        )}
      </div>
    </div>
  );
}
