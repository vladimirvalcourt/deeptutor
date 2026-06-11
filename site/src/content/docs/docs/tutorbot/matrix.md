---
title: Matrix
description: TutorBot on Matrix — decentralized chat, with optional end-to-end encryption.
---

Matrix is the decentralized chat option. DeepTutor talks to any Matrix homeserver (matrix.org, your self-hosted Synapse, Conduit, Dendrite) via the standard client-server API.

End-to-end encryption is **optional** and split into its own install extra so most users don't pay the libolm dependency cost.

## What you need

- A Matrix account (on matrix.org or any homeserver)
- The bot's `access_token` from that account
- *(For E2EE)* `libolm` installed on your system

## Step 1 — Create a Matrix account for the bot

The bot needs its own Matrix account. Use any homeserver:

- **Public**: Element web app → matrix.org → Create Account
- **Self-hosted**: `register_new_matrix_user` (Synapse) or the equivalent for your server

For testing, matrix.org's public homeserver is fine.

## Step 2 — Get the access token

### Option A — From Element

1. Sign into Element as the bot user
2. **Settings** → **Help & About** → scroll to **Advanced**
3. Reveal **Access Token** and copy it

### Option B — From the REST API

```bash
curl -X POST https://matrix.org/_matrix/client/r0/login \
  -H "Content-Type: application/json" \
  -d '{
    "type": "m.login.password",
    "user": "math-bot",
    "password": "your-password"
  }'

# Response includes "access_token": "syt_..."
```

## Step 3 — Configure

```yaml
channels:
  matrix:
    enabled: true
    homeserver: "https://matrix.org"   # or your self-hosted URL
    user_id: "@math-bot:matrix.org"
    access_token: "syt_xxxxxxxxxxxxxxxxxxxx"
    encryption_enabled: false           # set true after installing matrix-e2e extra
    allow_from: []                      # empty = anyone in joined rooms can talk to bot
    rooms: []                           # specific room ids the bot should join, or [] = listen everywhere
```

## Step 4 — Install dependencies

Matrix support is in an optional install extra. Three layers:

| Goal | Install |
|------|---------|
| Base Matrix (no E2EE) | `pip install -e ".[matrix]"` |
| Matrix with E2EE | `pip install -e ".[matrix-e2e]"` *(also needs libolm)* |
| All Partners gateways including Matrix | `pip install -e ".[partners]"` |

For E2EE, install **libolm** first:

```bash
# macOS
brew install libolm

# Debian / Ubuntu
sudo apt install libolm-dev

# Then the Python extra
pip install -e ".[matrix-e2e]"
```

## Step 5 — Start

```bash
deeptutor bot start my-math-tutor
```

```text
[bot:my-math-tutor] channel:matrix → connecting (homeserver=matrix.org)
[bot:my-math-tutor] channel:matrix → sync ok (next_batch=...)
[bot:my-math-tutor] channel:matrix → joined 3 rooms
```

## Inviting the bot to a room

Once the bot is running, invite it from any Matrix client:

```text
/invite @math-bot:matrix.org
```

The bot auto-accepts invitations and starts listening for messages in that room. To restrict which rooms the bot joins:

```yaml
channels:
  matrix:
    rooms:
      - "!abc123:matrix.org"     # only auto-join these specific rooms
```

## Config reference

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| `enabled` | bool | yes | `false` | |
| `homeserver` | url | yes | — | e.g., `https://matrix.org` |
| `user_id` | string | yes | — | `@bot:matrix.org` |
| `access_token` | string | yes | — | From login or Element |
| `encryption_enabled` | bool | optional | `false` | Requires `[matrix-e2e]` extra + libolm |
| `allow_from` | list[string] | optional | `[]` | Matrix user ids; `[]` = anyone in joined rooms |
| `rooms` | list[string] | optional | `[]` | Specific room ids; `[]` = listen in any room the bot is in |

## Capabilities on Matrix

| Feature | Supported |
|---------|-----------|
| Direct (1:1) chat | ✅ |
| Group rooms | ✅ |
| Markdown → HTML | ✅ *(rendered correctly in Element, Cinny, etc.)* |
| LaTeX math | ⚠️ requires `mathjs` client plugin in your Matrix client |
| File uploads | ✅ |
| File downloads | ✅ |
| End-to-end encryption | ✅ *(opt-in)* |
| Typing indicators | ✅ |
| Reactions | ⚠️ outbound only |

## End-to-end encryption

Once `encryption_enabled: true` + libolm + `[matrix-e2e]` extra:

- The bot generates its own device key on first launch
- For each E2EE room, the bot participates in key exchange via Megolm
- All messages are end-to-end encrypted including attachments

**Caveat**: the bot's reasoning still happens server-side in DeepTutor. The encryption is between the Matrix client (user) and the bot's Matrix process, but the message text reaches the LLM provider unencrypted (unless you've configured a local LLM).

If end-to-end-to-LLM privacy matters, use a local Ollama / vLLM with the bot.

## Keep-alive specifics

The Matrix channel uses the **`/sync` long-poll endpoint** with a 30-second timeout. The pattern:

1. Open `/sync?since=<last_batch>` with timeout=30000
2. Receive new events (or empty response after 30s)
3. Update `last_batch`, immediately re-poll

On disconnect:

- Network drops are transparent — the next `/sync` retries
- Auth errors (401) require manual intervention (token expired or invalidated)

For high uptime, run the DeepTutor server under a process supervisor (systemd, docker restart-policy). The channel itself handles transient failures.

## Common issues

### `M_UNKNOWN_TOKEN`

Your `access_token` was invalidated (logged out from another client, or the server rotated keys). Get a fresh token via Element settings or the REST login.

### Bot joins but doesn't respond in E2EE rooms

You enabled `encryption_enabled: true` without installing `[matrix-e2e]` extra. The bot connects but can't decrypt — install libolm + reinstall.

### Federation lag

If your bot is on `matrix.org` and you're chatting on a small self-hosted server, messages can take a few seconds to federate. Not a bug — federation latency.

### "User not in room" error sending replies

The bot was kicked or left the room. Re-invite from your Matrix client.

## See also

- [**Explore TutorBot**](/docs/tutorbot/) — overall architecture
- [Matrix specification](https://spec.matrix.org/) — the underlying protocol
