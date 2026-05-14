"use client";

import { useParams } from "next/navigation";
import { useEffect, useState, useRef, useCallback } from "react";
import { Lightbulb, Loader2 } from "lucide-react";
import { useTranslation } from "react-i18next";
import { apiUrl, wsUrl } from "@/lib/api";
import ModuleTree from "@/components/learning/ModuleTree";

interface StreamEvent {
  type: string;
  source: string;
  stage: string;
  content: string;
  metadata: Record<string, unknown>;
}

interface StageProgress {
  stage: string;
  status: "pending" | "active" | "completed" | "error";
  content: string;
}

const STAGE_LABELS: Record<string, string> = {
  diagnostic_phase1: "Diagnostic Phase 1",
  diagnostic_phase2: "Diagnostic Phase 2",
  metacognitive_intro: "Metacognitive Intro",
  plan: "Study Plan",
  pretest: "Pretest",
  explain: "Explain",
  feynman_check: "Feynman Check",
  practice: "Practice",
  error_diagnosis: "Error Diagnosis",
  module_test: "Module Test",
  review: "Review",
  completed: "Completed",
};

export default function LearningBookPage() {
  const params = useParams<{ bookId: string }>();
  const { t } = useTranslation();
  const [stages, setStages] = useState<StageProgress[]>([]);
  const stagesRef = useRef<StageProgress[]>([]);
  const [currentStage, setCurrentStage] = useState<string>("");
  const currentStageRef = useRef<string>("");
  const [connecting, setConnecting] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const errorRef = useRef<boolean>(false);
  const activeTurnRetryRef = useRef<boolean>(false);
  const [toast, setToast] = useState("");
  const wsRef = useRef<WebSocket | null>(null);

  interface ModuleData {
    id: string;
    name: string;
    order: number;
    knowledge_points: { id: string; name: string; type: string }[];
    pass_threshold: number;
  }
  const [modules, setModules] = useState<ModuleData[]>([]);
  const [masteryLevels, setMasteryLevels] = useState<Record<string, number>>({});
  const [currentModuleId, setCurrentModuleId] = useState<string>("");

  const fetchProgress = useCallback(() => {
    fetch(apiUrl(`/api/v1/learning/progress/${params.bookId}`), { credentials: "include" })
      .then((r) => r.json())
      .then((data) => {
        setModules(data.modules ?? []);
        setMasteryLevels(data.mastery_levels ?? {});
        setCurrentModuleId(data.current_module_id ?? "");
      })
      .catch(() => {});
  }, [params.bookId]);

  const fetchProgressRef = useRef(fetchProgress);
  fetchProgressRef.current = fetchProgress;

  const connect = useCallback(() => {
    const ws = new WebSocket(wsUrl("/api/v1/ws"));
    wsRef.current = ws;

    ws.onopen = () => {
      setConnecting(false);
      setError(null);
      ws.send(JSON.stringify({
        type: "start_turn",
        session_id: params.bookId,
        capability: "guided_learning",
        content: "Start learning",
        book_references: [{ book_id: params.bookId, page_ids: [] }],
        config: {},
      }));
    };

    ws.onmessage = (event) => {
      try {
        const evt: StreamEvent = JSON.parse(event.data);
        handleStreamEvent(evt);
      } catch { /* ignore parse errors */ }
    };

    ws.onerror = () => setError(t("guidedLearning.connectionError"));
    ws.onclose = () => setConnecting(true);
  }, [params.bookId]);

  const handleStreamEvent = (evt: StreamEvent) => {
    if (evt.type === "stage_start") {
      currentStageRef.current = evt.stage;
      setCurrentStage(evt.stage);
      // Clear recoverable errors on new turn
      if (activeTurnRetryRef.current) {
        setError(null);
        activeTurnRetryRef.current = false;
      }
      setStages(prev => {
        const updated = [...prev];
        const idx = updated.findIndex(s => s.stage === evt.stage);
        if (idx >= 0) {
          updated[idx] = { ...updated[idx], status: "active" };
        } else {
          updated.push({ stage: evt.stage, status: "active", content: "" });
        }
        stagesRef.current = updated;
        return updated;
      });
    } else if (evt.type === "content") {
      setStages(prev => prev.map(s =>
        s.stage === currentStageRef.current ? { ...s, content: s.content + evt.content } : s
      ));
    } else if (evt.type === "result" || evt.type === "stage_end") {
      setStages(prev => {
        const updated = prev.map(s =>
          s.stage === currentStageRef.current ? { ...s, status: "completed" as const } : s
        );
        stagesRef.current = updated;
        return updated;
      });
      const endedStage = currentStageRef.current;
      currentStageRef.current = "";
      setCurrentStage("");
      if (["plan", "diagnostic_phase1", "diagnostic_phase2", "review", "module_test"].includes(endedStage)) {
        fetchProgressRef.current();
      }
    } else if (evt.type === "done") {
      // Auto-advance after turn completes, skip if terminal completed stage exists or any error occurred
      const hasCompletedTerminal = stagesRef.current.some(s => s.stage === "completed" && s.status === "completed");
      const hasError = errorRef.current || stagesRef.current.some(s => s.status === "error" || s.stage === "error");
      if (!hasCompletedTerminal && !hasError && wsRef.current?.readyState === WebSocket.OPEN) {
        const sendContinue = (retriesLeft: number) => {
          if (wsRef.current?.readyState !== WebSocket.OPEN) return;
          errorRef.current = false;
          activeTurnRetryRef.current = false;
          wsRef.current.send(JSON.stringify({
            type: "start_turn",
            session_id: params.bookId,
            capability: "guided_learning",
            content: "Continue",
            book_references: [{ book_id: params.bookId, page_ids: [] }],
            config: {},
          }));
          // If still active turn after 2s, retry (only for active turn errors)
          if (retriesLeft > 0) {
            setTimeout(() => {
              if (activeTurnRetryRef.current && retriesLeft > 0) {
                sendContinue(retriesLeft - 1);
              }
            }, 2000);
          }
        };
        setTimeout(() => sendContinue(3), 500);
      }
    } else if (evt.type === "error") {
      setError(evt.content);
      errorRef.current = true;
      // Check if this is a recoverable "active turn" error
      if (evt.content?.includes("active turn")) {
        activeTurnRetryRef.current = true;
      }
      setToast(t("guidedLearning.stageFailed"));
      setStages(prev => {
        const updated = prev.map(s =>
          s.stage === currentStageRef.current ? { ...s, status: "error" as const } : s
        );
        stagesRef.current = updated;
        return updated;
      });
    }
  };

  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(""), 3500);
    return () => clearTimeout(timer);
  }, [toast]);

  // Fetch learning progress for module tree
  useEffect(() => {
    fetchProgress();
  }, [fetchProgress]);

  useEffect(() => {
    connect();
    return () => { wsRef.current?.close(); };
  }, [connect]);

  return (
    <div className="flex h-full relative">
      {toast && (
        <div className="fixed top-4 right-4 z-50 rounded-lg bg-red-500/90 px-4 py-2 text-sm text-white shadow-lg">
          {toast}
        </div>
      )}
      {/* Sidebar */}
      <div className="w-64 border-r border-[var(--border)] p-4 overflow-y-auto flex flex-col gap-4">
        {/* Module tree */}
        {modules.length > 0 && (
          <div>
            <h2 className="text-sm font-semibold mb-2">{t("guidedLearning.modules")}</h2>
            <ModuleTree
              modules={modules}
              masteryLevels={masteryLevels}
              currentModuleId={currentModuleId}
              currentStage={currentStage}
            />
          </div>
        )}
        {/* Stage progress */}
        <div>
          <h2 className="text-sm font-semibold mb-3 flex items-center gap-2">
            <Lightbulb className="w-4 h-4 text-[var(--primary)]" />
            {t("guidedLearning.stages")}
          </h2>
        {connecting && <Loader2 className="w-4 h-4 animate-spin text-[var(--muted-foreground)]" />}
        {stages.map((s) => (
          <div key={s.stage} className="flex items-center gap-2 py-1 text-sm">
            <span className={s.status === "completed" ? "text-green-500" : s.status === "error" ? "text-red-500" : "text-[var(--muted-foreground)]"}>
              {s.status === "active" ? <Loader2 className="w-3 h-3 animate-spin" /> :
               s.status === "completed" ? "✓" : s.status === "error" ? "✗" : "○"}
            </span>
            <span className={s.status === "active" ? "text-[var(--foreground)]" : "text-[var(--muted-foreground)]"}>
              {STAGE_LABELS[s.stage] || s.stage}
            </span>
          </div>
        ))}
        </div>
      </div>
      {/* Content area */}
      <div className="flex-1 p-8 overflow-y-auto">
        {error && <div className="text-red-500 mb-4">{error}</div>}
        {(stages.find(s => s.status === "active") || stages.find(s => s.status === "completed" && s.content))?.content ? (
          <div className="prose dark:prose-invert max-w-none whitespace-pre-wrap">
            {(stages.find(s => s.status === "active") || stages.find(s => s.status === "completed" && s.content))?.content}
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-[var(--muted-foreground)]">
            {connecting ? <Loader2 className="w-8 h-8 animate-spin" /> : t("guidedLearning.ready")}
          </div>
        )}
      </div>
    </div>
  );
}
