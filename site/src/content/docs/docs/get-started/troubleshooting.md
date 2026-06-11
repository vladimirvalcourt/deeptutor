---
title: Troubleshooting
description: Common errors across install paths, with copy-pasteable fixes.
---

If your install isn't behaving, find your symptom below. Errors are grouped by category. The fixes are tested against the current `main` branch.

## Ports and processes

### `Address already in use :3782` (or :8001)

Something else is bound to the port. Find it:

```bash
# macOS
lsof -i :3782

# Linux
ss -ltnp | grep :3782

# Windows PowerShell
Get-NetTCPConnection -LocalPort 3782
```

Kill it, or change the DeepTutor port by re-running the setup wizard or editing `data/user/settings/system.json`:

```bash
deeptutor init
```

```json
{
  "backend_port": 18001,
  "frontend_port": 4000
}
```

For a one-off process override, export environment variables in the shell before starting DeepTutor: `BACKEND_PORT=18001 FRONTEND_PORT=4000 deeptutor start`.

If you're using Docker, override the docker-specific ports instead:

```bash
DEEPTUTOR_DOCKER_FRONTEND_PORT=4000
DEEPTUTOR_DOCKER_BACKEND_PORT=18001
```

### Backend starts but frontend can't reach it

When you serve DeepTutor under a different hostname (cloud deployment, LAN
access, reverse proxy), the browser needs a backend URL it can reach.

Fix: open **Settings -> Network** or set `next_public_api_base_external` in
`data/user/settings/system.json` to the externally-reachable backend URL:

```json
{
  "next_public_api_base_external": "https://deeptutor.example.com:8001"
}
```

Then restart DeepTutor. `public_api_base` is accepted as a compatibility alias
and normalized into `next_public_api_base_external` on save.

If auth is enabled and the frontend origin differs from the API origin, also
set exact CORS origins:

```json
{
  "cors_origins": ["https://deeptutor.example.com"]
}
```

## LLM / Embedding providers

### `HTTPError 401 Unauthorized` during provider probe

The provider rejected your API key. Common gotchas:

- **OpenAI**: starts with `sk-` (project keys start with `sk-proj-`)
- **Anthropic**: starts with `sk-ant-`
- **Azure OpenAI**: also requires `LLM_API_VERSION` (set in Settings → LLM)
- **Google Gemini**: starts with `AIza`
- **Ollama / local OpenAI-compatible**: leave the API key blank or use `none`, set the base URL like `http://localhost:11434/v1`

Re-run `deeptutor init` to re-enter the key, or edit `data/user/settings/model_catalog.json` directly.

### `Failed to fetch /models` during setup

DeepTutor pings the provider's model-list endpoint to populate the model dropdown. If your network blocks it, you'll see this warning — it's **non-fatal**. The wizard falls back to a hardcoded list of common models and continues.

### `host.docker.internal` not resolving (Docker + local Ollama)

| Host OS | Use |
|---------|-----|
| macOS, Windows | `http://host.docker.internal:11434/v1` |
| Linux | `http://172.17.0.1:11434/v1` *(docker0 bridge)* or the host's LAN IP |

Linux users can also add `host.docker.internal` manually:

```yaml
# docker-compose.ghcr.yml
services:
  deeptutor:
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

### `Embedding dimension mismatch` when querying a KB

You re-indexed a KB with a different embedding model. The cached dimension no longer matches.

Fix: in the Web UI, navigate to **Knowledge → select KB → Index versions → Re-index now**. Re-indexing isn't exposed as a CLI command.

### Embedding endpoint URL keeps coming back wrong

Some providers expect the **full embeddings path** in `EMBEDDING_HOST`, not the API root:

| Provider | Wrong | Right |
|----------|-------|-------|
| OpenAI | `https://api.openai.com/v1` | `https://api.openai.com/v1/embeddings` |
| Cohere | `https://api.cohere.ai` | `https://api.cohere.ai/v1/embed` |
| Voyage | `https://api.voyageai.com/v1` | `https://api.voyageai.com/v1/embeddings` |

## Knowledge Bases

### KB stuck in `indexing` state

Indexing happens in a background task. Check logs:

```bash
tail -f data/user/logs/ai_tutor_*.log | grep -i kb
```

