---
title: 多用户部署
description: 打开认证开关，DeepTutor 就变成多租户部署 —— 每个用户拥有独立的工作区，资源由管理员统一编排。
---

打开认证开关，DeepTutor 就变成多租户部署 —— **每个用户拥有独立的工作区**，**资源由管理员统一编排**。第一个注册的人成为 admin，代表所有其他人配置模型、API key 和知识库。后续账号由 admin 创建（邀请制），每个人有自己作用域内的对话历史 / 记忆 / 笔记本 / 知识库，并且只能看到 admin 分配给他们的 LLM、KB 和 skill。

## 快速上手（5 步）

```bash
# 1. 在 data/user/settings/auth.json 里开启 auth：
#    {"enabled": true, "token_expire_hours": 24, "cookie_secure": false}

# 2. 重启 web 栈。
deeptutor start

# 3. 打开 http://localhost:3782/register 并创建第一个账号。
#    第一次注册是唯一一次公开注册；那个用户成为 admin，之后
#    /register 端点会自动关闭。

# 4. 以 admin 身份进入 /admin/users → "Add user" 给团队成员开账号。

# 5. 对每个用户，点击 slider 图标 → 分配 LLM profile、知识库和 skill。
#    保存。用户现在就能登录开干了。
```

## admin 能看到什么

- **完整的设置页面**，在 `/settings` —— 管理 LLM / embedding / 搜索 provider、API key、模型 catalog，以及运行时 "Apply"。
- **用户管理**，在 `/admin/users` —— 创建、提升、降级、删除账号。一旦有了第一个 admin，公开的 `/register` 端点会自动关闭；后续账号走 `POST /api/v1/auth/users`（admin-only）。
- **授权编辑器** —— 对每个非 admin 用户，挑选他们可用的 LLM 模型、知识库和 skill，把系统工具（联网搜索、论文搜索……）和 MCP 工具收窄成白名单，也可以彻底关掉代码执行。工具白名单与 partner 配置同语义：*Default* 全部放行，*Custom* 是显式白名单。授权只带**逻辑 ID**；API key 永远不会越过授权边界。
- **审计追踪** —— 每次授权变更和被授权资源的访问都会追加到 `data/system/audit/usage.jsonl`。

## 普通用户得到什么

- **独立工作区**，在 `data/users/<uid>/` 下 —— 自己的对话历史（`chat_history.db`）、记忆、笔记本和个人知识库。默认什么都不共享。
- **只读访问** admin 分配的知识库和 skill，在他们自己的资源旁边以 "Assigned by admin" 徽章并列展示。
- **删减版设置页面** —— 只展示主题、语言以及已授权模型的摘要。API key、base URL 和 provider endpoint 不会返回给非 admin 请求。
- **作用域内的 LLM** —— 对话轮次通过 admin 分配的模型走。如果没有授权的 LLM，那一轮会被直接拒绝（不会偷偷 fallback 到 admin 的 key）。
- **作用域内的工具** —— 输入框、`/settings/tools` 页面以及每一轮对话都只暴露授权白名单内的系统工具和 MCP 工具；代码执行在部署沙箱策略之上再尊重每用户开关。

## 工作区布局

所有数据都在 `data/` 下 —— 挂载和备份只需要这一棵树：

```text
data/
├── user/                        # Admin 工作区（设置、API key、admin 任务）
├── system/
│   ├── auth/users.json          # 凭证哈希、角色
│   ├── auth/auth_secret         # JWT 签名密钥（自动生成）
│   ├── grants/<uid>.json        # 每个用户的资源授权（admin 管理）
│   └── audit/usage.jsonl        # 审计追踪
├── users/<uid>/
│   ├── user/
│   │   ├── chat_history.db
│   │   ├── settings/interface.json
│   │   └── workspace/{chat,co-writer,book,...}
│   ├── memory/
│   └── knowledge_bases/...
└── partners/<id>/               # Partner 工作区
```

从 v1.5 之前的布局（与 `data/` 平级的 `multi-user/` 目录）升级的部署会在首次启动时自动迁移：`multi-user/_system` 移到 `data/system`，每个 `multi-user/<uid>` 移到 `data/users/<uid>`。

