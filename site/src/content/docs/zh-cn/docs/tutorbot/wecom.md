---
title: 企业微信
description: 在企业微信上跑 TutorBot —— 通过 AI Bot 平台的 WebSocket 长连。
---

企业微信是腾讯的企业即时通信产品。DeepTutor 通过 **AI Bot** 平台用一条 WebSocket 长连接入。

## 你需要准备

- 一个有管理员权限的企业微信组织
- [`wecom-aibot-sdk`](https://pypi.org/project/wecom-aibot-sdk/) Python 包
- 10 分钟在企业微信管理后台

## Step 1 —— 装 SDK

企业微信支持依赖一个可选 Python 包：

```bash
pip install wecom-aibot-sdk
```

如果你用 `pip install -e ".[partners]"` 装的，可能已经带了。验证一下：

```bash
python -c "import wecom_aibot_sdk; print('ok')"
```

## Step 2 —— 创建 AI Bot

1. 登录 <https://work.weixin.qq.com/>
2. **应用与小程序** → **AI 机器人平台**
3. **新建应用** → 选 **AI 机器人** 类型
4. 填名字、描述、允许使用的部门
5. 复制 **Bot ID** 和 **Secret**

## Step 3 —— 配置

```yaml
channels:
  wecom:
    enabled: true
    bot_id: "YOUR_BOT_ID"
    secret: "YOUR_SECRET"
    allow_from: []                  # 可选，按 user id 做限制
    welcome_message: "Hi! 我是你的数学导师，有什么问题尽管问。"
```

## Step 4 —— 启动

```bash
deeptutor bot start my-math-tutor
```

```text
[bot:my-math-tutor] channel:wecom → connecting (ws://wecom...)
[bot:my-math-tutor] channel:wecom → ready
```

## 配置参考

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `enabled` | bool | 是 | |
| `bot_id` | string | 是 | 来自 AI Bot 平台 |
| `secret` | string | 是 | 来自 AI Bot 平台 |
| `allow_from` | list[string] | 可选 | 企业微信 user id；`[]` 允许组织内所有人 |
| `welcome_message` | string | 可选 | 新用户首次发消息时回的欢迎语 |

## 企业微信上支持的能力

| 特性 | 支持情况 |
|------|----------|
| 企业内私聊 | ✅ |
| 群聊 | ✅ |
| Markdown | ✅ |
| 文件 / 图片 / 语音 | ✅ |
| 外部联系人（客户） | ⚠️ 通过企业微信的外部联系人能力 |
| @ 寻址 | ✅ |

## 保活机制

后台线程维护 WebSocket，瞬时故障自动重连。

如果 bot 持续掉线：

1. 检查 AI Bot 平台 —— bot 是不是被停用了？
2. 确认你的 DeepTutor server 能正常向企业微信服务器发出 TLS 出站
3. 重启：`deeptutor bot stop my-math-tutor && deeptutor bot start my-math-tutor`

## 常见问题

### `ImportError: wecom_aibot_sdk`

```bash
pip install wecom-aibot-sdk
deeptutor bot start my-math-tutor
```

### Bot 连上了但不回复

`allow_from` 是常见嫌疑人。也确认发消息的用户在你 AI Bot 配置允许的部门里。

### 同一个组织里跑多个 bot

每个 bot 都要自己独立的 `bot_id` + `secret`。你可以在同一个 DeepTutor server 里跑多个 TutorBot，各连各的企业微信 bot。

## 另请参阅

- [**飞书**](/zh-cn/docs/tutorbot/feishu/) —— 字节的企业聊天平台
- [**TutorBot 概览**](/zh-cn/docs/tutorbot/) —— 整体架构
