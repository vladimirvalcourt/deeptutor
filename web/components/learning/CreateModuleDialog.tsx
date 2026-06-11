"use client";

import { useCallback, useEffect, useState } from "react";
import { FileText, Loader2, Plus, Trash2, X } from "lucide-react";
import { useTranslation } from "react-i18next";

import {
  importFromBook,
  initModules,
  generateModulesFromNotebook,
  type ModuleInit,
} from "@/lib/learning-api";
import { bookApi } from "@/lib/book-api";
import type { Book } from "@/lib/book-types";
import {
  listNotebooks,
  getNotebook,
  type NotebookSummary,
  type NotebookRecordItem,
} from "@/lib/notebook-api";

interface CreateModuleDialogProps {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
}

type Source = "manual" | "book" | "notebook";

interface KpRow {
  name: string;
  type: string;
}

/**
 * Derive a stable, collision-resistant id from a human label without ever
 * surfacing it in the UI. crypto.randomUUID keeps this opaque (the old code
 * leaked `Date.now()`-based ids through a free-text field).
 */
function genId(prefix: string): string {
  const rand =
    typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID().slice(0, 8)
      : Math.random().toString(36).slice(2, 10);
  return `${prefix}_${rand}`;
}

export default function CreateModuleDialog({
  open,
  onClose,
  onCreated,
}: CreateModuleDialogProps) {
  const { t } = useTranslation();
  const [source, setSource] = useState<Source>("manual");

  // ── Manual ──
  const [moduleName, setModuleName] = useState("");
  const [kpRows, setKpRows] = useState<KpRow[]>([{ name: "", type: "concept" }]);

  // ── Book ──
  const [books, setBooks] = useState<Book[]>([]);
  const [selectedBookId, setSelectedBookId] = useState("");
  const [bookChapters, setBookChapters] = useState<
    { title: string; learning_objectives: string[] }[]
  >([]);
  const [loadingBooks, setLoadingBooks] = useState(false);
  const [loadingChapters, setLoadingChapters] = useState(false);

  // ── Notebook ──
  const [notebooks, setNotebooks] = useState<NotebookSummary[]>([]);
  const [selectedNotebook, setSelectedNotebook] = useState("");
  const [notebookRecords, setNotebookRecords] = useState<NotebookRecordItem[]>([]);
  const [selectedRecordIds, setSelectedRecordIds] = useState<Set<string>>(
    new Set(),
  );
  const [loadingNotebooks, setLoadingNotebooks] = useState(false);
  const [loadingRecords, setLoadingRecords] = useState(false);

  // ── Shared ──
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Lazy-load the list for whichever non-manual source is active.
  useEffect(() => {
    if (!open) return;
    if (source === "book" && books.length === 0) {
      setLoadingBooks(true);
      bookApi
        .list()
        .then((data) => setBooks(data.books ?? []))
        .catch(() => setError(t("masteryPath.loadBooksFailed")))
        .finally(() => setLoadingBooks(false));
    }
    if (source === "notebook" && notebooks.length === 0) {
      setLoadingNotebooks(true);
      listNotebooks()
        .then(setNotebooks)
        .catch(() => setError(t("masteryPath.loadNotebooksFailed")))
        .finally(() => setLoadingNotebooks(false));
    }
  }, [open, source, books.length, notebooks.length, t]);

  useEffect(() => {
    if (!selectedBookId) {
      setBookChapters([]);
      return;
    }
    setBookChapters([]);
    setLoadingChapters(true);
    bookApi
      .get(selectedBookId)
      .then((data) => setBookChapters(data.spine?.chapters ?? []))
      .catch(() => setError(t("masteryPath.loadChaptersFailed")))
      .finally(() => setLoadingChapters(false));
  }, [selectedBookId, t]);

  useEffect(() => {
    if (!selectedNotebook) {
      setNotebookRecords([]);
      setSelectedRecordIds(new Set());
      return;
    }
    setLoadingRecords(true);
    getNotebook(selectedNotebook)
      .then((data) => setNotebookRecords(data.records ?? []))
      .catch(() => setError(t("masteryPath.loadRecordsFailed")))
      .finally(() => setLoadingRecords(false));
  }, [selectedNotebook, t]);

  const resetState = useCallback(() => {
    setSource("manual");
    setModuleName("");
    setKpRows([{ name: "", type: "concept" }]);
    setSelectedBookId("");
    setBookChapters([]);
    setSelectedNotebook("");
    setNotebookRecords([]);
    setSelectedRecordIds(new Set());
    setSubmitting(false);
    setError(null);
  }, []);

  const handleClose = useCallback(() => {
    resetState();
    onClose();
  }, [resetState, onClose]);

  // ── Submit (one entry point, branches per source) ──
  const handleSubmit = useCallback(async () => {
    setSubmitting(true);
    setError(null);
    try {
      if (source === "manual") {
        const validKps = kpRows.filter((r) => r.name.trim());
        if (validKps.length === 0) {
          setError(t("masteryPath.moduleNameRequired"));
          return;
        }
        const bookId = genId("manual");
        const moduleId = genId("m");
        const modules: ModuleInit[] = [
          {
            id: moduleId,
            name: moduleName.trim() || t("masteryPath.untitledModule"),
            order: 0,
            pass_threshold: 0.7,
            knowledge_points: validKps.map((kp) => ({
              id: genId("kp"),
              name: kp.name.trim(),
              type: kp.type,
              module_id: moduleId,
            })),
          },
        ];
        await initModules(bookId, modules);
      } else if (source === "book") {
        if (!selectedBookId || bookChapters.length === 0) return;
        const chapters = bookChapters.map((ch) => ({
          title: ch.title,
          knowledge_points: ch.learning_objectives ?? [],
        }));
        await importFromBook(selectedBookId, chapters);
      } else {
        if (!selectedNotebook || selectedRecordIds.size === 0) return;
        const bookId = `nb_${selectedNotebook}`;
        const records = notebookRecords
          .filter((r) => selectedRecordIds.has(r.id))
          .map((r) => ({
            id: r.id,
            type: r.type,
            title: r.title,
            output: r.output,
          }));
        await generateModulesFromNotebook(
          bookId,
          selectedNotebook,
          records.slice(0, 20),
        );
      }
      onCreated();
      handleClose();
    } catch {
      setError(
        source === "manual"
          ? t("masteryPath.createModuleFailed")
          : source === "book"
            ? t("masteryPath.importBookFailed")
            : t("masteryPath.importNotebookFailed"),
      );
    } finally {
      setSubmitting(false);
    }
  }, [
    source,
    kpRows,
    moduleName,
    selectedBookId,
    bookChapters,
    selectedNotebook,
    selectedRecordIds,
    notebookRecords,
    onCreated,
    handleClose,
    t,
  ]);

  if (!open) return null;

  const sources: { key: Source; label: string }[] = [
    { key: "manual", label: t("masteryPath.tabManual") },
    { key: "book", label: t("masteryPath.tabBook") },
    { key: "notebook", label: t("masteryPath.tabNotebook") },
  ];

  const submitDisabled =
    submitting ||
    (source === "book" && (!selectedBookId || bookChapters.length === 0)) ||
    (source === "notebook" && selectedRecordIds.size === 0);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/40 backdrop-blur-sm"
        onClick={handleClose}
      />
      <div className="relative z-10 flex max-h-[80vh] w-full max-w-lg flex-col rounded-xl border border-[var(--border)] bg-[var(--card)] shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-[var(--border)] px-5 py-4">
          <h2 className="text-lg font-semibold text-[var(--foreground)]">
            {t("masteryPath.createModule")}
          </h2>
          <button
            onClick={handleClose}
            className="rounded-md p-1 text-[var(--muted-foreground)] hover:bg-[var(--secondary)] hover:text-[var(--foreground)]"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Source picker */}
        <div className="flex gap-1 border-b border-[var(--border)] px-5 pt-3">
          {sources.map((s) => (
            <button
              key={s.key}
              onClick={() => {
                setSource(s.key);
                setError(null);
              }}
              className={`-mb-px rounded-t-md border-b-2 px-3 py-1.5 text-xs font-medium transition-colors ${
                source === s.key
                  ? "border-[var(--primary)] bg-[var(--secondary)]/40 text-[var(--foreground)]"
                  : "border-transparent text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
              }`}
            >
              {s.label}
            </button>
          ))}
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-5 py-4">
          {error && (
            <div className="mb-3 rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-2 text-xs text-red-500">
              {error}
            </div>
          )}

          {source === "manual" && (
            <div className="space-y-4">
              <div>
                <label className="mb-1 block text-xs font-medium text-[var(--muted-foreground)]">
                  {t("masteryPath.moduleName")}
                </label>
                <input
                  value={moduleName}
                  onChange={(e) => setModuleName(e.target.value)}
                  placeholder={t("masteryPath.moduleNamePlaceholder")}
                  className="w-full rounded-md border border-[var(--border)] bg-[var(--background)] px-3 py-1.5 text-sm text-[var(--foreground)] placeholder:text-[var(--muted-foreground)]/50 focus:border-[var(--primary)]/40 focus:outline-none"
                />
              </div>
              <div>
                <label className="mb-2 block text-xs font-medium text-[var(--muted-foreground)]">
                  {t("masteryPath.knowledgePointsLabel")}
                </label>
                {kpRows.map((row, i) => (
                  <div key={i} className="mb-2 flex items-center gap-2">
                    <input
                      value={row.name}
                      onChange={(e) => {
                        const next = [...kpRows];
                        next[i] = { ...next[i], name: e.target.value };
                        setKpRows(next);
                      }}
                      placeholder={t("masteryPath.kpNamePlaceholder")}
                      className="flex-1 rounded-md border border-[var(--border)] bg-[var(--background)] px-3 py-1.5 text-sm text-[var(--foreground)] placeholder:text-[var(--muted-foreground)]/50 focus:border-[var(--primary)]/40 focus:outline-none"
                    />
                    <select
                      value={row.type}
                      onChange={(e) => {
                        const next = [...kpRows];
                        next[i] = { ...next[i], type: e.target.value };
                        setKpRows(next);
                      }}
                      className="rounded-md border border-[var(--border)] bg-[var(--background)] px-2 py-1.5 text-xs text-[var(--foreground)] focus:outline-none"
                    >
                      <option value="memory">{t("knowledgeType.memory")}</option>
                      <option value="concept">{t("knowledgeType.concept")}</option>
                      <option value="procedure">
                        {t("knowledgeType.procedure")}
                      </option>
                      <option value="design">{t("knowledgeType.design")}</option>
                    </select>
                    {kpRows.length > 1 && (
                      <button
                        onClick={() =>
                          setKpRows(kpRows.filter((_, j) => j !== i))
                        }
                        className="p-1 text-[var(--muted-foreground)] hover:text-red-500"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    )}
                  </div>
                ))}
                <button
                  onClick={() =>
                    setKpRows([...kpRows, { name: "", type: "concept" }])
                  }
                  className="flex items-center gap-1 text-xs text-[var(--primary)] hover:opacity-80"
                >
                  <Plus className="h-3 w-3" />
                  {t("masteryPath.addKp")}
                </button>
              </div>
            </div>
          )}

          {source === "book" && (
            <div className="space-y-3">
              {loadingBooks ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-5 w-5 animate-spin text-[var(--muted-foreground)]" />
                </div>
              ) : books.length === 0 ? (
                <div className="py-8 text-center text-sm text-[var(--muted-foreground)]">
                  {t("masteryPath.noBooks")}
                </div>
              ) : (
                <>
                  <div className="max-h-40 space-y-1 overflow-y-auto">
                    {books.map((book) => (
                      <button
                        key={book.id}
                        onClick={() => setSelectedBookId(book.id)}
                        className={`w-full rounded-lg px-3 py-2 text-left text-sm transition-colors ${
                          selectedBookId === book.id
                            ? "border border-[var(--primary)]/30 bg-[var(--primary)]/10 text-[var(--foreground)]"
                            : "border border-transparent text-[var(--muted-foreground)] hover:bg-[var(--secondary)]/40 hover:text-[var(--foreground)]"
                        }`}
                      >
                        <div className="truncate font-medium">
                          {book.title || book.id}
                        </div>
                        <div className="text-xs opacity-70">
                          {book.chapter_count ?? 0} {t("masteryPath.chapters")} ·{" "}
                          {book.status}
                        </div>
                      </button>
                    ))}
                  </div>
                  {selectedBookId && (
                    <div className="border-t border-[var(--border)] pt-3">
                      {loadingChapters ? (
                        <div className="flex items-center gap-2 text-sm text-[var(--muted-foreground)]">
                          <Loader2 className="h-4 w-4 animate-spin" />
                          {t("masteryPath.loadingChapters")}
                        </div>
                      ) : bookChapters.length === 0 ? (
                        <div className="text-sm text-[var(--muted-foreground)]">
                          {t("masteryPath.noChapters")}
                        </div>
                      ) : (
                        <div>
                          <p className="mb-2 text-xs font-medium text-[var(--muted-foreground)]">
                            {t("masteryPath.chaptersToImport", {
                              count: bookChapters.length,
                            })}
                          </p>
                          <div className="max-h-32 space-y-1 overflow-y-auto">
                            {bookChapters.map((ch, i) => (
                              <div
                                key={i}
                                className="flex items-center gap-2 text-xs text-[var(--muted-foreground)]"
                              >
                                <FileText className="h-3 w-3 shrink-0" />
                                <span className="truncate">{ch.title}</span>
                                <span className="opacity-50">
                                  ({(ch.learning_objectives ?? []).length}{" "}
                                  {t("masteryPath.kps")})
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </>
              )}
            </div>
          )}

          {source === "notebook" && (
            <div className="space-y-3">
              {loadingNotebooks ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-5 w-5 animate-spin text-[var(--muted-foreground)]" />
                </div>
              ) : notebooks.length === 0 ? (
                <div className="py-8 text-center text-sm text-[var(--muted-foreground)]">
                  {t("masteryPath.noNotebooks")}
                </div>
              ) : (
                <>
                  <div className="max-h-32 space-y-1 overflow-y-auto">
                    {notebooks.map((nb) => (
                      <button
                        key={nb.id}
                        onClick={() => setSelectedNotebook(nb.id)}
                        className={`w-full rounded-lg px-3 py-2 text-left text-sm transition-colors ${
                          selectedNotebook === nb.id
                            ? "border border-[var(--primary)]/30 bg-[var(--primary)]/10 text-[var(--foreground)]"
                            : "border border-transparent text-[var(--muted-foreground)] hover:bg-[var(--secondary)]/40 hover:text-[var(--foreground)]"
                        }`}
                      >
                        <div className="truncate font-medium">{nb.name}</div>
                        <div className="text-xs opacity-70">
                          {nb.record_count ?? 0} {t("masteryPath.records")}
                        </div>
                      </button>
                    ))}
                  </div>
                  {selectedNotebook && (
                    <div className="border-t border-[var(--border)] pt-3">
                      {loadingRecords ? (
                        <div className="flex items-center gap-2 text-sm text-[var(--muted-foreground)]">
                          <Loader2 className="h-4 w-4 animate-spin" />
                          {t("masteryPath.loadingRecords")}
                        </div>
                      ) : notebookRecords.length === 0 ? (
                        <div className="text-sm text-[var(--muted-foreground)]">
                          {t("masteryPath.noRecords")}
                        </div>
                      ) : (
                        <div>
                          <p className="mb-2 text-xs font-medium text-[var(--muted-foreground)]">
                            {t("masteryPath.selectRecords")} (
                            {selectedRecordIds.size} {t("masteryPath.selected")})
                          </p>
                          <div className="max-h-40 space-y-1 overflow-y-auto">
                            {notebookRecords.slice(0, 20).map((rec) => (
                              <label
                                key={rec.id}
                                className="flex cursor-pointer items-start gap-2 rounded px-2 py-1.5 text-xs hover:bg-[var(--secondary)]/40"
                              >
                                <input
                                  type="checkbox"
                                  checked={selectedRecordIds.has(rec.id)}
                                  onChange={(e) => {
                                    const next = new Set(selectedRecordIds);
                                    if (e.target.checked) next.add(rec.id);
                                    else next.delete(rec.id);
                                    setSelectedRecordIds(next);
                                  }}
                                  className="mt-0.5 rounded border-[var(--border)]"
                                />
                                <div className="min-w-0">
                                  <div className="truncate font-medium text-[var(--foreground)]">
                                    {rec.title || rec.id}
                                  </div>
                                  {rec.output && (
                                    <div className="truncate text-[var(--muted-foreground)] opacity-70">
                                      {rec.output.slice(0, 80)}
                                    </div>
                                  )}
                                </div>
                              </label>
                            ))}
                          </div>
                          {notebookRecords.length > 20 && (
                            <p className="mt-1 text-[10px] text-[var(--muted-foreground)] opacity-60">
                              {t("masteryPath.recordsLimited")}
                            </p>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-2 border-t border-[var(--border)] px-5 py-3">
          <button
            onClick={handleClose}
            className="rounded-lg border border-[var(--border)] px-4 py-1.5 text-sm text-[var(--muted-foreground)] hover:bg-[var(--secondary)]/40 hover:text-[var(--foreground)]"
          >
            {t("masteryPath.cancel")}
          </button>
          <button
            onClick={() => void handleSubmit()}
            disabled={submitDisabled}
            className="flex items-center gap-1.5 rounded-lg bg-[var(--primary)] px-4 py-1.5 text-sm text-[var(--primary-foreground)] hover:opacity-90 disabled:opacity-50"
          >
            {submitting && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
            {source === "notebook"
              ? t("masteryPath.generateModules")
              : t("masteryPath.create")}
          </button>
        </div>
      </div>
    </div>
  );
}
