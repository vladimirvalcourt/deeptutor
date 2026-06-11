---
title: Multi-User Deployment
description: Flip on authentication and DeepTutor turns into a multi-tenant deployment with per-user isolated workspaces and admin-curated resources.
---

Flip on authentication and DeepTutor turns into a multi-tenant deployment with **per-user isolated workspaces** and **admin-curated resources**. The first person to register becomes the admin and configures models, API keys, and knowledge bases on behalf of everyone else. Subsequent accounts are created by the admin (invite-only), each gets their own scoped chat history / memory / notebooks / knowledge bases, and they only see the LLMs, KBs, and skills the admin assigned to them.

## Quick start (5 steps)

```bash
# 1. Enable auth in data/user/settings/auth.json:
#    {"enabled": true, "token_expire_hours": 24, "cookie_secure": false}
#    Use cookie_secure=true for HTTPS deployments where Web and API are cross-site.

# 2. Restart the web stack.
deeptutor start

# 3. Open http://localhost:3782/register and create the first account.
#    The first registration is the only public one; that user becomes admin
#    and the /register endpoint is closed automatically afterward.

# 4. As admin, navigate to /admin/users → "Add user" to provision teammates.

# 5. For each user, click the slider icon → assign LLM profiles, knowledge
#    bases, and skills. Save. The user can now sign in and start working.
```

## What the admin sees

- **Full Settings page** at `/settings` — manage LLM / embedding / search providers, API keys, model catalogs, and runtime "Apply".
- **User management** at `/admin/users` — create, promote, demote, and delete accounts. The public `/register` endpoint is automatically closed once the first admin exists; further accounts go through `POST /api/v1/auth/users` (admin-only).
- **Grant editor** — for each non-admin user, pick the LLM models, knowledge bases, and skills they may use, restrict the system tools (web search, paper search, …) and MCP tools to a whitelist, and switch code execution off entirely. Tool whitelists follow the same semantics as partner configs: *Default* allows everything, *Custom* is an explicit whitelist. Grants carry **logical IDs only**; API keys never cross the grant boundary.
- **Audit trail** — every grant change and assigned-resource access is appended to `data/system/audit/usage.jsonl`.

## What ordinary users get

