---
title: Matrix
description: 在 Matrix 上跑 TutorBot —— 去中心化聊天，端到端加密可选。
---

Matrix 是去中心化聊天的选项。DeepTutor 通过标准的 client-server API 和任何 Matrix homeserver 通信（matrix.org、你自己跑的 Synapse、Conduit、Dendrite 都行）。

端到端加密是 **可选的**，独立成一个 install extra，所以大多数用户不用承担 libolm 依赖的代价。

## 你需要准备

- 一个 Matrix 账号（matrix.org 或任意 homeserver）
- 那个账号的 `access_token`
- *（如果要 E2EE）* 系统里装好 `libolm`

## Step 1 —— 给 bot 注册一个 Matrix 账号

Bot 需要自己独立的 Matrix 账号。任意 homeserver 都行：

- **公共的**：Element web 应用 → matrix.org → Create Account
- **自建**：`register_new_matrix_user`（Synapse）或对应你服务器的等价工具

测试用的话，matrix.org 的公共 homeserver 就够了。

## Step 2 —— 拿 access token

### 方案 A —— 从 Element 拿

1. 用 bot 账号登 Element
2. **Settings** → **Help & About** → 滚到 **Advanced**
3. 展开 **Access Token** 复制

### 方案 B —— 从 REST API 拿

```bash
curl -X POST https://matrix.org/_matrix/client/r0/login \
  -H "Content-Type: application/json" \
  -d '{
    "type": "m.login.password",
    "user": "math-bot",
    "password": "your-password"
  }'

# 返回里有 "access_token": "syt_..."
```

## Step 3 —— 配置

```yaml
channels:
  matrix:
    enabled: true
    homeserver: "https://matrix.org"   # 或你自建 homeserver 的 URL
    user_id: "@math-bot:matrix.org"
    access_token: "syt_xxxxxxxxxxxxxxxxxxxx"
    encryption_enabled: false           # 装了 matrix-e2e extra 后再设 true
    allow_from: []                      # 空 = bot 在加入的房间里谁都能聊
    rooms: []                           # 指定 bot 加入的 room id，或 [] = 任何房间都监听
```

## Step 4 —— 装依赖

Matrix 支持放在一个可选 install extra 里。三档：

| 目标 | 安装命令 |
|------|----------|
| 基础 Matrix（无 E2EE） | `pip install -e ".[matrix]"` |
| Matrix + E2EE | `pip install -e ".[matrix-e2e]"` *（还得装 libolm）* |
| 所有 Partners 渠道（含 Matrix） | `pip install -e ".[partners]"` |

要 E2EE 的话先装 **libolm**：

```bash
# macOS
brew install libolm

# Debian / Ubuntu
sudo apt install libolm-dev

# 然后装 Python extra
pip install -e ".[matrix-e2e]"
```

## Step 5 —— 启动

```bash
deeptutor bot start my-math-tutor
```

```text
[bot:my-math-tutor] channel:matrix → connecting (homeserver=matrix.org)
[bot:my-math-tutor] channel:matrix → sync ok (next_batch=...)
[bot:my-math-tutor] channel:matrix → joined 3 rooms
```

## 邀请 bot 进房间

Bot 跑起来之后，从任意 Matrix 客户端邀请：

```text
/invite @math-bot:matrix.org
```

Bot 会自动接受邀请并开始监听该房间的消息。要限制 bot 加入哪些房间：

```yaml
channels:
  matrix:
    rooms:
      - "!abc123:matrix.org"     # 只自动加入这些指定的房间
```

## 配置参考

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `enabled` | bool | 是 | `false` | |
| `homeserver` | url | 是 | —— | 比如 `https://matrix.org` |
| `user_id` | string | 是 | —— | `@bot:matrix.org` |
| `access_token` | string | 是 | —— | 来自 login 或 Element |
| `encryption_enabled` | bool | 可选 | `false` | 需要 `[matrix-e2e]` extra + libolm |
| `allow_from` | list[string] | 可选 | `[]` | Matrix user id 列表；`[]` = bot 加入的房间里谁都能聊 |
| `rooms` | list[string] | 可选 | `[]` | 指定 room id 列表；`[]` = bot 在任意房间都监听 |

## Matrix 上支持的能力

| 特性 | 支持情况 |
|------|----------|
| 1:1 私聊 | ✅ |
| 群组房间 | ✅ |
| Markdown → HTML | ✅ *（在 Element、Cinny 等里渲染正确）* |
| LaTeX 数学公式 | ⚠️ 需要 Matrix 客户端装 `mathjs` 插件 |
| 文件上传 | ✅ |
| 文件下载 | ✅ |
| 端到端加密 | ✅ *（按需开启）* |
| 正在输入指示 | ✅ |
| 表情反应 | ⚠️ 只支持发出方向 |

## 端到端加密

`encryption_enabled: true` + libolm + `[matrix-e2e]` extra 都齐了之后：

- Bot 首次启动时生成自己的设备密钥
- 对每个 E2EE 房间，bot 通过 Megolm 参与密钥交换
- 所有消息（含附件）都是端到端加密

**注意**：bot 的推理仍然在 DeepTutor 服务端发生。加密只是在 Matrix 客户端（用户）和 bot 的 Matrix 进程之间，但消息文本到达 LLM provider 时是未加密的（除非你配了本地 LLM）。

如果想做到「端到端到 LLM」的隐私，配本地 Ollama / vLLM 跟 bot 一起用。

## 保活机制

Matrix 渠道用 **`/sync` 长轮询接口**，30 秒超时。模式：

1. 用 `since=<last_batch>` 调 `/sync`，超时 30000
2. 收到新事件（或 30 秒后空响应）
3. 更新 `last_batch`，立即重新 poll

断线时：

- 网络中断是透明的 —— 下一次 `/sync` 重试
- 认证错误（401）需要人工介入（token 过期或被撤销）

想要高可用就把 DeepTutor server 放在进程守护下（systemd、docker restart-policy）。渠道自身处理瞬时故障。

## 常见问题

### `M_UNKNOWN_TOKEN`

你的 `access_token` 被撤了（从其他客户端登出、或服务器轮换密钥）。通过 Element 设置或 REST login 重新拿一个 token。

### Bot 进了房间但 E2EE 房间里不回复

你开了 `encryption_enabled: true` 但没装 `[matrix-e2e]` extra。Bot 连得上但解不开密 —— 装 libolm 后重装。

### 联邦延迟

如果 bot 在 `matrix.org` 而你在一个小的自建服务器聊，消息可能要几秒才联邦过来。不是 bug —— 联邦延迟。

### "User not in room" 发回复时报错

Bot 被踢了或退群了。从你的 Matrix 客户端重新邀请。

## 另请参阅

- [**TutorBot 概览**](/zh-cn/docs/tutorbot/) —— 整体架构
- [Matrix 规范](https://spec.matrix.org/) —— 底层协议
