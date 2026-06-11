"use client";

/**
 * Soul source selector for the creation wizard: start from the library, clone
 * one of the chat personas, or write a custom soul. Always shows a live
 * preview/editor — the chosen text IS the partner's SOUL.md. A custom soul
 * can be saved back into the shared library for future partners.
 */

import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { BookHeart, Check, Loader2, Save, Sparkles, UserRound } from "lucide-react";
import {
  createSoulTemplate,
  getSoulSources,
  type SoulSources,
  type SoulSpec,
} from "@/lib/partners-api";

type SourceTab = "library" | "persona" | "custom";

function slugifySoulId(name: string): string {
  return (
    name
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9一-鿿]+/g, "-")
      .replace(/^-+|-+$/g, "") || `soul-${Date.now().toString(36)}`
  );
}

export default function SoulPicker({
  value,
  onChange,
}: {
  value: SoulSpec;
  onChange: (next: SoulSpec) => void;
}) {
  const { t } = useTranslation();
  const [sources, setSources] = useState<SoulSources | null>(null);
  const [tab, setTab] = useState<SourceTab>(
    value.source === "persona" ? "persona" : value.source === "custom" ? "custom" : "library",
  );
  const [saveName, setSaveName] = useState("");
  const [saving, setSaving] = useState(false);
  const [savedId, setSavedId] = useState("");
  const [saveError, setSaveError] = useState("");

  useEffect(() => {
    void (async () => {
      try {
        setSources(await getSoulSources());
      } catch {
        setSources({ library: [], personas: [] });
      }
    })();
  }, []);

  const tabs: { key: SourceTab; label: string; icon: typeof Sparkles }[] = [
    { key: "library", label: t("Soul library"), icon: BookHeart },
    { key: "persona", label: t("Clone a persona"), icon: UserRound },
    { key: "custom", label: t("Write your own"), icon: Sparkles },
  ];

  const selectLibrary = (id: string) => {
    const entry = sources?.library.find((s) => s.id === id);
    onChange({ source: "library", id, content: entry?.content });
  };

  const selectPersona = (name: string) => {
    onChange({ source: "persona", id: name });
  };

  const saveToLibrary = async () => {
    const content = (value.content ?? "").trim();
    const name = saveName.trim();
    if (!content || !name) return;
    setSaving(true);
    setSaveError("");
    try {
      const entry = await createSoulTemplate(slugifySoulId(name), name, content);
      setSavedId(entry.id);
      setSources(await getSoulSources());
      // Keep the wizard pointed at the (identical) library entry.
      onChange({ source: "library", id: entry.id, content });
      setTab("library");
      setSaveName("");
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : t("Save failed"));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex w-fit gap-1 rounded-lg bg-[var(--muted)] p-0.5">
        {tabs.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            type="button"
            onClick={() => {
              setTab(key);
              if (key === "custom")
                onChange({ source: "custom", content: value.content ?? "" });
            }}
            className={`inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-[12px] transition-colors ${
              tab === key
                ? "bg-[var(--background)] font-medium text-[var(--foreground)] shadow-sm"
                : "text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
            }`}
          >
            <Icon className="h-3.5 w-3.5" />
            {label}
          </button>
        ))}
      </div>

      {tab === "library" && (
        <div className="flex flex-wrap gap-1.5">
          {(sources?.library ?? []).map((soul) => (
            <button
              key={soul.id}
              type="button"
              onClick={() => selectLibrary(soul.id)}
              className={`rounded-full border px-3 py-1 text-[12px] transition-colors ${
                value.source === "library" && value.id === soul.id
                  ? "border-[var(--primary)] bg-[var(--secondary)] font-medium text-[var(--primary)]"
                  : "border-[var(--border)] text-[var(--muted-foreground)] hover:border-[var(--ring)] hover:text-[var(--foreground)]"
              }`}
            >
              {soul.name}
              {savedId === soul.id && (
                <Check className="ml-1 inline h-3 w-3 text-[var(--primary)]" />
              )}
            </button>
          ))}
          {sources && sources.library.length === 0 && (
            <p className="text-[12px] text-[var(--muted-foreground)]">
              {t("No soul templates yet.")}
            </p>
          )}
        </div>
      )}

      {tab === "persona" && (
        <div className="flex flex-wrap gap-1.5">
          {(sources?.personas ?? []).map((persona) => (
            <button
              key={persona.name}
              type="button"
              onClick={() => selectPersona(persona.name)}
              title={persona.description}
              className={`rounded-full border px-3 py-1 text-[12px] transition-colors ${
                value.source === "persona" && value.id === persona.name
                  ? "border-[var(--primary)] bg-[var(--secondary)] font-medium text-[var(--primary)]"
                  : "border-[var(--border)] text-[var(--muted-foreground)] hover:border-[var(--ring)] hover:text-[var(--foreground)]"
              }`}
            >
              {persona.name}
            </button>
          ))}
          {sources && sources.personas.length === 0 && (
            <p className="text-[12px] text-[var(--muted-foreground)]">
              {t("No personas in your chat workspace yet.")}
            </p>
          )}
          {value.source === "persona" && value.id && (
            <p className="w-full text-[11px] text-[var(--muted-foreground)]">
              {t("The persona's markdown is copied into the partner — later edits to the persona won't affect it.")}
            </p>
          )}
        </div>
      )}

      {(tab === "custom" ||
        (tab === "library" && value.source === "library" && value.content)) && (
        <textarea
          value={value.content ?? ""}
          onChange={(e) => onChange({ source: "custom", content: e.target.value })}
          rows={10}
          placeholder={t("# Soul\nDescribe who this partner is, how it speaks, what it values…")}
          className="w-full rounded-xl border border-[var(--border)] bg-transparent px-3.5 py-3 font-mono text-[12.5px] leading-relaxed outline-none focus:border-[var(--ring)]"
        />
      )}

      {tab === "custom" && (value.content ?? "").trim() && (
        <div className="flex flex-wrap items-center gap-2">
          <input
            value={saveName}
            onChange={(e) => setSaveName(e.target.value)}
            placeholder={t("Template name")}
            className="w-44 rounded-lg border border-[var(--border)] bg-transparent px-3 py-1.5 text-[12px] outline-none focus:border-[var(--ring)]"
          />
          <button
            type="button"
            onClick={() => void saveToLibrary()}
            disabled={saving || !saveName.trim()}
            className="inline-flex items-center gap-1.5 rounded-lg border border-[var(--border)] px-3 py-1.5 text-[12px] font-medium text-[var(--foreground)] hover:border-[var(--ring)] disabled:opacity-40"
          >
            {saving ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Save className="h-3.5 w-3.5" />
            )}
            {t("Save to soul library")}
          </button>
          {saveError && (
            <span className="text-[11.5px] text-[var(--destructive)]">{saveError}</span>
          )}
        </div>
      )}
    </div>
  );
}