- **Isolated workspace** under `data/users/<uid>/` — their own chat history (`chat_history.db`), memory, notebooks, and personal knowledge bases. Nothing is shared by default.
- **Read-only access** to admin-assigned knowledge bases and skills, surfaced inline next to their own resources with an "Assigned by admin" badge.
- **Redacted Settings page** — only theme, language, and a summary of granted models. API keys, base URLs, and provider endpoints are never returned for non-admin requests.
- **Scoped LLM** — chat turns are routed through the admin-assigned model. If no LLM is granted, the turn is rejected up-front (no silent fallback to the admin's keys).
- **Scoped tools** — the composer, the `/settings/tools` page, and every turn only expose the system tools and MCP tools inside the user's grant whitelist; code execution honors the per-user switch on top of the deployment sandbox policy.

## Workspace layout

Everything lives under `data/` — one tree to mount and back up:

```text
data/
├── user/                        # Admin workspace (settings, API keys, admin tasks)
├── system/
│   ├── auth/users.json          # Hashed credentials, roles
│   ├── auth/auth_secret         # JWT signing secret (auto-generated)
│   ├── grants/<uid>.json        # Per-user resource grants (admin-managed)
│   └── audit/usage.jsonl        # Audit trail
├── users/<uid>/
│   ├── user/
│   │   ├── chat_history.db
│   │   ├── settings/interface.json
│   │   └── workspace/{chat,co-writer,book,...}
│   ├── memory/
│   └── knowledge_bases/...
└── partners/<id>/               # Partner workspaces
```

Deployments upgraded from the pre-v1.5 layout (a sibling `multi-user/` directory next to `data/`) are migrated automatically on first start: `multi-user/_system` moves to `data/system`, each `multi-user/<uid>` to `data/users/<uid>`.

## Configuration reference

| Setting | Required | Description |
|---------|----------|-------------|
| `data/user/settings/auth.json: enabled` | Yes | Set to `true` to enable multi-user auth. Default `false` (single-user mode — admin paths everywhere). |
| `data/system/auth/auth_secret` | Recommended | JWT signing secret. Auto-generated on first authenticated boot if missing. |
| `data/user/settings/auth.json: token_expire_hours` | No | JWT lifetime; defaults to `24`. |
| `data/user/settings/auth.json: cookie_secure` | HTTPS / cross-site auth | Set `true` to use `SameSite=None; Secure` cookies. Keep `false` for local HTTP. |
| `data/user/settings/auth.json: username` / `password_hash` | No | Optional headless single-user bootstrap credential. Leave blank when using browser registration. |
| `data/user/settings/system.json` | No | `deeptutor start` derives frontend auth flags, public API base, and CORS origins from runtime settings. |

## Important caveats

> ⚠️ **PocketBase mode (`integrations.pocketbase_url` set) is single-user only.** The default PocketBase schema has no `role` field on `users` (every login resolves to `role=user`, no admin can be created), and `sessions` / `messages` / `turns` queries are not filtered by `user_id`. Multi-user deployments must keep `integrations.pocketbase_url` blank and use the default JSON/SQLite backend.

> ⚠️ **Single-process recommendation.** The first-user-becomes-admin promotion is protected by an in-process `threading.Lock`. Multi-worker deployments should provision the first admin offline (start with `auth.json.enabled=false`, register the admin via the bootstrap flow, then set `auth.json.enabled=true`) or back the user store with an external system.

## Production checklist

- ✅ Set a strong `auth_secret` and back it up
- ✅ Set `cookie_secure: true` in `auth.json` to require HTTPS for the session cookie
- ✅ Put DeepTutor behind a reverse proxy (Caddy, nginx, Traefik) with TLS termination
- ✅ Set `next_public_api_base_external` in `system.json` so the frontend bundle knows where to find the backend
- ✅ Set `cors_origins` to the exact frontend origin when auth is enabled and Web/API are cross-origin
- ✅ Back up `data/` regularly — accounts, grants, and every workspace live under this one tree
- ✅ Docker: keep the `./data:/app/data` volume from `docker-compose.yml`. The sandbox runner intentionally mounts only the workspace subtrees (`data/user/workspace`, `data/users`) — never `data/system` or `data/user/settings`, which hold auth state and API keys

## Caddyfile example

```caddyfile
deeptutor.example.com {
    reverse_proxy /api/* localhost:8001
    reverse_proxy localhost:3782
}
```

Then in `data/user/settings/system.json`:

```json
{
  "next_public_api_base_external": "https://deeptutor.example.com",
  "cors_origins": ["https://deeptutor.example.com"]
}
```

`public_api_base` is accepted as a compatibility alias and is normalized into
`next_public_api_base_external` on save.

And in `data/user/settings/auth.json`:

```json
{
  "enabled": true,
  "token_expire_hours": 24,
  "cookie_secure": true
}
```

## Common errors

### `404 /register` after enabling auth

The frontend bundle may be cached. With Docker, recreate the container. From source, restart `deeptutor start` after editing `auth.json`.

### First login works but no admin link

Confirm `data/system/auth/users.json` has `"role": "admin"` on the first user. If not, manually set it and restart.

### `Cannot decode JWT` after restart

`auth_secret` was lost or regenerated. Restore from backup, or accept the regenerated secret and ask all users to log in again.

## Headless single-user bootstrap

For automation where no human can register in a browser, set credentials directly in `auth.json`:

```json
{
  "enabled": true,
  "username": "alice",
  "password_hash": "<bcrypt-hash>",
  "token_expire_hours": 24
}
```

Generate the hash:

```python
import bcrypt
print(bcrypt.hashpw(b"your-password", bcrypt.gensalt()).decode())
```

Then `deeptutor start` and log in with `alice` + your-password.

More fixes: [**Troubleshooting**](/docs/get-started/troubleshooting/).
