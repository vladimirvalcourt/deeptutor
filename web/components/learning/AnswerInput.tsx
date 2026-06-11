"use client";

import { useState } from "react";
import { Loader2, Send } from "lucide-react";
import { useTranslation } from "react-i18next";
import MarkdownRenderer from "@/components/common/MarkdownRenderer";
import type { QuizQuestion } from "@/components/learning/StageContent";

interface AnswerInputProps {
  prompt: string;
  /** When present and it has `options`, render selectable choices. */
  question: QuizQuestion | null;
  submitting: boolean;
  onSubmit: (text: string) => void;
}

export default function AnswerInput({
  prompt,
  question,
  submitting,
  onSubmit,
}: AnswerInputProps) {
  const { t } = useTranslation();
  const [text, setText] = useState("");
  const isChoice = (question?.options.length ?? 0) > 0;

  const submit = (value: string) => {
    const answer = value.trim();
    if (!answer || submitting) return;
    onSubmit(answer);
  };

  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-5 shadow-sm">
      {prompt && (
        <div className="mb-3 text-sm text-[var(--foreground)]">
          <MarkdownRenderer content={prompt} enableMath variant="compact" />
        </div>
      )}

      {isChoice ? (
        <div className="grid gap-2">
          {question!.options.map((opt, i) => {
            // Submit the option's leading label (e.g. "A") when the option is
            // formatted "A. ...", otherwise the full option text.
            const labelMatch = opt.match(/^([A-Za-z0-9]+)[.)]\s/);
            const value = labelMatch ? labelMatch[1] : opt;
            return (
              <button
                key={i}
                type="button"
                disabled={submitting}
                onClick={() => submit(value)}
                className="flex w-full items-center gap-3 rounded-lg border border-[var(--border)] bg-[var(--background)] px-4 py-3 text-left text-sm text-[var(--foreground)] transition-colors hover:border-[var(--primary)]/50 hover:bg-[var(--primary)]/5 disabled:cursor-not-allowed disabled:opacity-60"
              >
                <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-[var(--border)] text-xs text-[var(--muted-foreground)]">
                  {labelMatch ? labelMatch[1] : i + 1}
                </span>
                <span className="flex-1">
                  {labelMatch ? opt.slice(labelMatch[0].length) : opt}
                </span>
              </button>
            );
          })}
        </div>
      ) : (
        <>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if ((e.metaKey || e.ctrlKey) && e.key === "Enter") submit(text);
            }}
            disabled={submitting}
            placeholder={t("masteryPath.inputPlaceholder")}
            className="min-h-[96px] w-full resize-y rounded-lg border border-[var(--border)] bg-[var(--background)] p-3 text-sm text-[var(--foreground)] placeholder:text-[var(--muted-foreground)]/60 focus:border-[var(--primary)]/40 focus:outline-none"
          />
          <div className="mt-3 flex justify-end">
            <button
              type="button"
              onClick={() => submit(text)}
              disabled={submitting || !text.trim()}
              className="flex items-center gap-1.5 rounded-lg bg-[var(--primary)] px-4 py-2 text-sm font-medium text-[var(--primary-foreground)] transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {submitting ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Send className="h-3.5 w-3.5" />
              )}
              {t("masteryPath.submit")}
            </button>
          </div>
        </>
      )}
    </div>
  );
}
