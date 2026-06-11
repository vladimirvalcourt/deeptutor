---
title: Explore TutorBot
description: TutorBot — persistent, multi-channel autonomous tutors. Architecture, lifecycle, keep-alive strategies, and a dedicated page per gateway.
---

A **TutorBot** is a persistent, autonomous AI tutor that lives in DeepTutor and connects to one or more **external chat gateways** (Telegram, Slack, Feishu, etc.) so your users can interact with it from wherever they already are.

This section is the operator's guide: how the system works, how to keep bots alive, and a **dedicated page for every gateway** with registration steps, config keys, and troubleshooting.

## Architecture in one diagram

```text
┌─────────────────────────────────────────────────────────────────────┐
│                          DeepTutor server                           │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                      Bot orchestrator                       │    │
│  │   (agent loop powered by nanobot reasoning engine)          │    │
│  └──────────┬──────────────────────────────────────────────────┘    │
│             │                                                       │
│   ┌─────────┼─────────┐                                             │
│   ▼         ▼         ▼                                             │
│ ┌───┐    ┌─────┐   ┌───────┐   each bot is its own asyncio task     │
│ │bot│    │ bot │   │  bot  │   isolated workspace at                │
│ │ A │    │  B  │   │   C   │   data/tutorbot/<bot_id>/              │
│ └─┬─┘    └──┬──┘   └───┬───┘                                        │
│   │         │          │                                            │
│   │ ┌───────┼──────────┼───────────────────────────────────┐        │
│   ▼ ▼       ▼          ▼                                   ▼        │
│  ┌──────────────────────────────────────────────────┐               │
│  │             Channel registry (12 gateways)        │              │
│  └──────────────────────────────────────────────────┘               │
└────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┬──┬──┬───┘
     │     │     │     │     │     │     │     │     │     │  │  │
     ▼     ▼     ▼     ▼     ▼     ▼     ▼     ▼     ▼     ▼  ▼  ▼
   Telegram Discord Slack Matrix Zulip Feishu WeCom DingTalk QQ WA Email Mochat
```

Key properties:

- **One process** — Bots run as asyncio tasks inside the DeepTutor server. No separate process, no docker sidecar, no systemd unit per bot.
- **Many gateways per bot** — One bot can speak on Telegram **and** Slack **and** Matrix simultaneously.
- **Isolated workspaces** — Each bot has its own `agents.yaml`, soul template, skills, cron jobs, and local sessions database under `data/tutorbot/<bot_id>/`.
- **Shared memory** — All bots see the same user's L3 memory (`data/memory/L3/`), with per-channel L1 trace for source separation.
- **No restart required for channel reconnects** — Channel-level disconnects (e.g., transient network blip) auto-recover.

## Lifecycle

```bash
# Create
deeptutor bot create my-math-tutor \
  --name "Math Mentor" \
  --persona "Socratic tutor specializing in calculus and linear algebra" \
  --model gpt-4o

# Configure channels (edit data/tutorbot/my-math-tutor/agents.yaml)

# Start (forks into asyncio tasks for each enabled channel)
deeptutor bot start my-math-tutor

# Stop
deeptutor bot stop my-math-tutor

# List
deeptutor bot list
```

To delete a bot: stop it first, then remove its workspace directory at `data/tutorbot/<bot_id>/`.

You can also start/stop bots from the **`/agents`** Web UI route.

## Keeping bots alive

TutorBots live inside the DeepTutor server process. So **the question of "keeping the bot alive" reduces to "keeping the server alive"**.

