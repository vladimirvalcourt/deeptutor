"use client";

import { useCallback, useEffect, useReducer, useRef } from "react";
import { wsUrl } from "@/lib/api";

/* ------------------------------------------------------------------ */
/*  Protocol types                                                     */
/* ------------------------------------------------------------------ */

/** A single event coming over the unified turn-runtime WebSocket. */
export interface MasteryStreamEvent {
  type: string;
  source?: string;
  stage?: string;
  content?: string;
  metadata?: Record<string, unknown>;
  turn_id?: string;
  // Some event types carry extra top-level fields:
  status?: string;
  success?: boolean;
  module_id?: string;
}

export const MASTERY_CAPABILITY = "mastery_path";

/** The canonical journey, in display order. Terminal "completed" is separate. */
export const MASTERY_STAGES = [
  "diagnostic",
  "explain",
  "feynman_check",
  "practice",
  "error_diagnosis",
  "review",
] as const;

export type StageStatus = "pending" | "active" | "completed" | "error";

export interface StageProgress {
  stage: string;
  status: StageStatus;
  content: string;
}

/* ------------------------------------------------------------------ */
/*  Reducer — single source of truth for session state                */
/* ------------------------------------------------------------------ */

export interface MasteryState {
  /** Live record of every stage we've seen this session, in arrival order. */
  stages: StageProgress[];
  /** Stage currently streaming content (empty when none is active). */
  currentStage: string;
  /** Socket is connecting / reconnecting. */
  connecting: boolean;
  /** A turn is running and we're waiting on the model (no input yet). */
  busy: boolean;
  /** The model asked the learner for an answer. */
  waitingForInput: boolean;
  /** Prompt to show above the answer input. */
  inputPrompt: string;
  /** Set true once a turn finishes (`done`) and the terminal stage isn't reached. */
  canContinue: boolean;
  /** The terminal "completed" stage was reached. */
  completed: boolean;
  /** One error banner, or null. */
  error: string | null;
  /** Current turn id (needed for user_input). */
  turnId: string;
}

type Action =
  | { type: "CONNECTING" }
  | { type: "OPEN" }
  | { type: "TURN_ID"; turnId: string }
  | { type: "BUSY" }
  | { type: "WAIT_FOR_INPUT"; prompt: string }
  | { type: "STAGE_START"; stage: string }
  | { type: "CONTENT"; content: string }
  | { type: "STAGE_END" }
  | { type: "DONE" }
  | { type: "ERROR"; message: string }
  | { type: "CLEAR_ERROR" }
  | { type: "RESET" };

const initialState: MasteryState = {
  stages: [],
  currentStage: "",
  connecting: true,
  busy: false,
  waitingForInput: false,
  inputPrompt: "",
  canContinue: false,
  completed: false,
  error: null,
  turnId: "",
};

function reducer(state: MasteryState, action: Action): MasteryState {
  switch (action.type) {
    case "CONNECTING":
      return { ...state, connecting: true };
    case "OPEN":
      return { ...state, connecting: false, error: null };
    case "TURN_ID":
      return state.turnId === action.turnId
        ? state
        : { ...state, turnId: action.turnId };
    case "BUSY":
      return { ...state, busy: true, canContinue: false };
    case "WAIT_FOR_INPUT":
      return {
        ...state,
        busy: false,
        waitingForInput: true,
        inputPrompt: action.prompt,
      };
    case "STAGE_START": {
      const idx = state.stages.findIndex((s) => s.stage === action.stage);
      const stages =
        idx >= 0
          ? state.stages.map((s, i) =>
              i === idx ? { ...s, status: "active" as const, content: "" } : s,
            )
          : [
              ...state.stages,
              { stage: action.stage, status: "active" as const, content: "" },
            ];
      return {
        ...state,
        stages,
        currentStage: action.stage,
        busy: false,
        canContinue: false,
        waitingForInput: false,
        error: null,
      };
    }
    case "CONTENT": {
      if (!state.currentStage) return state;
      const stages = state.stages.map((s) =>
        s.stage === state.currentStage
          ? { ...s, content: s.content ? `${s.content}\n${action.content}` : action.content }
          : s,
      );
      return { ...state, stages };
    }
    case "STAGE_END": {
      const ended = state.currentStage;
      if (!ended) return state;
      const stages = state.stages.map((s) =>
        s.stage === ended ? { ...s, status: "completed" as const } : s,
      );
      return {
        ...state,
        stages,
        currentStage: "",
        completed: state.completed || ended === "completed",
      };
    }
    case "DONE": {
      const reachedTerminal =
        state.completed ||
        state.stages.some((s) => s.stage === "completed" && s.status === "completed");
      return {
        ...state,
        busy: false,
        waitingForInput: false,
        completed: reachedTerminal,
        // Surface a Continue affordance only when not terminal and no error.
        canContinue: !reachedTerminal && !state.error,
      };
    }
    case "ERROR": {
      const stages = state.currentStage
        ? state.stages.map((s) =>
            s.stage === state.currentStage ? { ...s, status: "error" as const } : s,
          )
        : state.stages;
      return {
        ...state,
        stages,
        busy: false,
        waitingForInput: false,
        canContinue: false,
        error: action.message,
      };
    }
    case "CLEAR_ERROR":
      return { ...state, error: null };
    case "RESET":
      return { ...initialState, connecting: true };
    default:
      return state;
  }
}

