"use client";

import { Check, Loader2 } from "lucide-react";
import { useTranslation } from "react-i18next";
import { MASTERY_STAGES, type StageProgress } from "@/hooks/useMasteryTurn";

interface StageRoadmapProps {
  stages: StageProgress[];
  currentStage: string;
}

type DisplayStatus = "done" | "active" | "upcoming";

/**
 * The fixed 6-stage journey, decorated with live status. The per-knowledge
 * point loop (explain ↔ feynman_check) repeats internally; the roadmap only
 * presents the canonical sequence so the learner sees the whole path.
 */
export default function StageRoadmap({ stages, currentStage }: StageRoadmapProps) {
  const { t } = useTranslation();

  const statusFor = (stage: string): DisplayStatus => {
    if (stage === currentStage) return "active";
    const seen = stages.find((s) => s.stage === stage);
    if (seen?.status === "completed") return "done";
    return "upcoming";
  };

  return (
    <ol className="space-y-0.5">
      {MASTERY_STAGES.map((stage, i) => {
        const status = statusFor(stage);
        return (
          <li key={stage} className="flex items-center gap-2.5 py-1">
            <span
              className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[11px] font-medium ${
                status === "done"
                  ? "bg-[var(--primary)] text-[var(--primary-foreground)]"
                  : status === "active"
                    ? "bg-[var(--primary)]/15 text-[var(--primary)] ring-1 ring-[var(--primary)]/40"
                    : "bg-[var(--muted)] text-[var(--muted-foreground)]"
              }`}
            >
              {status === "done" ? (
                <Check className="h-3 w-3" strokeWidth={2.5} />
              ) : status === "active" ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                i + 1
              )}
            </span>
            <span
              className={`text-[13px] ${
                status === "active"
                  ? "font-medium text-[var(--foreground)]"
                  : status === "done"
                    ? "text-[var(--foreground)]"
                    : "text-[var(--muted-foreground)]"
              }`}
            >
              {t(`masteryPath.stage.${stage}`)}
            </span>
          </li>
        );
      })}
    </ol>
  );
}
