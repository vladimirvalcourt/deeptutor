"use client";

import { useTranslation } from "react-i18next";
import MarkdownRenderer from "@/components/common/MarkdownRenderer";

/* ------------------------------------------------------------------ */
/*  Quiz payload parsing                                               */
/* ------------------------------------------------------------------ */

type JsonObject = Record<string, unknown>;

export interface QuizQuestion {
  /** Stable id for the question, if the server provided one. */
  questionId?: string;
  /** The full (answer-stripped) question object as sent by the backend. */
  fields: JsonObject;
  /** Multiple-choice options, if present. */
  options: string[];
}

/** One parsed segment of a stage's streamed content. */
export type StageSegment =
  | { kind: "markdown"; text: string }
  | { kind: "quiz"; question: QuizQuestion };

function isJsonObject(value: unknown): value is JsonObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function tryParseJson(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return undefined;
  }
}

function toText(value: unknown): string {
  if (value == null) return "";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  if (Array.isArray(value)) return value.map(toText).join(", ");
  return JSON.stringify(value);
}

function normalizeOptions(raw: unknown): string[] {
  if (!Array.isArray(raw)) return [];
  return raw.map((opt) => {
    if (isJsonObject(opt)) {
      // Common shapes: {label, text} / {key, value} / {id, content}
      const label = opt.label ?? opt.key ?? opt.id;
      const body = opt.text ?? opt.value ?? opt.content ?? opt.option;
      if (label != null && body != null) return `${toText(label)}. ${toText(body)}`;
      return toText(body ?? label ?? opt);
    }
    return toText(opt);
  });
}

function parseQuestionPayload(obj: JsonObject): QuizQuestion {
  const inner = isJsonObject(obj.question) ? obj.question : obj;
  const questionId =
    typeof obj.question_id === "string" ? obj.question_id : undefined;
  return {
    questionId,
    fields: inner,
    options: normalizeOptions(inner.options),
  };
}

/**
 * Split a stage's accumulated content into ordered markdown / quiz segments.
 * Quiz questions arrive as standalone JSON lines ({question, question_id});
 * everything else is plain markdown (which may contain LaTeX).
 */
export function parseStageContent(content: string): StageSegment[] {
  const segments: StageSegment[] = [];
  let markdownBuffer: string[] = [];

  const flush = () => {
    const text = markdownBuffer.join("\n").trim();
    if (text) segments.push({ kind: "markdown", text });
    markdownBuffer = [];
  };

  for (const line of content.split("\n")) {
    const trimmed = line.trim();
    // A quiz line is a self-contained JSON object carrying a question.
    if (trimmed.startsWith("{") && trimmed.endsWith("}")) {
      const parsed = tryParseJson(trimmed);
      if (isJsonObject(parsed) && ("question" in parsed || "question_id" in parsed)) {
        flush();
        segments.push({ kind: "quiz", question: parseQuestionPayload(parsed) });
        continue;
      }
    }
    markdownBuffer.push(line);
  }
  flush();
  return segments;
}

/** The question the answer input should bind to (last one in the stream). */
export function activeQuestion(content: string): QuizQuestion | null {
  const segments = parseStageContent(content);
  for (let i = segments.length - 1; i >= 0; i -= 1) {
    const seg = segments[i];
    if (seg.kind === "quiz") return seg.question;
  }
  return null;
}

/* ------------------------------------------------------------------ */
/*  Rendering                                                          */
/* ------------------------------------------------------------------ */

const HIDDEN_FIELDS = new Set([
  "answer",
  "correct_answer",
  "solution",
  "options",
  "question_id",
  "id",
]);

function QuestionText({ question }: { question: QuizQuestion }) {
  const { fields } = question;
  const prompt = fields.question ?? fields.text ?? fields.prompt ?? fields.stem;
  if (prompt != null) {
    return (
      <MarkdownRenderer
        content={toText(prompt)}
        enableMath
        variant="compact"
      />
    );
  }
  // Fallback: render any descriptive fields we didn't hide.
  const entries = Object.entries(fields).filter(([k]) => !HIDDEN_FIELDS.has(k));
  return (
    <div className="space-y-1">
      {entries.map(([key, value]) => (
        <div key={key} className="text-sm text-[var(--foreground)]">
          <span className="text-[var(--muted-foreground)]">{key}: </span>
          {toText(value)}
        </div>
      ))}
    </div>
  );
}

function QuizCard({ question, index }: { question: QuizQuestion; index: number }) {
  const { t } = useTranslation();
  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-5 shadow-sm">
      <div className="mb-2 flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-[var(--muted-foreground)]">
        <span className="flex h-5 w-5 items-center justify-center rounded-full bg-[var(--primary)]/10 text-[var(--primary)]">
          {index + 1}
        </span>
        <span>{t("masteryPath.question")}</span>
      </div>
      <QuestionText question={question} />
      {question.options.length > 0 && (
        <ul className="mt-3 space-y-1.5">
          {question.options.map((opt, i) => (
            <li
              key={i}
              className="rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)]"
            >
              {opt}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function StageContent({ content }: { content: string }) {
  const segments = parseStageContent(content);
  // Precompute the running quiz number per segment so render stays pure
  // (no mutable counter reassigned inside the JSX map).
  const quizNumbers = segments.map(
    (seg, i) =>
      seg.kind === "quiz"
        ? segments.slice(0, i).filter((s) => s.kind === "quiz").length
        : -1,
  );
  return (
    <div className="space-y-4">
      {segments.map((seg, i) => {
        if (seg.kind === "markdown") {
          return (
            <MarkdownRenderer
              key={i}
              content={seg.text}
              enableMath
              enableCode
              enableMermaid
            />
          );
        }
        return (
          <QuizCard key={i} question={seg.question} index={quizNumbers[i]} />
        );
      })}
    </div>
  );
}
