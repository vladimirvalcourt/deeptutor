<div align="center">

<p align="center"><img src="assets/figs/logo/logo.png" alt="DeepTutor logo" height="56" style="vertical-align: middle;">&nbsp;<img src="assets/figs/logo/banner.png" alt="DeepTutor" height="48" style="vertical-align: middle;"></p>

# DeepTutor: Agent-Native Personalized Tutoring

<p align="center">
  <a href="https://deeptutor.info" target="_blank"><img alt="Docs — deeptutor.info" src="https://img.shields.io/badge/Docs-deeptutor.info%20%E2%86%97-0A0A0A?style=for-the-badge&labelColor=F5F5F4" height="36"></a>
</p>

<a href="https://trendshift.io/repositories/17099" target="_blank"><img src="https://trendshift.io/api/badge/repositories/17099" alt="HKUDS%2FDeepTutor | Trendshift" style="width: 250px; height: 55px;" width="250" height="55"/></a>

<p align="center">
  <a href="README.md"><img alt="English" height="40" src="https://img.shields.io/badge/English-BCDCF7"></a>&nbsp;
  <a href="assets/README/README_CN.md"><img alt="简体中文" height="40" src="https://img.shields.io/badge/简体中文-CDCFD4"></a>&nbsp;
  <a href="assets/README/README_JA.md"><img alt="日本語" height="40" src="https://img.shields.io/badge/日本語-CDCFD4"></a>&nbsp;
  <a href="assets/README/README_ES.md"><img alt="Español" height="40" src="https://img.shields.io/badge/Español-CDCFD4"></a>&nbsp;
  <a href="assets/README/README_FR.md"><img alt="Français" height="40" src="https://img.shields.io/badge/Français-CDCFD4"></a>&nbsp;
  <a href="assets/README/README_AR.md"><img alt="Arabic" height="40" src="https://img.shields.io/badge/Arabic-CDCFD4"></a>&nbsp;
  <a href="assets/README/README_RU.md"><img alt="Русский" height="40" src="https://img.shields.io/badge/Русский-CDCFD4"></a>&nbsp;
  <a href="assets/README/README_HI.md"><img alt="Hindi" height="40" src="https://img.shields.io/badge/Hindi-CDCFD4"></a>&nbsp;
  <a href="assets/README/README_PT.md"><img alt="Português" height="40" src="https://img.shields.io/badge/Português-CDCFD4"></a>&nbsp;
  <a href="assets/README/README_TH.md"><img alt="Thai" height="40" src="https://img.shields.io/badge/Thai-CDCFD4"></a>&nbsp;
  <a href="assets/README/README_PL.md"><img alt="Polski" height="40" src="https://img.shields.io/badge/Polski-CDCFD4"></a>