| Deployment | How to keep it up |
|------------|-------------------|
| Local development | Just run `deeptutor start` in a terminal. Ctrl+C stops everything. |
| Docker | `docker compose up -d` (restart policy is `unless-stopped`). Auto-recovers on host reboot. |
| systemd / bare metal | Wrap `deeptutor serve` in a unit file. See [example below](#systemd-unit-example). |
| Kubernetes | Standard Deployment with a liveness probe on `/api/v1/system/info`. |

### systemd unit example

```ini
# /etc/systemd/system/deeptutor.service
[Unit]
Description=DeepTutor
After=network.target

[Service]
Type=simple
User=deeptutor
Group=deeptutor
WorkingDirectory=/opt/deeptutor
EnvironmentFile=/opt/deeptutor/.env
ExecStart=/opt/deeptutor/.venv/bin/deeptutor start
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable deeptutor
sudo systemctl start deeptutor
sudo journalctl -fu deeptutor      # follow logs
```

### Per-bot health monitoring

Bot status surfaces in two places:

- **`deeptutor bot list`** — shows running / stopped state for every bot
- **The Web UI's `/agents` page** — per-bot status panel with per-channel connection state

Channels report a heartbeat to the orchestrator internally; the Heartbeat system also drives proactive check-ins and scheduled tasks. If a channel goes offline for more than a few minutes, check the channel-specific page below for that gateway.

## The 12 supported gateways

Each gateway has its own dedicated page below with **registration**, **config keys**, **launch**, and **keep-alive specifics**:

| Gateway | Status | Connection model | Page |
|---------|--------|------------------|------|
| Telegram | ✅ Stable | Polling | [**Telegram**](/docs/tutorbot/telegram/) |
| Discord | ✅ Stable | WebSocket Gateway | [**Discord**](/docs/tutorbot/discord/) |
| Slack | ✅ Stable | Socket Mode | [**Slack**](/docs/tutorbot/slack/) |
| Matrix | ✅ Stable | HTTP Sync | [**Matrix**](/docs/tutorbot/matrix/) |
| Zulip | ✅ v1.3.9+ | Event Queue | [**Zulip**](/docs/tutorbot/zulip/) |
| Feishu (飞书) / Lark | ✅ Stable | WebSocket | [**Feishu**](/docs/tutorbot/feishu/) |
| WeCom (企业微信) | ✅ Stable | WebSocket | [**WeCom**](/docs/tutorbot/wecom/) |
| DingTalk (钉钉) | ✅ Stable | Stream Mode | [**DingTalk**](/docs/tutorbot/dingtalk/) |
| QQ | ✅ Stable | WebSocket | [**QQ**](/docs/tutorbot/qq/) |
| WhatsApp | ⚠️ Via Node.js bridge | WebSocket to bridge | [**WhatsApp**](/docs/tutorbot/whatsapp/) |
| Email | ✅ Stable | IMAP poll + SMTP | [**Email**](/docs/tutorbot/email/) |
| Mochat | ✅ Stable | Socket.IO / HTTP poll | [**Mochat**](/docs/tutorbot/mochat/) |

## Universal config shape

Every gateway uses the same outer schema in the bot's `agents.yaml`:

```yaml
agent:
  id: my-math-tutor
  name: Math Mentor
  persona: "Socratic tutor specializing in calculus..."
  model: gpt-4o

channels:
  telegram:
    enabled: true
    token: "..."
    allow_from: ["*"]

  slack:
    enabled: true
    bot_token: "xoxb-..."
    app_token: "xapp-..."
    reply_in_thread: true

  email:
    enabled: false
    # ... per-gateway fields
```

**Common fields** across all gateways:

| Field | Type | Required | Effect |
|-------|------|----------|--------|
| `enabled` | bool | yes | Whether to start this channel |
| `allow_from` | list[string] | yes | User-id / email allowlist (`["*"]` = open, `[]` = deny all) |
| `group_policy` | `"mention"` \| `"open"` | optional | For group chats: only respond to mentions vs every message |

Per-gateway fields are documented on their dedicated pages.

## Bot capabilities

Inside a bot conversation, the bot has access to:

- The same **seven capabilities** as the Web UI (Chat, Deep Solve, Quiz, Research, Animator, Visualize, Auto)
- All **tools** (RAG, web search, code execution, reasoning, paper search, etc.)
- **Attached Knowledge Bases** (configurable per-bot)
- **Skills** — reusable system-prompt fragments
- **Cron jobs** — scheduled tasks (e.g., "send a daily summary at 9 AM")
- **Memory** — L3 cross-surface profile

This means a TutorBot on Telegram can do everything you can do in the Web UI — research, quiz generation, code execution, etc. — without the user ever leaving Telegram.

## When to use TutorBot vs Web UI

| Use case | Surface |
|----------|---------|
| Solo deep-dive learning | Web UI |
| Quick on-the-go questions | TutorBot on Telegram / Slack |
| Team Q&A in a shared channel | TutorBot on Feishu / Slack / Discord channel |
| Async help via email | TutorBot on Email |
| Scheduled daily nudges / digests | TutorBot with cron jobs |
| Programmatic integration | DeepTutor [CLI](/docs/cli/) or [API](/docs/cli/server-api/) |

## Where state lives

```text
data/
├── tutorbot/
│   ├── my-math-tutor/
│   │   ├── agents.yaml           # Channels + persona
│   │   ├── souls/                # Soul / personality templates
│   │   ├── skills/               # User-authored skill fragments
│   │   ├── cron/                 # Scheduled task definitions
│   │   ├── media/                # Cached inbound/outbound attachments
│   │   ├── logs/                 # Per-bot logs
│   │   └── sessions.db           # Local chat session cache
│   └── helpdesk-bot/
│       └── ...
└── memory/                        # Shared across all bots + Web UI
    ├── L1/
    ├── L2/
    └── L3/
```

## Required Python extras

Bots require the `[tutorbot]` extra (or the equivalent in `packaging/deeptutor-cli`):

```bash
# Full server + TutorBot
pip install -e ".[partners]"

# CLI-only + TutorBot
pip install -e "./packaging/deeptutor-cli[tutorbot]"

# From PyPI (already includes tutorbot)
pip install deeptutor
```

Some specific gateways need extra system dependencies:

| Gateway | Extra needed |
|---------|--------------|
| Matrix (E2EE) | `[matrix-e2e]` + libolm system library |
| WhatsApp | Separate Node.js bridge (not Python) |

Check each gateway's page for details.

## Common patterns

### Pattern: study group on Slack

1. Create a bot: `deeptutor bot create study-helper --persona "Patient study group facilitator"`
2. Enable Slack with `group_policy: "mention"` so it only responds when @mentioned
3. Attach the course KB to the bot's config
4. Invite the bot to a Slack channel
5. Students ask questions — the bot retrieves from the KB and answers, citing sources

### Pattern: solo TG tutor

1. `deeptutor bot create my-tutor --persona "Personal calculus tutor"`
2. Enable Telegram with `allow_from: ["123456789"]` (your TG user id)
3. Optional cron: "every weekday at 8 AM, ask me what I want to work on today"
4. Chat normally on Telegram — gets the same memory / context as Web UI

### Pattern: enterprise helpdesk on Feishu

1. `deeptutor bot create helpdesk --persona "Friendly first-line IT helpdesk"`
2. Attach the internal docs KB
3. Enable Feishu with `group_policy: "open"` in the help channel, `mention` everywhere else
4. Configure `allow_from` to your org's verified user list

## See also

- [**DeepTutor CLI → bot**](/docs/cli/commands/#deeptutor-bot--tutorbot-lifecycle) — lifecycle commands
- [**Memory**](/docs/explore/memory/) — how bots share user memory
- Any gateway page above for setup details
