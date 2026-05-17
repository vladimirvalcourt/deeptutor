"use client";

import { useCallback, useEffect, useState } from "react";
import { BookOpen, FileText, Loader2, Plus, Trash2, X } from "lucide-react";
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

type TabKey = "manual" | "book" | "kb" | "notebook";

interface KpRow {
  name: string;
  type: string;
}

export default function CreateModuleDialog({
  open,
  onClose,
  onCreated,
}: CreateModuleDialogProps) {
  const { t } = useTranslation();
  const [tab, setTab] = useState<TabKey>("manual");

  // ── Manual tab state ──
  const [moduleName, setModuleName] = useState("");
  const [kpRows, setKpRows] = useState<KpRow[]>([{ name: "", type: "concept" }]);
  const [manualBookId, setManualBookId] = useState("manual");

  // ── Book tab state ──
  const [books, setBooks] = useState<Book[]>([]);
  const [selectedBookId, setSelectedBookId] = useState<string>("");
  const [bookChapters, setBookChapters] = useState<{ title: string; learning_objectives: string[] }[]>([]);
  const [loadingBooks, setLoadingBooks] = useState(false);
  const [loadingChapters, setLoadingChapters] = useState(false);

  // ── Notebook tab state ──
  const [notebooks, setNotebooks] = useState<NotebookSummary[]>([]);
  const [selectedNotebook, setSelectedNotebook] = useState<string>("");
  const [notebookRecords, setNotebookRecords] = useState<NotebookRecordItem[]>([]);
  const [selectedRecordIds, setSelectedRecordIds] = useState<Set<string>>(new Set());
  const [loadingNotebooks, setLoadingNotebooks] = useState(false);
  const [loadingRecords, setLoadingRecords] = useState(false);

  // ── Shared state ──
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load data when tab changes
  useEffect(() => {
    if (!open) return;
    if (tab === "book" && books.length === 0) {
      setLoadingBooks(true);
      bookApi.list()
        .then((data) => setBooks(data.books ?? []))
        .catch(() => setError(t("guidedLearning.loadBooksFailed")))
        .finally(() => setLoadingBooks(false));
    }
    if (tab === "notebook" && notebooks.length === 0) {
      setLoadingNotebooks(true);
      listNotebooks()
        .then(setNotebooks)
        .catch(() => setError(t("guidedLearning.loadNotebooksFailed")))
        .finally(() => setLoadingNotebooks(false));
    }
  }, [open, tab, books.length, notebooks.length, t]);

  // Load chapters when book selected
  useEffect(() => {
    if (!selectedBookId) { setBookChapters([]); return; }
    setBookChapters([]);
    setLoadingChapters(true);
    import("@/lib/book-api").then(({ bookApi }) =>
      bookApi.get(selectedBookId)
        .then((data) => setBookChapters(data.spine?.chapters ?? []))
        .catch(() => setError(t("guidedLearning.loadChaptersFailed")))
        .finally(() => setLoadingChapters(false)),
    );
  }, [selectedBookId, t]);

  // Load records when notebook selected
  useEffect(() => {
    if (!selectedNotebook) { setNotebookRecords([]); setSelectedRecordIds(new Set()); return; }
    setLoadingRecords(true);
    getNotebook(selectedNotebook)
      .then((data) => setNotebookRecords(data.records ?? []))
      .catch(() => setError(t("guidedLearning.loadRecordsFailed")))
      .finally(() => setLoadingRecords(false));
  }, [selectedNotebook, t]);

  const resetState = useCallback(() => {
    setTab("manual");
    setModuleName("");
    setKpRows([{ name: "", type: "concept" }]);
    setManualBookId("manual");
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

  // ── Submit handlers ──

  const handleManualSubmit = async () => {
    const validKps = kpRows.filter((r) => r.name.trim());
    if (!moduleName.trim() && validKps.length === 0) {
      setError(t("guidedLearning.moduleNameRequired"));
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const bookId = manualBookId.trim() || "manual";
      const moduleId = `${bookId}_m${Date.now()}`;
      const modules: ModuleInit[] = [{
        id: moduleId,
        name: moduleName.trim() || t("guidedLearning.untitledModule"),
        order: 0,
        pass_threshold: 0.7,
        knowledge_points: validKps.map((kp, j) => ({
          id: `${moduleId}_kp${j}`,
          name: kp.name.trim(),
          type: kp.type,
          module_id: moduleId,
        })),
      }];
      await initModules(bookId, modules);
      onCreated();
      handleClose();
    } catch {
      setError(t("guidedLearning.createModuleFailed"));
    } finally {
      setSubmitting(false);
    }
  };

  const handleBookSubmit = async () => {
    if (!selectedBookId || bookChapters.length === 0) return;
    setSubmitting(true);
    setError(null);
    try {
      const chapters = bookChapters.map((ch) => ({
        title: ch.title,
        knowledge_points: ch.learning_objectives ?? [],
      }));
      await importFromBook(selectedBookId, chapters);
      onCreated();
      handleClose();
    } catch {
      setError(t("guidedLearning.importBookFailed"));
    } finally {
      setSubmitting(false);
    }
  };

  const handleNotebookSubmit = async () => {
    if (!selectedNotebook || selectedRecordIds.size === 0) return;
    setSubmitting(true);
    setError(null);
    try {
      const bookId = `nb_${selectedNotebook}`;
      const records = notebookRecords
        .filter((r) => selectedRecordIds.has(r.id))
        .map((r) => ({ id: r.id, type: r.type, title: r.title, output: r.output }));
      await generateModulesFromNotebook(bookId, selectedNotebook, records.slice(0, 20));
      onCreated();
      handleClose();
    } catch {
      setError(t("guidedLearning.importNotebookFailed"));
    } finally {
      setSubmitting(false);
    }
  };

  if (!open) return null;

  const tabs: { key: TabKey; label: string }[] = [
    { key: "manual", label: t("guidedLearning.tabManual") },
    { key: "book", label: t("guidedLearning.tabBook") },
    { key: "kb", label: t("guidedLearning.tabKb") + " (" + t("guidedLearning.comingSoon") + ")" },
    { key: "notebook", label: t("guidedLearning.tabNotebook") },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/40 backdrop-blur-sm"
        onClick={handleClose}
      />
      {/* Dialog */}
      <div className="relative z-10 w-full max-w-lg max-h-[80vh] flex flex-col rounded-xl border border-[var(--border)] bg-[var(--card)] shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-[var(--border)]">
          <h2 className="text-lg font-semibold text-[var(--foreground)]">
            {t("guidedLearning.createModule")}
          </h2>
          <button
            onClick={handleClose}
            className="p-1 rounded-md text-[var(--muted-foreground)] hover:text-[var(--foreground)] hover:bg-[var(--secondary)]"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 px-5 pt-3 border-b border-[var(--border)]">
          {tabs.map((tb) => (
            <button
              key={tb.key}
              onClick={() => { setTab(tb.key); setError(null); }}
              className={`px-3 py-1.5 text-xs font-medium rounded-t-md transition-colors border-b-2 -mb-px ${
                tab === tb.key
                  ? "border-[var(--primary)] text-[var(--foreground)] bg-[var(--secondary)]/40"
                  : "border-transparent text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
              }`}
            >
              {tb.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-5 py-4">
          {error && (
            <div className="mb-3 rounded-lg bg-red-500/10 border border-red-500/20 px-3 py-2 text-xs text-red-500">
              {error}
            </div>
          )}

          {/* Manual Tab */}
          {tab === "manual" && (
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-[var(--muted-foreground)] mb-1">
                  {t("guidedLearning.bookId")}
                </label>
                <input
                  value={manualBookId}
                  onChange={(e) => setManualBookId(e.target.value)}
                  placeholder="manual"
                  className="w-full rounded-md border border-[var(--border)] bg-[var(--background)] px-3 py-1.5 text-sm text-[var(--foreground)] placeholder:text-[var(--muted-foreground)]/50 focus:border-[var(--primary)]/40 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-[var(--muted-foreground)] mb-1">
                  {t("guidedLearning.moduleName")}
                </label>
                <input
                  value={moduleName}
                  onChange={(e) => setModuleName(e.target.value)}
                  placeholder={t("guidedLearning.moduleNamePlaceholder")}
                  className="w-full rounded-md border border-[var(--border)] bg-[var(--background)] px-3 py-1.5 text-sm text-[var(--foreground)] placeholder:text-[var(--muted-foreground)]/50 focus:border-[var(--primary)]/40 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-[var(--muted-foreground)] mb-2">
                  {t("guidedLearning.knowledgePoints")}
                </label>
                {kpRows.map((row, i) => (
                  <div key={i} className="flex items-center gap-2 mb-2">
                    <input
                      value={row.name}
                      onChange={(e) => {
                        const next = [...kpRows];
                        next[i] = { ...next[i], name: e.target.value };
                        setKpRows(next);
                      }}
                      placeholder={t("guidedLearning.kpNamePlaceholder")}
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
                      <option value="procedure">{t("knowledgeType.procedure")}</option>
                      <option value="design">{t("knowledgeType.design")}</option>
                    </select>
                    {kpRows.length > 1 && (
                      <button
                        onClick={() => setKpRows(kpRows.filter((_, j) => j !== i))}
                        className="p-1 text-[var(--muted-foreground)] hover:text-red-500"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                ))}
                <button
                  onClick={() => setKpRows([...kpRows, { name: "", type: "concept" }])}
                  className="flex items-center gap-1 text-xs text-[var(--primary)] hover:opacity-80"
                >
                  <Plus className="w-3 h-3" />
                  {t("guidedLearning.addKp")}
                </button>
              </div>
            </div>
          )}

          {/* Book Tab */}
          {tab === "book" && (
            <div className="space-y-3">
              {loadingBooks ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-5 h-5 animate-spin text-[var(--muted-foreground)]" />
                </div>
              ) : books.length === 0 ? (
                <div className="py-8 text-center text-sm text-[var(--muted-foreground)]">
                  {t("guidedLearning.noBooks")}
                </div>
              ) : (
                <>
                  <div className="max-h-40 overflow-y-auto space-y-1">
                    {books.map((book) => (
                      <button
                        key={book.id}
                        onClick={() => setSelectedBookId(book.id)}
                        className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                          selectedBookId === book.id
                            ? "bg-[var(--primary)]/10 border border-[var(--primary)]/30 text-[var(--foreground)]"
                            : "border border-transparent text-[var(--muted-foreground)] hover:bg-[var(--secondary)]/40 hover:text-[var(--foreground)]"
                        }`}
                      >
                        <div className="font-medium truncate">{book.title || book.id}</div>
                        <div className="text-xs opacity-70">
                          {book.chapter_count ?? 0} {t("guidedLearning.chapters")} · {book.status}
                        </div>
                      </button>
                    ))}
                  </div>
                  {selectedBookId && (
                    <div className="border-t border-[var(--border)] pt-3">
                      {loadingChapters ? (
                        <div className="flex items-center gap-2 text-sm text-[var(--muted-foreground)]">
                          <Loader2 className="w-4 h-4 animate-spin" />
                          {t("guidedLearning.loadingChapters")}
                        </div>
                      ) : bookChapters.length === 0 ? (
                        <div className="text-sm text-[var(--muted-foreground)]">
                          {t("guidedLearning.noChapters")}
                        </div>
                      ) : (
                        <div>
                          <p className="text-xs font-medium text-[var(--muted-foreground)] mb-2">
                            {t("guidedLearning.chaptersToImport", { count: bookChapters.length })}
                          </p>
                          <div className="max-h-32 overflow-y-auto space-y-1">
                            {bookChapters.map((ch, i) => (
                              <div key={i} className="flex items-center gap-2 text-xs text-[var(--muted-foreground)]">
                                <FileText className="w-3 h-3 shrink-0" />
                                <span className="truncate">{ch.title}</span>
                                <span className="opacity-50">
                                  ({(ch.learning_objectives ?? []).length} {t("guidedLearning.kps")})
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

          {/* KB Tab */}
          {tab === "kb" && (
            <div className="flex flex-col items-center justify-center py-8 text-[var(--muted-foreground)]">
              <BookOpen className="w-8 h-8 mb-3 opacity-40" />
              <p className="text-sm font-medium">{t("guidedLearning.kbComingSoon")}</p>
              <p className="text-xs mt-1 opacity-70">{t("guidedLearning.kbComingSoonDesc")}</p>
            </div>
          )}

          {/* Notebook Tab */}
          {tab === "notebook" && (
            <div className="space-y-3">
              {loadingNotebooks ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-5 h-5 animate-spin text-[var(--muted-foreground)]" />
                </div>
              ) : notebooks.length === 0 ? (
                <div className="py-8 text-center text-sm text-[var(--muted-foreground)]">
                  {t("guidedLearning.noNotebooks")}
                </div>
              ) : (
                <>
                  <div className="max-h-32 overflow-y-auto space-y-1">
                    {notebooks.map((nb) => (
                      <button
                        key={nb.id}
                        onClick={() => setSelectedNotebook(nb.id)}
                        className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                          selectedNotebook === nb.id
                            ? "bg-[var(--primary)]/10 border border-[var(--primary)]/30 text-[var(--foreground)]"
                            : "border border-transparent text-[var(--muted-foreground)] hover:bg-[var(--secondary)]/40 hover:text-[var(--foreground)]"
                        }`}
                      >
                        <div className="font-medium truncate">{nb.name}</div>
                        <div className="text-xs opacity-70">
                          {nb.record_count ?? 0} {t("guidedLearning.records")}
                        </div>
                      </button>
                    ))}
                  </div>
                  {selectedNotebook && (
                    <div className="border-t border-[var(--border)] pt-3">
                      {loadingRecords ? (
                        <div className="flex items-center gap-2 text-sm text-[var(--muted-foreground)]">
                          <Loader2 className="w-4 h-4 animate-spin" />
                          {t("guidedLearning.loadingRecords")}
                        </div>
                      ) : notebookRecords.length === 0 ? (
                        <div className="text-sm text-[var(--muted-foreground)]">
                          {t("guidedLearning.noRecords")}
                        </div>
                      ) : (
                        <div>
                          <p className="text-xs font-medium text-[var(--muted-foreground)] mb-2">
                            {t("guidedLearning.selectRecords")} ({selectedRecordIds.size} {t("guidedLearning.selected")})
                          </p>
                          <div className="max-h-40 overflow-y-auto space-y-1">
                            {notebookRecords.slice(0, 20).map((rec) => (
                              <label
                                key={rec.id}
                                className="flex items-start gap-2 px-2 py-1.5 rounded text-xs cursor-pointer hover:bg-[var(--secondary)]/40"
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
                                  <div className="font-medium text-[var(--foreground)] truncate">
                                    {rec.title || rec.id}
                                  </div>
                                  {rec.output && (
                                    <div className="text-[var(--muted-foreground)] truncate opacity-70">
                                      {rec.output.slice(0, 80)}
                                    </div>
                                  )}
                                </div>
                              </label>
                            ))}
                          </div>
                          {notebookRecords.length > 20 && (
                            <p className="text-[10px] text-[var(--muted-foreground)] mt-1 opacity-60">
                              {t("guidedLearning.recordsLimited")}
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
        <div className="flex items-center justify-end gap-2 px-5 py-3 border-t border-[var(--border)]">
          <button
            onClick={handleClose}
            className="px-4 py-1.5 text-sm rounded-lg border border-[var(--border)] text-[var(--muted-foreground)] hover:text-[var(--foreground)] hover:bg-[var(--secondary)]/40"
          >
            {t("guidedLearning.cancel")}
          </button>
          <button
            onClick={() => {
              if (tab === "manual") void handleManualSubmit();
              else if (tab === "book") void handleBookSubmit();
              else if (tab === "notebook") void handleNotebookSubmit();
            }}
            disabled={submitting || tab === "kb" || (tab === "book" && (!selectedBookId || bookChapters.length === 0)) || (tab === "notebook" && selectedRecordIds.size === 0)}
            className="flex items-center gap-1.5 px-4 py-1.5 text-sm rounded-lg bg-[var(--primary)] text-[var(--primary-foreground)] hover:opacity-90 disabled:opacity-50"
          >
            {submitting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
            {tab === "notebook" ? t("guidedLearning.generateModules") : t("guidedLearning.create")}
          </button>
        </div>
      </div>
    </div>
  );
}
