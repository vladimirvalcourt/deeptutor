import { apiUrl, apiFetch } from "./api";

export interface AnswerRequest {
  question_id: string;
  knowledge_point_id: string;
  module_id?: string;
  user_answer: string;
  self_attribution?: string;
}

export interface ModuleInit {
  id: string;
  name: string;
  order: number;
  pass_threshold?: number;
  knowledge_points: { id: string; name: string; type: string; module_id: string }[];
}

export async function fetchProgress(bookId: string) {
  const res = await apiFetch(apiUrl(`/api/v1/learning/progress/${bookId}`));
  if (!res.ok) throw new Error(`Failed to fetch progress: ${res.status}`);
  return res.json();
}

export async function submitAnswer(bookId: string, body: AnswerRequest) {
  const res = await apiFetch(apiUrl(`/api/v1/learning/progress/${bookId}/answer`), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Failed to submit answer: ${res.status}`);
  return res.json();
}

export async function initModules(bookId: string, modules: ModuleInit[]) {
  const res = await apiFetch(apiUrl(`/api/v1/learning/progress/${bookId}/init-modules`), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ modules }),
  });
  if (!res.ok) throw new Error(`Failed to init modules: ${res.status}`);
  return res.json();
}

export interface ProgressSummary {
  book_id: string;
  modules_count: number;
  kp_count: number;
  current_stage: string;
  mastered_pct: number;
  updated_at: number;
}

export async function fetchAllProgress(): Promise<ProgressSummary[]> {
  const res = await apiFetch(apiUrl("/api/v1/learning/progress"));
  if (!res.ok) throw new Error(`Failed to fetch all progress: ${res.status}`);
  return res.json();
}

export async function deleteProgress(bookId: string) {
  const res = await apiFetch(apiUrl(`/api/v1/learning/progress/${encodeURIComponent(bookId)}`), { method: "DELETE" });
  if (!res.ok) throw new Error(`Failed to delete progress: ${res.status}`);
  return res.json();
}

export async function redoProgress(bookId: string) {
  const res = await apiFetch(apiUrl(`/api/v1/learning/progress/${encodeURIComponent(bookId)}/redo`), { method: "POST" });
  if (!res.ok) throw new Error(`Failed to redo progress: ${res.status}`);
  return res.json();
}

export async function importFromBook(bookId: string, chapters: { title: string; knowledge_points: string[] }[]) {
  const res = await apiFetch(apiUrl(`/api/v1/learning/progress/${encodeURIComponent(bookId)}/import-from-book`), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ chapters }),
  });
  if (!res.ok) throw new Error(`Failed to import from book: ${res.status}`);
  return res.json();
}

export async function generateModulesFromNotebook(
  bookId: string,
  notebookId: string,
  records: { id: string; type: string; title: string; output: string }[],
): Promise<{ modules: ModuleInit[] }> {
  const res = await apiFetch(apiUrl(`/api/v1/learning/progress/${encodeURIComponent(bookId)}/generate-from-notebook`), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ notebook_id: notebookId, records }),
  });
  if (!res.ok) throw new Error(`Failed to generate modules from notebook: ${res.status}`);
  return res.json();
}
