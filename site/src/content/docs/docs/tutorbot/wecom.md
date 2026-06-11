---
title: WeCom (WeChat Work)
description: TutorBot on WeCom (企业微信) — enterprise messaging via the WebSocket AI Bot platform.
---

WeCom (企业微信 / WeChat Work) is Tencent's enterprise messaging product. DeepTutor integrates via the **AI Bot** platform with a WebSocket long-connection.

## What you need

- A WeCom organization with admin access
- The [`wecom-aibot-sdk`](https://pypi.org/project/wecom-aibot-sdk/) Python package
- 10 minutes in the WeCom admin console

## Step 1 — Install the SDK

WeCom support uses an optional Python package:

```bash
pip install wecom-aibot-sdk
```

If you started with `pip install -e ".[partners]"`, this may already be in. Verify:

```bash
python -c "import wecom_aibot_sdk; print('ok')"
```

## Step 2 — Create the AI Bot

1. Sign in to <https://work.weixin.qq.com/>
2. **Applications & Mini Programs** → **AI Bot Platform**
3. **Create New Application** → select **AI Bot** type
4. Fill in name, description, departments allowed to use it
5. Copy **Bot ID** and **Secret**

## Step 3 — Configure

```yaml
channels:
  wecom:
    enabled: true
    bot_id: "YOUR_BOT_ID"
    secret: "YOUR_SECRET"
    allow_from: []                  # optional restriction by user id
    welcome_message: "Hi! I'm your math tutor. Ask me anything."
```

## Step 4 — Start

```bash
deeptutor bot start my-math-tutor
```

```text
[bot:my-math-tutor] channel:wecom → connecting (ws://wecom...)
[bot:my-math-tutor] channel:wecom → ready
```

## Config reference

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `enabled` | bool | yes | |
| `bot_id` | string | yes | From AI Bot platform |
| `secret` | string | yes | From AI Bot platform |
| `allow_from` | list[string] | optional | WeCom user ids; `[]` allows anyone in your org |
| `welcome_message` | string | optional | Sent on first message from a new user |

## Capabilities on WeCom

| Feature | Supported |
|---------|-----------|
| Direct messages within enterprise | ✅ |
| Group chats | ✅ |
| Markdown | ✅ |
| File / image / voice | ✅ |
| External contacts (customers) | ⚠️ via WeCom's external contacts feature |
| Mention routing | ✅ |

## Keep-alive specifics

A background thread maintains the WebSocket. Reconnection is automatic on transient failures.

If the bot stays offline:

1. Check the AI Bot platform — has the bot been disabled?
2. Verify your DeepTutor server has outbound TLS access to WeCom servers
3. Restart: `deeptutor bot stop my-math-tutor && deeptutor bot start my-math-tutor`

## Common issues

### `ImportError: wecom_aibot_sdk`

```bash
pip install wecom-aibot-sdk
deeptutor bot start my-math-tutor
```

### Bot connects but doesn't respond

`allow_from` is the usual suspect. Also confirm the user sending messages is in the departments you granted access to in the AI Bot config.

### Multiple bots in same org

Each bot needs its own `bot_id` + `secret`. You can run multiple TutorBots in one DeepTutor server, each connecting to a different WeCom bot.

## See also

- [**Feishu**](/docs/tutorbot/feishu/) — ByteDance's enterprise chat platform
- [**Explore TutorBot**](/docs/tutorbot/) — overall architecture
