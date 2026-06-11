"use client";

import { useState, useEffect } from "react";
import { ChevronRight, ChevronDown, Circle } from "lucide-react";
import { useTranslation } from "react-i18next";

interface KnowledgePoint {
  id: string;
  name: string;
  type: string;
}

interface Module {
  id: string;
  name: string;
  order: number;
  knowledge_points: KnowledgePoint[];
  pass_threshold: number;
}

interface ModuleTreeProps {
  modules: Module[];
  masteryLevels: Record<string, number>;
  currentModuleId: string;
  onModuleClick?: (moduleId: string) => void;
}

function masteryColor(mastery: number, threshold: number): string {
  if (mastery >= threshold) return "text-green-500";
  if (mastery > 0) return "text-yellow-500";
  return "text-[var(--muted-foreground)]";
}

function ModuleNode({
  module,
  masteryLevels,
  isCurrent,
  onSelect,
}: {
  module: Module;
  masteryLevels: Record<string, number>;
  isCurrent: boolean;
  onSelect?: () => void;
}) {
  const [expanded, setExpanded] = useState(isCurrent);

  useEffect(() => {
    if (!isCurrent) return;
    const timer = setTimeout(() => setExpanded(true), 0);
    return () => clearTimeout(timer);
  }, [isCurrent]);

  const total = module.knowledge_points.length;
  const averageMastery = total > 0
    ? module.knowledge_points.reduce((sum, kp) => sum + (masteryLevels[kp.id] ?? 0), 0) / total
    : 0;
  const masteryPercent = Math.round(averageMastery * 100);

  return (
    <div>
      <button
        onClick={() => {
          if (!isCurrent) onSelect?.();
          setExpanded((prev) => !prev);
        }}
        className={`flex items-center gap-1.5 w-full px-2 py-1.5 text-left text-sm rounded-md transition-colors cursor-pointer ${
          isCurrent
            ? "bg-[var(--primary)]/10 ring-1 ring-[var(--primary)]/30 text-[var(--primary)]"
            : "text-[var(--foreground)] hover:bg-[var(--accent)]"
        }`}
      >
        {expanded ? (
          <ChevronDown className="w-3.5 h-3.5 shrink-0" />
        ) : (
          <ChevronRight className="w-3.5 h-3.5 shrink-0" />
        )}
        <span className="truncate flex-1">{module.name}</span>
        <span className="text-xs text-[var(--muted-foreground)] shrink-0">
          {masteryPercent}%
        </span>
      </button>
      {expanded && (
        <div className="ml-4 border-l border-[var(--border)] pl-2">
          {module.knowledge_points.map((kp) => {
            const mastery = masteryLevels[kp.id] ?? 0;
            return (
              <div
                key={kp.id}
                className="flex items-center gap-1.5 px-2 py-1 text-sm text-[var(--muted-foreground)]"
              >
                <Circle
                  className={`w-2 h-2 shrink-0 fill-current ${masteryColor(mastery, module.pass_threshold)}`}
                />
                <span className="truncate">{kp.name}</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default function ModuleTree({
  modules,
  masteryLevels,
  currentModuleId,
  onModuleClick,
}: ModuleTreeProps) {
  const { t } = useTranslation();
  const sorted = [...modules].sort((a, b) => a.order - b.order);

  if (sorted.length === 0) {
    return (
      <div className="text-sm text-[var(--muted-foreground)] px-2 py-1">
        {t("masteryPath.noModulesLoaded")}
      </div>
    );
  }

  return (
    <div className="space-y-0.5">
      {sorted.map((mod) => (
        <ModuleNode
          key={mod.id}
          module={mod}
          masteryLevels={masteryLevels}
          isCurrent={mod.id === currentModuleId}
          onSelect={() => onModuleClick?.(mod.id)}
        />
      ))}
    </div>
  );
}