</p>

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/downloads/)
[![Next.js 16](https://img.shields.io/badge/Next.js-16-000000?style=flat-square&logo=next.js&logoColor=white)](https://nextjs.org/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue?style=flat-square)](LICENSE)
[![GitHub release](https://img.shields.io/github/v/release/HKUDS/DeepTutor?style=flat-square&color=brightgreen)](https://github.com/HKUDS/DeepTutor/releases)
[![arXiv](https://img.shields.io/badge/arXiv-2604.26962-b31b1b?style=flat-square&logo=arxiv&logoColor=white)](https://arxiv.org/abs/2604.26962)

[![Discord](https://img.shields.io/badge/Discord-Community-5865F2?style=flat-square&logo=discord&logoColor=white)](https://discord.gg/eRsjPgMU4t)
[![Feishu](https://img.shields.io/badge/Feishu-Group-00D4AA?style=flat-square&logo=feishu&logoColor=white)](./Communication.md)
[![WeChat](https://img.shields.io/badge/WeChat-Group-07C160?style=flat-square&logo=wechat&logoColor=white)](https://github.com/HKUDS/DeepTutor/issues/78)

[Features](#-key-features) · [Get Started](#-get-started) · [Explore](#-explore-deeptutor) · [CLI](#%EF%B8%8F-deeptutor-cli--agent-native-interface) · [Multi-User](#-multi-user--shared-deployments) · [Community](#-community--ecosystem)

</div>

---

> 🤝 **We welcome any kinds of contributing!** Vote on roadmap items or propose new ones at [`Roadmap`](https://github.com/HKUDS/DeepTutor/issues/498), and see our [Contributing Guide](CONTRIBUTING.md) for branching strategy, coding standards, and how to get started.

### 📦 Releases

> **[2026.5.28]** [v1.4.2](https://github.com/HKUDS/DeepTutor/releases/tag/v1.4.2) — Stability + polish on v1.4.1: Gemini 2.5+ unblocked across Visualize and Chat, ContextVar auth-routing fix (#485), reasoning + native-tools label protocol hardened, smooth-streaming UX on every chat surface, new collapsible Recents sidebar, and Lemonade local-provider support.

> **[2026.5.27]** [v1.4.1](https://github.com/HKUDS/DeepTutor/releases/tag/v1.4.1) — Security + stability patch: TutorBot tool sandbox locked down, per-user resource isolation, multimodal image fallback for vision-capable providers, an HTTP/SSE API for talking to a TutorBot, and a v1.4.0 chat regression fix.

> **[2026.5.22]** [v1.4.0](https://github.com/HKUDS/DeepTutor/releases/tag/v1.4.0) — GA cut of v1.4: Auto Mode, three-layer Memory, agentic Deep Research / Solve / Question, LlamaIndex RAG refactor, Visualize/Animator merge, plus reasoning-effort normalization, tool-schema fallback, and restart-safe turn runtime.

> **[2026.5.21]** [v1.4.0-beta](https://github.com/HKUDS/DeepTutor/releases/tag/v1.4.0-beta) — Three-layer Memory workbench (L1/L2/L3), every chat capability rebuilt on a single agentic engine, LlamaIndex-only RAG, and a unified Settings + Capabilities surface.

<details>
<summary><b>Past releases (more than 2 weeks ago)</b></summary>

> **[2026.5.10]** [v1.3.10](https://github.com/HKUDS/DeepTutor/releases/tag/v1.3.10) — Remote Docker CORS recovery, `DISABLE_SSL_VERIFY` across SDK providers, safer code-block citations, and optional Matrix E2EE add-on.

> **[2026.5.9]** [v1.3.9](https://github.com/HKUDS/DeepTutor/releases/tag/v1.3.9) — TutorBot Zulip and NVIDIA NIM support, safer thinking-model routing, `deeptutor start`, sidebar tooltips, and session-store parity.

> **[2026.5.8]** [v1.3.8](https://github.com/HKUDS/DeepTutor/releases/tag/v1.3.8) — Optional multi-user deployments with isolated user workspaces, admin grants, auth routes, and scoped runtime access.

> **[2026.5.4]** [v1.3.7](https://github.com/HKUDS/DeepTutor/releases/tag/v1.3.7) — Thinking-model/provider fixes, visible Knowledge index history, and safer Co-Writer clear/template editing.

> **[2026.5.3]** [v1.3.6](https://github.com/HKUDS/DeepTutor/releases/tag/v1.3.6) — Catalog-based model selection for chat and TutorBot, safer RAG re-indexing, OpenAI Responses token-limit fixes, and Skills editor validation.

> **[2026.5.2]** [v1.3.5](https://github.com/HKUDS/DeepTutor/releases/tag/v1.3.5) — Smoother local launch settings, safer RAG queries, cleaner local embedding auth, and Settings dark-mode polish.

> **[2026.5.1]** [v1.3.4](https://github.com/HKUDS/DeepTutor/releases/tag/v1.3.4) — Book page chat persistence and rebuild flows, chat-to-book references, stronger language/reasoning handling, RAG document extraction hardening.

> **[2026.4.30]** [v1.3.3](https://github.com/HKUDS/DeepTutor/releases/tag/v1.3.3) — NVIDIA NIM + Gemini embedding support, unified Space context for chat history/skills/memory, session snapshots, RAG re-index resilience.

> **[2026.4.29]** [v1.3.2](https://github.com/HKUDS/DeepTutor/releases/tag/v1.3.2) — Transparent embedding endpoint URLs, RAG re-index resilience for invalid persisted vectors, memory cleanup for thinking-model output, Deep Solve runtime fix.

> **[2026.4.28]** [v1.3.1](https://github.com/HKUDS/DeepTutor/releases/tag/v1.3.1) — Stability: safer RAG routing & embedding validation, Docker persistence, IME-safe input, Windows/GBK robustness.

> **[2026.4.27]** [v1.3.0](https://github.com/HKUDS/DeepTutor/releases/tag/v1.3.0) — Versioned KB indexes with re-index workflow, rebuilt Knowledge workspace, embedding auto-discovery with new adapters, Space hub.

> **[2026.4.25]** [v1.2.5](https://github.com/HKUDS/DeepTutor/releases/tag/v1.2.5) — Persistent chat attachments with file-preview drawer, attachment-aware capability pipelines, TutorBot Markdown export.

> **[2026.4.25]** [v1.2.4](https://github.com/HKUDS/DeepTutor/releases/tag/v1.2.4) — Text/code/SVG attachments, one-command Setup Tour, Markdown chat export, compact KB management UI.

> **[2026.4.24]** [v1.2.3](https://github.com/HKUDS/DeepTutor/releases/tag/v1.2.3) — Document attachments (PDF/DOCX/XLSX/PPTX), reasoning thinking-block display, Soul template editor, Co-Writer save-to-notebook.

> **[2026.4.22]** [v1.2.2](https://github.com/HKUDS/DeepTutor/releases/tag/v1.2.2) — User-authored Skills system, chat input performance overhaul, TutorBot auto-start, Book Library UI, visualization fullscreen.

> **[2026.4.21]** [v1.2.1](https://github.com/HKUDS/DeepTutor/releases/tag/v1.2.1) — Per-stage token limits, Regenerate response across all entry points, RAG & Gemma compatibility fixes.

> **[2026.4.20]** [v1.2.0](https://github.com/HKUDS/DeepTutor/releases/tag/v1.2.0) — Book Engine "living book" compiler, multi-document Co-Writer, interactive HTML visualizations, Question Bank @-mention.

> **[2026.4.18]** [v1.1.2](https://github.com/HKUDS/DeepTutor/releases/tag/v1.1.2) — Schema-driven Channels tab, RAG single-pipeline consolidation, externalized chat prompts.

> **[2026.4.17]** [v1.1.1](https://github.com/HKUDS/DeepTutor/releases/tag/v1.1.1) — Universal "Answer now", Co-Writer scroll sync, unified settings panel, streaming Stop button.

> **[2026.4.15]** [v1.1.0](https://github.com/HKUDS/DeepTutor/releases/tag/v1.1.0) — LaTeX block math overhaul, LLM diagnostic probe, Docker + local LLM guidance.

> **[2026.4.14]** [v1.1.0-beta](https://github.com/HKUDS/DeepTutor/releases/tag/v1.1.0-beta) — Bookmarkable sessions, Snow theme, WebSocket heartbeat & auto-reconnect, embedding registry overhaul.

> **[2026.4.13]** [v1.0.3](https://github.com/HKUDS/DeepTutor/releases/tag/v1.0.3) — Question Notebook with bookmarks & categories, Mermaid in Visualize, embedding mismatch detection, Qwen/vLLM compatibility, LM Studio & llama.cpp support, and Glass theme.

> **[2026.4.11]** [v1.0.2](https://github.com/HKUDS/DeepTutor/releases/tag/v1.0.2) — Search consolidation with SearXNG fallback, provider switch fix, and frontend resource leak fixes.

> **[2026.4.10]** [v1.0.1](https://github.com/HKUDS/DeepTutor/releases/tag/v1.0.1) — Visualize capability (Chart.js/SVG), quiz duplicate prevention, and o4-mini model support.

> **[2026.4.10]** [v1.0.0-beta.4](https://github.com/HKUDS/DeepTutor/releases/tag/v1.0.0-beta.4) — Embedding progress tracking with rate-limit retry, cross-platform dependency fixes, and MIME validation fix.

> **[2026.4.8]** [v1.0.0-beta.3](https://github.com/HKUDS/DeepTutor/releases/tag/v1.0.0-beta.3) — Native OpenAI/Anthropic SDK (drop litellm), Windows Math Animator support, robust JSON parsing, and full Chinese i18n.

> **[2026.4.7]** [v1.0.0-beta.2](https://github.com/HKUDS/DeepTutor/releases/tag/v1.0.0-beta.2) — Hot settings reload, MinerU nested output, WebSocket fix, and Python 3.11+ minimum.

> **[2026.4.4]** [v1.0.0-beta.1](https://github.com/HKUDS/DeepTutor/releases/tag/v1.0.0-beta.1) — Agent-native architecture rewrite (~200k lines): Tools + Capabilities plugin model, CLI & SDK, TutorBot, Co-Writer, Guided Learning, and persistent memory.

> **[2026.1.23]** [v0.6.0](https://github.com/HKUDS/DeepTutor/releases/tag/v0.6.0) — Session persistence, incremental document upload, flexible RAG pipeline import, and full Chinese localization.

> **[2026.1.18]** [v0.5.2](https://github.com/HKUDS/DeepTutor/releases/tag/v0.5.2) — Docling support for RAG-Anything, logging system optimization, and bug fixes.

> **[2026.1.15]** [v0.5.0](https://github.com/HKUDS/DeepTutor/releases/tag/v0.5.0) — Unified service configuration, RAG pipeline selection per knowledge base, question generation overhaul, and sidebar customization.

> **[2026.1.9]** [v0.4.0](https://github.com/HKUDS/DeepTutor/releases/tag/v0.4.0) — Multi-provider LLM & embedding support, new home page, RAG module decoupling, and environment variable refactor.

> **[2026.1.5]** [v0.3.0](https://github.com/HKUDS/DeepTutor/releases/tag/v0.3.0) — Unified PromptManager architecture, GitHub Actions CI/CD, and pre-built Docker images on GHCR.

> **[2026.1.2]** [v0.2.0](https://github.com/HKUDS/DeepTutor/releases/tag/v0.2.0) — Docker deployment, Next.js 16 & React 19 upgrade, WebSocket security hardening, and critical vulnerability fixes.

</details>

### 📰 News

> **[2026.5.22]** 🌐 Our official docs site is live at [**deeptutor.info**](https://deeptutor.info/) — guides, references, and capability tours all in one place.

> **[2026.4.19]** 🎉 We've reached 20k stars after 111 days! Thank you for the incredible support — we're committed to continuous iteration toward truly personalized, intelligent tutoring for everyone.

> **[2026.4.10]** 📄 Our paper is now live on arXiv! Read the [preprint](https://arxiv.org/abs/2604.26962) to learn more about the design and ideas behind DeepTutor.

> **[2026.4.4]** Long time no see! ✨ DeepTutor v1.0.0 is finally here — an agent-native evolution featuring a ground-up architecture rewrite, TutorBot, and flexible mode switching under the Apache-2.0 license. A new chapter begins, and our story continues!

> **[2026.2.6]** 🚀 We've reached 10k stars in just 39 days! A huge thank you to our incredible community for the support!

> **[2026.1.1]** Happy New Year! Join our [Discord](https://discord.gg/eRsjPgMU4t), [WeChat](https://github.com/HKUDS/DeepTutor/issues/78), or [Discussions](https://github.com/HKUDS/DeepTutor/discussions) — let's shape the future of DeepTutor together!

> **[2025.12.29]** DeepTutor is officially released!

## ✨ Key Features

DeepTutor is organized around an agent-native runtime: a shared ChatOrchestrator routes every turn into capabilities, a ToolRegistry exposes single-shot tools when the model needs them, and a CapabilityRegistry lets deeper workflows take over the turn when the task needs structure.

<div align="center">
<img src="assets/figs/system/system%20architecture.png" alt="DeepTutor system architecture" width="900">
</div>

**One learning workspace**

- **Chat as the default loop** — casual tutoring, source-grounded Q&A, Deep Solve, Deep Question, Deep Research, Visualize, and Auto Mode all share the same session context and source inventory.
- **Learning surfaces that stay connected** — Co-Writer drafts, Book pages, Knowledge Bases, Space assets, and Memory are separate workspaces, but they feed the same agent runtime instead of becoming isolated apps.
- **Partners for persistent companionship** — IM-connected companions now run on the same chat agent loop as the main product, with their own synthetic workspace and assigned library.

**Tools, memory, and control**

- **Composable tools** — RAG, source reading, memory read/write, notebooks, URL fetch, GitHub lookup, ask-user pauses, sandboxed execution, and optional brainstorm/web/paper/reason tools can be mounted according to context and settings.
- **Three-layer memory** — L1 traces, L2 per-surface summaries, and L3 cross-surface synthesis make personalization inspectable rather than hidden behind a black box.
- **Unified settings and CLI** — model catalogs, embeddings, search, network, MCP servers, tools, capabilities, and deployment settings are editable from the web UI and scriptable from `deeptutor`.

---

## 🚀 Get Started

DeepTutor ships four installation paths. They all share one workspace layout: settings live in `data/user/settings/` under the directory you launch from (or under `DEEPTUTOR_HOME` / `deeptutor start --home` if you set one explicitly). For the full app, the recommended flow is **pick a workspace directory → install → `deeptutor init` → `deeptutor start`**.

> ✨ **v1.4.2 is live.** `pip install -U deeptutor` picks up the latest stable. Pre-releases (when available) opt in with `pip install --pre -U deeptutor`.

### Option 1 — Install From PyPI

Full local Web app + CLI, no clone required. Needs **Python 3.11+** and a **Node.js 20+** runtime on PATH (the packaged Next.js standalone server is spawned by `deeptutor start`).

```bash
mkdir -p my-deeptutor && cd my-deeptutor
pip install -U deeptutor
deeptutor init     # prompts for ports + LLM provider + optional embedding
deeptutor start    # starts backend + frontend; keep the terminal open
```

`deeptutor init` prompts for backend port (default `8001`), frontend port (default `3782`), LLM provider / base URL / API key / model, and an optional embedding provider for Knowledge Base / RAG.

After `deeptutor start`, open the frontend URL printed in the terminal — by default [http://127.0.0.1:3782](http://127.0.0.1:3782). Press `Ctrl+C` in that terminal to stop both backend and frontend. Skipping `deeptutor init` is fine for a quick trial; the app boots with default ports and empty model settings, configure them later in **Settings → Models**.

### Option 2 — Install From Source

For development against a checkout. Use **Python 3.11+** and **Node.js 22 LTS** to match CI and Docker.

```bash
git clone https://github.com/HKUDS/DeepTutor.git
cd DeepTutor

# Create a venv (macOS/Linux). Windows PowerShell:
#   py -3.11 -m venv .venv ; .\.venv\Scripts\Activate.ps1
python3 -m venv .venv && source .venv/bin/activate
python -m pip install --upgrade pip

# Install backend + frontend deps
python -m pip install -e .
( cd web && npm ci --legacy-peer-deps )

deeptutor init
deeptutor start
```

Source installs run Next.js in dev mode against the local `web/` directory; everything else (config layout, ports, stop with `Ctrl+C`) matches Option 1.

<details>
<summary><b>Conda environment</b> (instead of <code>venv</code>)</summary>

```bash
conda create -n deeptutor python=3.11
conda activate deeptutor
python -m pip install --upgrade pip
```

</details>

<details>
<summary><b>Optional install extras</b> — dev / partners / matrix / math-animator</summary>

```bash
pip install -e ".[dev]"             # tests/lint tools
pip install -e ".[partners]"        # Partner IM channel SDKs + MCP client
pip install -e ".[matrix]"          # Matrix channel without E2EE/libolm
pip install -e ".[matrix-e2e]"      # Matrix E2EE; requires libolm
pip install -e ".[math-animator]"   # Manim addon; requires LaTeX/ffmpeg/system libs
```

</details>

<details>
<summary><b>Frontend dependency tweaks & dev-server troubleshooting</b></summary>

**Changing frontend dependencies:** run `npm install --legacy-peer-deps` to refresh `web/package-lock.json`, then commit both `web/package.json` and `web/package-lock.json`.

**Stuck dev server:** if `deeptutor start` reports an existing frontend that isn't responding, stop the PID it prints. If no Next.js process is actually running, the lock files are stale — remove them and retry:

```bash
rm -f web/.next/dev/lock web/.next/lock
deeptutor start
```

</details>

### Option 3 — Docker

One container for the full Web app. Images on GitHub Container Registry:

- `ghcr.io/hkuds/deeptutor:latest` — stable release
- `ghcr.io/hkuds/deeptutor:pre` — pre-release, when available

```bash
docker run --rm --name deeptutor \
  -p 127.0.0.1:3782:3782 \
  -p 127.0.0.1:8001:8001 \
  -v deeptutor-data:/app/data \
  ghcr.io/hkuds/deeptutor:latest
```

> ⚠️ **Map both `3782` and `8001`.** `3782` serves the web UI; `8001` is the FastAPI backend that your browser calls directly — there is no in-container proxy. Skip the `8001` mapping and the page still loads, but **Settings** shows "Backend unreachable" and stays unusable.

Open [http://127.0.0.1:3782](http://127.0.0.1:3782). The container creates `/app/data/user/settings/*.json` on first boot; configure model providers from the Web Settings page. Config, API keys, logs, workspace files, memory, and knowledge bases persist in the `deeptutor-data` volume.

- **Different host ports:** change the left side of each `-p host:container` mapping (e.g. `-p 127.0.0.1:8088:3782`). If you change container-side ports in `/app/data/user/settings/system.json`, restart and update the right side of each mapping to match.
- **Detached:** add `-d`, then `docker logs -f deeptutor` to follow, `docker stop deeptutor` to stop, `docker rm deeptutor` before reusing the name. The `deeptutor-data` volume keeps your settings and workspace across restarts.

**Remote Docker / reverse proxy:** the Web UI runs in the browser, so the
browser needs a backend URL it can reach. For remote servers, open
**Settings -> Network** or edit `data/user/settings/system.json`:

```json
{
  "next_public_api_base_external": "https://deeptutor.example.com"
}
```

`public_api_base` is accepted as a compatibility alias and is normalized into
`next_public_api_base_external` on save. CORS uses frontend **origins**, not API
URLs. With auth disabled, DeepTutor permits normal HTTP/HTTPS browser origins by
default. With auth enabled, add exact frontend origins:

```json
{
  "cors_origins": ["https://deeptutor.example.com"]
}
```

<details>
<summary><b>Connecting to Ollama / LM Studio / llama.cpp / vLLM / Lemonade on the host</b></summary>

Inside Docker, `localhost` is the container itself, not your host machine. To reach a model service running on the host, use the host gateway (recommended):

```bash
docker run --rm --name deeptutor \
  -p 127.0.0.1:3782:3782 -p 127.0.0.1:8001:8001 \
  --add-host=host.docker.internal:host-gateway \
  -v deeptutor-data:/app/data \
  ghcr.io/hkuds/deeptutor:latest
```

Then in **Settings → Models**, point the provider Base URL at `host.docker.internal`:

- Ollama LLM: `http://host.docker.internal:11434/v1`
- Ollama embedding: `http://host.docker.internal:11434/api/embed`
- LM Studio: `http://host.docker.internal:1234/v1`
- llama.cpp: `http://host.docker.internal:8080/v1`
- Lemonade: `http://host.docker.internal:13305/api/v1`

Docker Desktop (macOS/Windows) usually resolves `host.docker.internal` without `--add-host`. On Linux, the flag is the portable way to create that hostname on modern Docker Engine.

**Linux alternative — host networking:** add `--network=host` and drop the `-p` flags. The container shares the host network directly, so open [http://127.0.0.1:3782](http://127.0.0.1:3782) (or the `frontend_port` in `system.json`), and host services can be reached with normal localhost URLs like `http://127.0.0.1:11434/v1`. Note that host networking exposes container ports directly on the host and may conflict with existing services.

</details>

### Code Execution Sandbox (office skills)

The built-in office skills — **docx / pdf / pptx / xlsx** — work by having the
model write a short Python script (`python-docx`, `reportlab`, `openpyxl`, …),
run it through the `exec` / `code_execution` tools, and hand back a download URL.
Those tools mount whenever a sandbox backend is active, which it is **by default**
in every deployment shape:

- **Local (Option 1 / 2) and Docker (Option 3, single container):** a restricted
  subprocess sandbox runs the model's code (on the host locally, or inside the
  container under Docker — the container being its own isolation boundary).
- **docker-compose:** routed instead to a hardened, least-privileged **runner
  sidecar** (`Dockerfile.runner`) via `DEEPTUTOR_SANDBOX_RUNNER_URL` — the
  strongest posture, and preferred automatically when present.

The subprocess sandbox is controlled by the `sandbox_allow_subprocess` setting in
`data/user/settings/system.json` (default `true`). Running model-generated code
on your host is a real trust decision — set it to `false` (or export
`DEEPTUTOR_SANDBOX_ALLOW_SUBPROCESS=0`) to disable host-side execution, at the
cost of the office skills no longer being able to produce files.

### Option 4 — CLI Only

When you don't need the Web UI. The CLI-only package is installed from a source checkout, not from PyPI.

```bash
git clone https://github.com/HKUDS/DeepTutor.git
cd DeepTutor

# Create a venv (macOS/Linux). Windows PowerShell:
#   py -3.11 -m venv .venv-cli ; .\.venv-cli\Scripts\Activate.ps1
python3 -m venv .venv-cli && source .venv-cli/bin/activate
python -m pip install --upgrade pip

python -m pip install -e ./packaging/deeptutor-cli
deeptutor init --cli
deeptutor chat
```

`deeptutor init --cli` shares the same `data/user/settings/` layout as the full app but skips the backend/frontend port prompts and defaults embeddings to **off** (choose `Yes` if you plan to use `deeptutor kb …` or RAG tools). It still writes a complete runtime layout (`system.json`, `auth.json`, `integrations.json`, `model_catalog.json`, `main.yaml`, `agents.yaml`) and still prompts for the active LLM provider and model.

<details>
<summary><b>Common commands</b></summary>

```bash
deeptutor chat                                          # interactive REPL
deeptutor chat --capability deep_solve --tool rag --kb my-kb
deeptutor run chat "Explain Fourier transform"
deeptutor run deep_solve "Solve x^2 = 4" --tool rag --kb my-kb
deeptutor kb create my-kb --doc textbook.pdf
deeptutor memory show
deeptutor config show
```

</details>

The local `deeptutor-cli` install ships no Web assets or server dependencies. Keep the source checkout around — the editable install points to it. To add the Web app later, install the PyPI package (Option 1) and run `deeptutor init` + `deeptutor start` from the same workspace.

### Configuration Reference

<details>
<summary><b>Config files under <code>data/user/settings/</code></b> — JSON/YAML reference</summary>

Everything under `data/user/settings/` is plain JSON/YAML. The **Settings** page in the browser is the recommended editor.

| File | Purpose |
|:---|:---|
| `model_catalog.json` | LLM, embedding, and search provider profiles; API keys; active models |
| `system.json` | Backend/frontend ports, public API base, CORS, SSL verification, attachment directory |
| `auth.json` | Optional auth toggle, username, password hash, token/cookie settings |
| `integrations.json` | Optional PocketBase and sidecar integration settings |
| `interface.json` | UI language / theme / sidebar preferences |
| `main.yaml` | Runtime behavior defaults and path injection |
| `agents.yaml` | Capability/tool temperature and token settings |

Project-root `.env` is **not** read as an application config file. For a minimal model setup, open **Settings → Models**, add an LLM profile (Base URL / API key / model name), and save. Add an embedding profile only if you plan to use Knowledge Base / RAG features.

</details>

## 📖 Explore DeepTutor

The README tour follows the product surfaces in the order you will most often meet them: Chat, Partner, Co-Writer, Book, Knowledge, Space, Memory, and Settings. The screenshots below come from the reorganized `assets/figs` tree; archived legacy images are intentionally not used here.

### 💬 Chat — The Agent Loop You Actually Use

<div align="center">
<img src="assets/figs/webui/chat.png" alt="DeepTutor chat workspace" width="900">
</div>

Chat is the default capability and the place where most work begins. A single thread can talk normally, call tools, ground itself in selected knowledge bases, read attachments, write notebook records, and continue with the same source inventory across turns.

<div align="center">
<img src="assets/figs/system/chat-agent-loop.png" alt="DeepTutor chat agent loop" width="900">
</div>

The current loop is deliberately simple: the model thinks in rounds, calls tools when useful, observes the tool results, and finishes when it has enough evidence. User-toggleable tools are `brainstorm`, `web_search`, `paper_search`, and `reason`; contextual tools such as `rag`, `read_source`, `read_memory`, `write_memory`, `read_skill`, `load_tools`, `exec`, `web_fetch`, `ask_user`, `list_notebook`, `write_note`, and `github` mount when the turn has the right context.

Chat is also the launch point for deeper capabilities: `deep_solve` for worked reasoning, `deep_question` for question generation, `deep_research` for cited reports, `visualize` and `math_animator` for visual outputs, `auto` for routing, and `mastery_path` for learning-plan flows.

### 🤝 Partner — Persistent Companions on the Same Brain

<div align="center">
<img src="assets/figs/webui/partners.png" alt="DeepTutor partners workspace" width="900">
</div>

Partners replace the older TutorBot engine with a cleaner model: every inbound web or IM message becomes a normal ChatOrchestrator turn inside a partner-scoped workspace. There is no separate bot brain to keep in sync.

<div align="center">
<img src="assets/figs/system/partners-architecture.png" alt="DeepTutor partners architecture" width="900">
</div>

Each partner has a `SOUL.md`, model selection, channels, tool policy, and assigned library. Knowledge bases, skills, and notebooks are copied into `data/partners/<id>/workspace/`, so the same RAG, skill, notebook, and memory tools work without special cases.

<div align="center">
<img src="assets/figs/webui/partners02.png" alt="DeepTutor partner detail view" width="900">
</div>

The channel layer is schema-driven and can connect to IM platforms such as Feishu, Telegram, Slack, DingTalk, QQ/Napcat, WeCom, WhatsApp, Zulip, Matrix, and Microsoft Teams depending on installed extras and configured credentials.

### ✍️ Co-Writer — Selection-Aware Markdown Drafting

Co-Writer is a split-view Markdown workspace for reports, tutorials, notes, and long-form learning artifacts. Documents autosave, render a live preview, and can be saved back into notebooks when the draft becomes reusable context.

Select text and ask DeepTutor to rewrite, expand, or shorten it. The edit agent keeps a trace of tool calls and can ground an edit in a knowledge base or web evidence, so Co-Writer behaves more like an editor with retrieval than a detached text box.

### 📖 Book — Living Books from Your Materials

<p align="center">
<img src="assets/figs/webui/book01.png" alt="DeepTutor book reading view" width="31%">
&nbsp;
<img src="assets/figs/webui/book02.png" alt="DeepTutor book interactive block view" width="31%">
&nbsp;
<img src="assets/figs/webui/book03.png" alt="DeepTutor book creation view" width="31%">
</p>

Book turns selected sources into interactive learning material. A book can start from knowledge bases, notebooks, question banks, or chat history; the creation flow proposes a structure before content is generated, so users can review the shape instead of accepting a blind one-shot output.

The BookEngine compiles pages into typed blocks: text, sections, callouts, quizzes, flash cards, timelines, code, figures, interactive HTML, animations, concept graphs, deep dives, and user notes. Maintenance commands such as `deeptutor book health` and `deeptutor book refresh-fingerprints` help detect when source knowledge has drifted from compiled pages.

### 📚 Knowledge — Versioned RAG Libraries

<div align="center">
<img src="assets/figs/webui/knowledge.png" alt="DeepTutor knowledge base workspace" width="900">
</div>

Knowledge Bases are the document collections behind RAG. The current stack is LlamaIndex-only, with a flat `version-N` storage layout keyed by embedding signature. Re-indexing preserves prior versions and avoids clobbering a working index while new documents are processed.

The web workspace exposes files, upload, index versions, and settings. The CLI mirrors the same lifecycle with `deeptutor kb list`, `info`, `create`, `add`, `search`, `set-default`, and `delete`.

### 🌐 Space — Skills, Personas, and Reusable Context

<div align="center">
<img src="assets/figs/webui/space.png" alt="DeepTutor space workspace" width="900">
</div>

Space is the library layer for reusable context. It brings together user-authored skills, personas, notebooks, chat history, and question-bank style assets so the agent can be steered with deliberate context instead of ad hoc prompting.

Skills are stored as `SKILL.md` files under the user workspace and can be tagged, edited, or kept read-only when they are built in. Personas follow the same idea for role and voice. These assets can be assigned to partners, referenced in chat, and reused across learning workflows.

### 🧠 Memory — Inspectable Personalization

<div align="center">
<img src="assets/figs/webui/memory01.png" alt="DeepTutor memory workbench" width="900">
</div>

Memory is a three-layer system rooted in the active user workspace: `trace/<surface>/<date>.jsonl` for L1 event traces, `L2/<surface>.md` for per-surface facts, and `L3/<recent|profile|scope|preferences>.md` for cross-surface synthesis.

<div align="center">
<img src="assets/figs/webui/memory02.png" alt="DeepTutor memory graph" width="900">
</div>

The supported memory surfaces are `chat`, `notebook`, `quiz`, `kb`, `book`, `tutorbot`, and `cowriter`. The legacy `tutorbot` surface name remains in the memory layer for compatibility even though the product-facing companion model is now Partners. The workbench lets you inspect, edit, run consolidation, and use the graph to trace synthesized claims back to their supporting facts and raw events.

### ⚙️ Settings — One Control Plane

<div align="center">
<img src="assets/figs/webui/settings.png" alt="DeepTutor settings workspace" width="900">
</div>

Settings is the operational control plane. It covers appearance, network ports and external API base, LLM and embedding catalogs, search providers, MinerU parsing, capability budgets, memory cadence, MCP servers, built-in tools, and the enabled optional tool list.

Most settings use a draft-and-apply flow so users can test providers before committing them. Project-root `.env` files are intentionally ignored; runtime configuration lives under `data/user/settings/*.json` unless `DEEPTUTOR_HOME` or `deeptutor start --home` points the app elsewhere.

---

## ⌨️ DeepTutor CLI — Agent-Native Interface

DeepTutor is CLI-native: the same `deeptutor` entry point can initialize a workspace, start the web app, run a one-shot capability, open an interactive REPL, manage knowledge bases, inspect sessions, maintain books, and operate partners.

```bash
deeptutor run chat "Explain Fourier transform" --tool rag --kb textbook
deeptutor run deep_solve "Solve x^2 = 4" --tool reason
deeptutor chat --capability deep_research --kb papers
deeptutor partner create math-tutor --soul "Socratic math tutor"
deeptutor kb create calculus --doc textbook.pdf
```

<details>
<summary><b>Command reference</b></summary>

| Command | Description |
|:---|:---|
| `deeptutor init` | Create or update `data/user/settings` for the current workspace |
| `deeptutor start [--home PATH]` | Launch backend + frontend together |
| `deeptutor serve [--port PORT]` | Start only the FastAPI backend |
| `deeptutor run <capability> <message>` | Run a single capability turn (`chat`, `deep_solve`, `deep_question`, `deep_research`, `visualize`, `math_animator`, `auto`, `mastery_path`) |
| `deeptutor chat` | Interactive REPL with capability, tool, KB, notebook, and history controls |
| `deeptutor partner list/create/start/stop` | Manage IM-connected partners |
| `deeptutor kb list/info/create/add/search/set-default/delete` | Manage LlamaIndex knowledge bases |
| `deeptutor memory show/clear` | Inspect L2/L3 memory docs or clear L1/all memory |
| `deeptutor session list/show/open/rename/delete` | Manage shared sessions |
| `deeptutor notebook list/create/show/add-md/replace-md/remove-record` | Manage notebooks from Markdown files |
| `deeptutor book list/health/refresh-fingerprints` | Inspect books and refresh source fingerprints |
| `deeptutor plugin list/info` | Inspect registered tools and capabilities |
| `deeptutor config show` | Print configuration summary |
| `deeptutor provider login <provider>` | Manage provider OAuth login where supported |

</details>

The CLI-only distribution is present in `packaging/deeptutor-cli`; in this checkout it should be installed from source with `python -m pip install -e ./packaging/deeptutor-cli`. The public `deeptutor-cli` package is not currently available on PyPI, so the main Get Started section keeps the source-install path.

---

## 👥 Multi-User — Shared Deployments

<div align="center">
<img src="assets/figs/webui/multi-user.png" alt="DeepTutor multi-user admin workspace" width="900">
</div>

Authentication is optional and off by default. When enabled, DeepTutor becomes a shared deployment with one admin workspace, per-user workspaces, partner workspaces, and system state under one `data/` tree.

```text
data/
├── user/                         # Admin workspace and settings
├── users/<uid>/                  # Non-admin user scope
│   ├── user/chat_history.db
│   ├── user/settings/interface.json
│   ├── user/workspace/{chat,co-writer,book,memory,notebook,...}
│   └── knowledge_bases/...
├── partners/<id>/workspace/      # Partner synthetic-user scope
└── system/
    ├── auth/users.json
    ├── grants/<uid>.json
    └── audit/usage.jsonl
```

The first registered user becomes admin and can configure model catalogs, provider credentials, knowledge bases, skills, and user grants. Non-admin users get isolated chat history, memory, notebooks, personal knowledge bases, and a redacted Settings page; admin-assigned resources appear as scoped, read-only options rather than exposing API keys or provider internals.

For a local trial, set `data/user/settings/auth.json` to enable auth, restart `deeptutor start`, register the first admin at `/register`, then create users from `/admin/users` and assign models, KBs, skills, tool policy, MCP policy, and code-execution access through grants.

PocketBase mode remains a single-user integration in this tree; multi-user deployments should keep `integrations.pocketbase_url` blank and use the default JSON/SQLite auth and session stores unless an external user store has been explicitly designed for the deployment.

---
## 🌐 Community & Ecosystem

DeepTutor stands on the shoulders of outstanding open-source projects:

| Project | Role in DeepTutor |
|:---|:---|
| [**nanobot**](https://github.com/HKUDS/nanobot) | Ultra-lightweight agent engine that powered the original TutorBot (Partners now run on DeepTutor's chat agent loop) |
| [**LlamaIndex**](https://github.com/run-llama/llama_index) | RAG pipeline and document indexing backbone |
| [**ManimCat**](https://github.com/Wing900/ManimCat) | AI-driven math animation generation for Math Animator |

**From the HKUDS ecosystem:**

| [⚡ LightRAG](https://github.com/HKUDS/LightRAG) | [🤖 AutoAgent](https://github.com/HKUDS/AutoAgent) | [🔬 AI-Researcher](https://github.com/HKUDS/AI-Researcher) | [🧬 nanobot](https://github.com/HKUDS/nanobot) |
|:---:|:---:|:---:|:---:|
| Simple & Fast RAG | Zero-Code Agent Framework | Automated Research | Ultra-Lightweight AI Agent |


## 🤝 Contributing

<div align="center">

We hope DeepTutor becomes a gift for the community. 🎁

<a href="https://github.com/HKUDS/DeepTutor/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=HKUDS/DeepTutor&max=999" alt="Contributors" />
</a>

</div>

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on setting up your development environment, code standards, and pull request workflow.

## ⭐ Star History

<div align="center">

<a href="https://www.star-history.com/#HKUDS/DeepTutor&type=timeline&legend=top-left">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=HKUDS/DeepTutor&type=timeline&theme=dark&legend=top-left" />
    <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=HKUDS/DeepTutor&type=timeline&legend=top-left" />
    <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=HKUDS/DeepTutor&type=timeline&legend=top-left" />
  </picture>
</a>

</div>

<p align="center">
 <a href="https://www.star-history.com/hkuds/deeptutor">
  <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/badge?repo=HKUDS/DeepTutor&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/badge?repo=HKUDS/DeepTutor" />
   <img alt="Star History Rank" src="https://api.star-history.com/badge?repo=HKUDS/DeepTutor" />
  </picture>
 </a>
</p>

<div align="center">

**[Data Intelligence Lab @ HKU](https://github.com/HKUDS)**

[⭐ Star us](https://github.com/HKUDS/DeepTutor/stargazers) · [🐛 Report a bug](https://github.com/HKUDS/DeepTutor/issues) · [💬 Discussions](https://github.com/HKUDS/DeepTutor/discussions)

---

Licensed under the [Apache License 2.0](LICENSE).

<p>
  <img src="https://visitor-badge.laobi.icu/badge?page_id=HKUDS.DeepTutor&style=for-the-badge&color=00d4ff" alt="Views">
</p>

</div>