/* ------------------------------------------------------------------ */
/*  Hook                                                               */
/* ------------------------------------------------------------------ */

interface UseMasteryTurnOptions {
  sessionId: string;
  /** Gate connecting until the caller has resolved which module to learn. */
  enabled: boolean;
  /** Called after a stage ends, so the caller can refetch mastery/progress. */
  onStageEnd?: (stage: string) => void;
  /** Called when the server confirms a module switch. */
  onModuleChanged?: (moduleId: string, success: boolean) => void;
}

const MAX_RECONNECT_ATTEMPTS = 5;

export interface UseMasteryTurnResult extends MasteryState {
  /** Force a (re)connect; resets the reconnect backoff counter. */
  reconnect: () => void;
  /** Advance to the next turn after a `done`. */
  continueTurn: () => void;
  /** Submit the learner's answer to the current waiting prompt. */
  submitAnswer: (text: string) => void;
  /** Switch the active module mid-session. */
  changeModule: (moduleId: string) => void;
}

export function useMasteryTurn({
  sessionId,
  enabled,
  onStageEnd,
  onModuleChanged,
}: UseMasteryTurnOptions): UseMasteryTurnResult {
  const [state, dispatch] = useReducer(reducer, initialState);

  const wsRef = useRef<WebSocket | null>(null);
  const turnIdRef = useRef<string>("");
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const intentionalCloseRef = useRef(false);
  const connectRef = useRef<() => void>(() => {});

  // Suppress the "cancelled" error that the server emits right after a
  // module switch cancels the in-flight turn.
  const moduleSwitchRef = useRef(false);

  // Keep callbacks fresh without re-subscribing the socket.
  const onStageEndRef = useRef(onStageEnd);
  const onModuleChangedRef = useRef(onModuleChanged);
  useEffect(() => {
    onStageEndRef.current = onStageEnd;
    onModuleChangedRef.current = onModuleChanged;
  }, [onStageEnd, onModuleChanged]);

  const send = useCallback((payload: Record<string, unknown>) => {
    const ws = wsRef.current;
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(payload));
      return true;
    }
    return false;
  }, []);

  const startTurn = useCallback(
    (content: string) => {
      send({
        type: "start_turn",
        session_id: sessionId,
        capability: MASTERY_CAPABILITY,
        content,
        book_references: [{ book_id: sessionId, page_ids: [] }],
        config: {},
      });
      dispatch({ type: "BUSY" });
    },
    [send, sessionId],
  );

  const handleEvent = useCallback(
    (evt: MasteryStreamEvent) => {
      if (evt.turn_id) {
        turnIdRef.current = evt.turn_id;
        dispatch({ type: "TURN_ID", turnId: evt.turn_id });
      }

      switch (evt.type) {
        case "active_turn_info": {
          if (evt.turn_id && evt.status === "running") {
            turnIdRef.current = evt.turn_id;
            send({ type: "subscribe_turn", turn_id: evt.turn_id });
            dispatch({ type: "BUSY" });
          } else {
            startTurn("Start learning");
          }
          break;
        }
        case "wait_for_input":
          dispatch({
            type: "WAIT_FOR_INPUT",
            prompt: evt.content || "Please enter your answer",
          });
          break;
        case "stage_start":
          moduleSwitchRef.current = false;
          dispatch({ type: "STAGE_START", stage: evt.stage || "" });
          break;
        case "content":
          if (evt.content) dispatch({ type: "CONTENT", content: evt.content });
          break;
        case "result":
        case "stage_end": {
          const ended = evt.stage;
          dispatch({ type: "STAGE_END" });
          if (ended) onStageEndRef.current?.(ended);
          break;
        }
        case "done":
          moduleSwitchRef.current = false;
          dispatch({ type: "DONE" });
          break;
        case "module_changed": {
          moduleSwitchRef.current = true;
          dispatch({ type: "CLEAR_ERROR" });
          if (evt.success !== false && evt.module_id) {
            onModuleChangedRef.current?.(evt.module_id, true);
          } else {
            onModuleChangedRef.current?.(evt.module_id || "", false);
          }
          break;
        }
        case "error": {
          // Ignore the cancellation error emitted right after a module switch.
          if (moduleSwitchRef.current && evt.content?.includes("cancelled")) {
            return;
          }
          dispatch({ type: "ERROR", message: evt.content || "An error occurred" });
          break;
        }
        default:
          break;
      }
    },
    [send, startTurn],
  );

  const handleEventRef = useRef(handleEvent);
  useEffect(() => {
    handleEventRef.current = handleEvent;
  }, [handleEvent]);

  const connect = useCallback(() => {
    if (!enabled) return;
    const existing = wsRef.current;
    if (
      existing?.readyState === WebSocket.OPEN ||
      existing?.readyState === WebSocket.CONNECTING
    ) {
      return;
    }
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    intentionalCloseRef.current = false;
    dispatch({ type: "CONNECTING" });

    const ws = new WebSocket(wsUrl("/api/v1/ws"));
    wsRef.current = ws;

    ws.onopen = () => {
      reconnectAttemptsRef.current = 0;
      dispatch({ type: "OPEN" });
      // Resume an in-flight turn if one exists; otherwise the response
      // (active_turn_info) starts a fresh turn.
      ws.send(JSON.stringify({ type: "check_active_turn", session_id: sessionId }));
    };

    ws.onmessage = (event) => {
      try {
        const evt = JSON.parse(event.data) as MasteryStreamEvent;
        handleEventRef.current(evt);
      } catch {
        // Ignore malformed frames.
      }
    };

    ws.onerror = () => {
      // onclose fires next and drives reconnect; avoid double-handling here.
    };

    ws.onclose = () => {
      if (intentionalCloseRef.current) return;
      if (reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
        const delay = Math.min(
          1000 * 2 ** reconnectAttemptsRef.current,
          10000,
        );
        reconnectAttemptsRef.current += 1;
        dispatch({ type: "CONNECTING" });
        reconnectTimerRef.current = setTimeout(() => connectRef.current(), delay);
      } else {
        dispatch({ type: "ERROR", message: "Connection lost" });
      }
    };
  }, [enabled, sessionId]);

  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  // Connect / teardown on mount + when `enabled`/session changes.
  useEffect(() => {
    if (!enabled) return;
    const timer = setTimeout(() => connect(), 0);
    return () => {
      clearTimeout(timer);
      intentionalCloseRef.current = true;
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [connect, enabled]);

  const reconnect = useCallback(() => {
    reconnectAttemptsRef.current = 0;
    dispatch({ type: "CLEAR_ERROR" });
    connect();
  }, [connect]);

  const continueTurn = useCallback(() => {
    dispatch({ type: "CLEAR_ERROR" });
    startTurn("Continue");
  }, [startTurn]);

  const submitAnswer = useCallback(
    (text: string) => {
      if (!turnIdRef.current) return;
      const ok = send({
        type: "user_input",
        turn_id: turnIdRef.current,
        content: text,
      });
      if (ok) dispatch({ type: "BUSY" });
    },
    [send],
  );

  const changeModule = useCallback(
    (moduleId: string) => {
      moduleSwitchRef.current = true;
      send({ type: "change_module", session_id: sessionId, module_id: moduleId });
    },
    [send, sessionId],
  );

  return {
    ...state,
    reconnect,
    continueTurn,
    submitAnswer,
    changeModule,
  };
}