Common causes: embedding provider returned 429 (rate limit — retry with smaller batches), embedding host unreachable (check connection), or PDF parser failed (check the file isn't password-protected).

### Reindex doesn't fix dimension mismatch

If the dimension mismatch error persists after reindex, the KB store may have a stale config file. From the CLI:

```bash
deeptutor kb delete physics --force
deeptutor kb create physics --doc chapter1.pdf
```

## Multi-user

### `401 Unauthorized` on every API call after restart

`AUTH_SECRET` was regenerated, invalidating every JWT.

Fix: pin `AUTH_SECRET` in `.env` so it persists across restarts:

```bash
AUTH_SECRET=$(openssl rand -hex 32)
```

### First user wasn't promoted to admin

Edit `multi-user/_system/auth/users.json`, set `"role": "admin"` for the user, restart.

### Login works but redirects back to `/login`

The auth cookie isn't being set, usually because:

1. `AUTH_COOKIE_SECURE=true` but you're not on HTTPS — set it `false` for local testing
2. `auth.json: cookie_secure=false` on a cross-site HTTPS deployment — set it `true` and restart so the cookie uses `SameSite=None; Secure`
3. The browser blocks third-party cookies and you're on a subdomain — serve frontend and API from the same hostname (e.g., both at `deeptutor.example.com`, frontend on `/`, API proxied at `/api/`)

## Docker

### Container exits immediately

```bash
docker logs deeptutor | tail -30
```

Most common: the host folders aren't pre-created.

```bash
mkdir -p data/user data/memory data/knowledge_bases
python scripts/docker_compose.py up -d
```

### Container is `Running` but `unhealthy`

Healthcheck calls `curl http://localhost:8001/` from inside the container. If backend startup is slow (~30s for first run, downloading model metadata), the healthcheck may flap.

Wait 60 seconds. If still unhealthy, check the supervisord state:

```bash
docker exec deeptutor supervisorctl status
docker exec deeptutor tail -40 /app/data/user/logs/ai_tutor_$(date +%Y%m%d).log
```

### npm install times out during build

The Next.js dep tree is large. Bump npm's network timeout:

```bash
npm config set fetch-timeout 600000
```

The official `Dockerfile` already sets this — only matters if you're building locally.

## Python install

### `Microsoft Visual C++ 14.0 is required` (Windows)

`tiktoken`, `chroma-hnswlib`, and a couple of other deps compile C extensions on Windows. Install [**Build Tools for Visual Studio**](https://visualstudio.microsoft.com/visual-cpp-build-tools/) with the "Desktop development with C++" workload.

### `libolm not found` (Matrix E2EE only)

```bash
# macOS
brew install libolm

# Debian / Ubuntu
sudo apt install libolm-dev

# Reinstall the matrix-e2e extra
pip install -e ".[matrix-e2e]" --force-reinstall
```

### `pip install` is glacially slow

Use a local PyPI mirror or wheelhouse if you're on a slow connection. For China-based users:

```bash
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
```

### Conda environment activated but `python` still points elsewhere

PATH ordering can shadow conda's python. Verify:

```bash
which python
# /Users/you/miniconda3/envs/deeptutor/bin/python
```

If not, run `conda activate deeptutor` in a fresh shell.

## Frontend

### Frontend shows a blank page

Open the browser dev tools (⌥⌘I) and check the Console tab. Common causes:

- **CORS errors** — frontend at one origin, backend at another, and the backend isn't on the allowed-origins list. Edit `data/user/settings/system.json` and add your frontend origin to `cors_origins`.
- **404 on `/_next/...`** — the static bundle wasn't built. From source: `cd web && npm run build`.
- **Backend not reachable** — verify `curl http://localhost:8001/` returns JSON.

### "Failed to fetch" toast on every page

Same as above — usually backend isn't running or CORS / API base URL mismatch. Check the Network tab to see what URL the request goes to.

## TutorBot

### Bot says "missing SDK" on start

The gateway-specific SDK wasn't installed. The error message tells you which one. Install:

```bash
# Generic
pip install -e ".[partners]"

# Or one specific (rarely needed)
pip install python-telegram-bot   # Telegram
pip install slack-sdk              # Slack
pip install zulip                  # Zulip
pip install matrix-nio             # Matrix (no E2EE)
```

### Bot connects but doesn't respond

Check `allow_from` in the bot's channel config:

```yaml
telegram:
  enabled: true
  token: "..."
  allow_from:               # empty = deny everyone
    - "*"                    # allow all
    # - "12345678"           # or specific Telegram user IDs
```

By default `allow_from: []` denies everyone — you have to explicitly opt users in.

### Bot disconnects after a few minutes

Long-poll / WebSocket connections drop occasionally. The channel manager auto-reconnects with backoff, but if you see frequent drops:

- Check network stability between the host and the gateway provider
- For Telegram polling, increase `timeout` to 60 seconds
- For Matrix, verify the homeserver isn't aggressively timing out

See [**Explore TutorBot**](/docs/tutorbot/) for per-gateway debugging.

## Memory / RAG accuracy

### Chat ignores the attached KB

Make sure:

1. The KB is **attached** to the turn (not just listed in the picker — actually clicked into the active set)
2. The `rag` tool is **enabled** in Settings → Tools, or auto-enabled because a KB is attached
3. The KB has `status: ready` (not still indexing) — check via `deeptutor kb list`

### `read_memory` returns empty

L3 memory is empty until the consolidator has run at least once. Memory is consolidated:

- Every N turns (configurable in Settings → Memory)
- On user request via the Memory Workbench

Force a consolidation from the **Memory Workbench** (`/memory` → **Run consolidator**), or via the HTTP API:

```bash
curl -X POST http://localhost:8001/api/v1/memory/runs/start
```

### Memory writes are getting flagged as `unsafe_text`

The `write_memory` tool has a 240-char limit and content-safety filter. Trim your preference text or rephrase.

## Still stuck?

- Ask on [Discord](https://discord.gg/eRsjPgMU4t) — fastest channel
- File a bug at [github.com/HKUDS/DeepTutor/issues](https://github.com/HKUDS/DeepTutor/issues)
- Long-form question? Open a [Discussion](https://github.com/HKUDS/DeepTutor/discussions)

When asking for help, include:

- Your install path (PyPI / From Source / Docker / CLI-Only)
- Output of `deeptutor config show`
- Last 40 lines of `data/user/logs/ai_tutor_*.log`
- For Docker: `docker logs deeptutor | tail -40`