## 配置参考

| 设置 | 必填 | 说明 |
|------|------|------|
| `data/user/settings/auth.json: enabled` | 是 | 设为 `true` 开启多用户 auth。默认 `false`（单用户模式 —— 各处都走 admin 路径）。 |
| `data/system/auth/auth_secret` | 推荐 | JWT 签名密钥。首次带认证启动时，若缺失会自动生成。 |
| `data/user/settings/auth.json: token_expire_hours` | 否 | JWT 寿命；默认 `24`。 |
| `data/user/settings/auth.json: username` / `password_hash` | 否 | 可选的 headless 单用户引导凭证。用浏览器注册时留空。 |
| `data/user/settings/system.json` | 否 | `deeptutor start` 会从运行时设置推导前端 auth flag 和 API base。 |

## 重要注意事项

> ⚠️ **PocketBase 模式（设置了 `integrations.pocketbase_url`）只支持单用户。** 默认 PocketBase schema 在 `users` 上没有 `role` 字段（每次登录解析为 `role=user`，无法创建 admin），并且 `sessions` / `messages` / `turns` 查询不会按 `user_id` 过滤。多用户部署必须把 `integrations.pocketbase_url` 留空，使用默认的 JSON/SQLite 后端。

> ⚠️ **建议单进程部署。** "第一个用户自动提升为 admin" 这个机制由进程内的 `threading.Lock` 保护。多 worker 部署应当离线 provision 第一个 admin（先以 `auth.json.enabled=false` 启动，通过引导流程注册 admin，再把 `auth.json.enabled=true` 打开），或者把用户存储换成外部系统。

## 生产 checklist

- ✅ 设置一个强 `auth_secret` 并备份
- ✅ 在 `auth.json` 里设 `cookie_secure: true`，让 session cookie 必须走 HTTPS
- ✅ 把 DeepTutor 放在反向代理后面（Caddy、nginx、Traefik），用 TLS termination
- ✅ 在 `system.json` 里设 `public_api_base`，让前端 bundle 知道去哪儿找后端
- ✅ 定期备份 `data/` —— 账号、授权和所有工作区都在这一棵树下
- ✅ Docker：保留 `docker-compose.yml` 里的 `./data:/app/data` 卷。沙箱 runner 刻意只挂工作区子树（`data/user/workspace`、`data/users`），永远不挂存放认证状态和 API key 的 `data/system`、`data/user/settings`

## Caddyfile 示例

```caddyfile
deeptutor.example.com {
    reverse_proxy /api/* localhost:8001
    reverse_proxy localhost:3782
}
```

然后在 `data/user/settings/system.json` 里：

```json
{
  "public_api_base": "https://deeptutor.example.com"
}
```

在 `data/user/settings/auth.json` 里：

```json
{
  "enabled": true,
  "token_expire_hours": 24,
  "cookie_secure": true
}
```

## 常见错误

### 开启 auth 后 `404 /register`

前端 bundle 可能被缓存了。用 Docker 的话，重新创建容器。从源码起的话，编辑完 `auth.json` 后重启 `deeptutor start`。

### 第一次登录能进但没有 admin 链接

确认 `data/system/auth/users.json` 里第一个用户的 `"role": "admin"`。如果不是，手动改掉并重启。

### 重启后 `Cannot decode JWT`

`auth_secret` 丢了或被重新生成。从备份恢复，或者接受新的 secret 然后要求所有用户重新登录。

## headless 单用户引导

对于没人能在浏览器里注册的自动化场景，直接在 `auth.json` 里设凭证：

```json
{
  "enabled": true,
  "username": "alice",
  "password_hash": "<bcrypt-hash>",
  "token_expire_hours": 24
}
```

生成 hash：

```python
import bcrypt
print(bcrypt.hashpw(b"your-password", bcrypt.gensalt()).decode())
```

然后 `deeptutor start`，用 `alice` + your-password 登录。

更多修复方法：[**故障排查**](/zh-cn/docs/get-started/troubleshooting/)。
