---
title: 故障排查
description: 各种安装路径下的常见错误，以及可以直接复制粘贴的修复方法。
---

如果你的安装行为不太对劲，在下面找到对应的症状。错误按类别分组。修复方法在当前 `main` 分支上验证过。

## 端口与进程

### `Address already in use :3782`（或 :8001）

有别的东西绑定到这个端口了。找出来：

```bash
# macOS
lsof -i :3782

# Linux
ss -ltnp | grep :3782

# Windows PowerShell
Get-NetTCPConnection -LocalPort 3782
```

干掉它，或者通过重跑 setup 向导或编辑 `data/user/settings/system.json` 改 DeepTutor 端口：

```bash
deeptutor init
```

```json
{
  "backend_port": 18001,
  "frontend_port": 4000
}
```

如果只是一次性进程级覆盖，启动 DeepTutor 之前在 shell 里 export 环境变量即可：`BACKEND_PORT=18001 FRONTEND_PORT=4000 deeptutor start`。

如果在用 Docker，改 docker 专用的端口变量：

```bash
DEEPTUTOR_DOCKER_FRONTEND_PORT=4000
DEEPTUTOR_DOCKER_BACKEND_PORT=18001
```

### 后端起来了但前端连不上

Next.js 前端在构建时把 API base 锁成了 `http://localhost:8001`。当你以另一个 hostname 提供 DeepTutor 服务时（云部署、局域网访问、反向代理），bundle 里仍然指向 `localhost`，从远端浏览器看就是错的。

修复：把 `data/user/settings/system.json` 里的 `next_public_api_base_external` 设成对外可达的 URL，或者在重新构建前端之前 export `NEXT_PUBLIC_API_BASE_EXTERNAL`：

```json
{
  "next_public_api_base_external": "https://deeptutor.example.com:8001"
}
```

然后重新构建：

```bash
# Docker
python scripts/docker_compose.py up -d --build

# 手动安装
cd web && npm run build && cd ..
```

## LLM / Embedding providers

### provider probe 时报 `HTTPError 401 Unauthorized`

provider 拒绝了你的 API key。常见坑：

- **OpenAI**：以 `sk-` 开头（project key 以 `sk-proj-` 开头）
- **Anthropic**：以 `sk-ant-` 开头
- **Azure OpenAI**：还需要 `LLM_API_VERSION`（在 设置 → LLM 里设置）
- **Google Gemini**：以 `AIza` 开头
- **Ollama / 本地 OpenAI 兼容**：API key 留空或用 `none`，base URL 设成像 `http://localhost:11434/v1`

重跑 `deeptutor init` 重新输入 key，或者直接编辑 `data/user/settings/model_catalog.json`。

### 配置时 `Failed to fetch /models`

DeepTutor 会 ping provider 的 model-list 端点来填充模型下拉框。如果你的网络把它挡了，会出现这个警告 —— 这是**非致命**的。向导会 fallback 到一份硬编码的常见模型列表然后继续。

### `host.docker.internal` 解析不了（Docker + 本地 Ollama）

| 宿主系统 | 用 |
|----------|-----|
| macOS、Windows | `http://host.docker.internal:11434/v1` |
| Linux | `http://172.17.0.1:11434/v1` *（docker0 网桥）* 或宿主机的 LAN IP |

Linux 用户也可以手动加 `host.docker.internal`：

```yaml
# docker-compose.ghcr.yml
services:
  deeptutor:
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

### 查询 KB 时报 `Embedding dimension mismatch`

你用不同的 embedding 模型重建了 KB。缓存里的维度对不上了。

修复：在 Web UI 里，**Knowledge → 选 KB → Index versions → Re-index now**。重建索引没有暴露成 CLI 命令。

### Embedding endpoint URL 老是出错

某些 provider 在 `EMBEDDING_HOST` 里要的是**完整的 embeddings 路径**，不是 API 根路径：

| Provider | 错误 | 正确 |
|----------|------|------|
| OpenAI | `https://api.openai.com/v1` | `https://api.openai.com/v1/embeddings` |
| Cohere | `https://api.cohere.ai` | `https://api.cohere.ai/v1/embed` |
| Voyage | `https://api.voyageai.com/v1` | `https://api.voyageai.com/v1/embeddings` |

## 知识库

### KB 卡在 `indexing` 状态

索引是后台任务跑的。看日志：

```bash
tail -f data/user/logs/ai_tutor_*.log | grep -i kb
```

常见原因：embedding provider 返回 429（限流 —— 用更小的 batch 重试）、embedding host 不可达（检查网络）、或者 PDF parser 失败（确认文件没有密码保护）。

### 重建索引修不了维度不匹配

如果重建索引之后维度不匹配仍然存在，KB store 里可能有过期的配置文件。从 CLI：

```bash
deeptutor kb delete physics --force
deeptutor kb create physics --doc chapter1.pdf
```

## 多用户

### 重启之后每个 API 调用都报 `401 Unauthorized`

`AUTH_SECRET` 被重新生成了，所有 JWT 都失效了。

修复：把 `AUTH_SECRET` 在 `.env` 里 pin 住，让它跨重启保持不变：

```bash
AUTH_SECRET=$(openssl rand -hex 32)
```

### 第一个用户没被提升为 admin

编辑 `multi-user/_system/auth/users.json`，把那个用户的 `"role": "admin"` 设好，然后重启。

### 登录成功但又跳回 `/login`

auth cookie 没被设置上，通常因为：

1. `AUTH_COOKIE_SECURE=true` 但你不在 HTTPS 上 —— 本地测试时设成 `false`
2. 浏览器拦了第三方 cookie，而你在子域上 —— 把前端和 API 部署在同一个 hostname 下（比如都在 `deeptutor.example.com`，前端在 `/`，API 通过 `/api/` 代理）

## Docker

### 容器立刻退出

```bash
docker logs deeptutor | tail -30
```

最常见：宿主机文件夹没预先创建。

```bash
mkdir -p data/user data/memory data/knowledge_bases
python scripts/docker_compose.py up -d
```

### 容器是 `Running` 但是 `unhealthy`

健康检查在容器内调用 `curl http://localhost:8001/`。如果后端启动慢（首次约 30 秒，下载模型元数据），健康检查可能会抖动。

等 60 秒。如果还是 unhealthy，看 supervisord 状态：

```bash
docker exec deeptutor supervisorctl status
docker exec deeptutor tail -40 /app/data/user/logs/ai_tutor_$(date +%Y%m%d).log
```

### 构建时 npm install 超时

Next.js 依赖树很大。调大 npm 的网络超时：

```bash
npm config set fetch-timeout 600000
```

官方 `Dockerfile` 已经设了 —— 只在本地构建时才需要管。

## Python 安装

### `Microsoft Visual C++ 14.0 is required`（Windows）

`tiktoken`、`chroma-hnswlib` 等几个依赖在 Windows 上要编译 C 扩展。装 [**Build Tools for Visual Studio**](https://visualstudio.microsoft.com/visual-cpp-build-tools/)，勾选 "Desktop development with C++" workload。

### `libolm not found`（仅 Matrix E2EE 需要）

```bash
# macOS
brew install libolm

# Debian / Ubuntu
sudo apt install libolm-dev

# 重装 matrix-e2e extra
pip install -e ".[matrix-e2e]" --force-reinstall
```

### `pip install` 慢到爆

网络慢的话，用本地 PyPI 镜像或 wheelhouse。中国大陆用户：

```bash
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
```

### Conda 环境已激活但 `python` 仍然指向别处

PATH 顺序可能盖住了 conda 的 python。验证：

```bash
which python
# /Users/you/miniconda3/envs/deeptutor/bin/python
```

如果不是，在一个新 shell 里跑 `conda activate deeptutor`。

## 前端

### 前端显示空白页

打开浏览器开发者工具（⌥⌘I），看 Console 标签页。常见原因：

- **CORS errors** —— 前端一个 origin，后端另一个 origin，而后端没把这个前端 origin 加进允许列表。编辑 `data/user/settings/system.json`，把你的前端 origin 加进 `cors_origins`。
- **`/_next/...` 404** —— 静态 bundle 没构建。从源码起的话：`cd web && npm run build`。
- **后端连不上** —— 验证 `curl http://localhost:8001/` 是否返回 JSON。

### 每个页面都弹 "Failed to fetch" toast

跟上面一样 —— 通常是后端没起来或者 CORS / API base URL 对不上。看 Network 标签页确认请求实际去了哪个 URL。

## TutorBot

### bot 启动时报 "missing SDK"

对应 gateway 的 SDK 没装。报错信息会告诉你是哪一个。装上：

```bash
# 通用
pip install -e ".[partners]"

# 或者装某一个（很少需要）
pip install python-telegram-bot   # Telegram
pip install slack-sdk              # Slack
pip install zulip                  # Zulip
pip install matrix-nio             # Matrix（不带 E2EE）
```

### bot 连上了但不响应

检查 bot channel 配置里的 `allow_from`：

```yaml
telegram:
  enabled: true
  token: "..."
  allow_from:               # 空 = 全部拒绝
    - "*"                    # 允许所有人
    # - "12345678"           # 或具体的 Telegram user ID
```

默认 `allow_from: []` 拒绝所有人 —— 你必须显式 opt in。

### bot 跑几分钟就掉线

Long-poll / WebSocket 连接偶尔会掉。channel manager 会带退避自动重连，但如果你看到频繁掉线：

- 检查宿主机和 gateway provider 之间的网络稳定性
- Telegram polling 把 `timeout` 调到 60 秒
- Matrix 的话，确认 homeserver 没有过于激进的超时

针对每个 gateway 的调试方法见 [**探索 TutorBot**](/zh-cn/docs/tutorbot/)。

## 记忆 / RAG 精度

### Chat 忽略了挂上的 KB

确认：

1. KB **挂上了**这一轮（不只是在选择器里出现 —— 真的点进了激活集）
2. `rag` 工具**已启用**，在 设置 → 工具，或者因为挂了 KB 而自动启用
3. KB 是 `status: ready`（不是还在索引）—— 通过 `deeptutor kb list` 检查

### `read_memory` 返回空

L3 记忆在 consolidator 至少跑过一次之前是空的。记忆的整合发生在：

- 每 N 轮（在 设置 → 记忆 里可配置）
- 用户在 Memory Workbench 里主动请求

可以从 **Memory Workbench**（`/memory` → **Run consolidator**）强制整合一次，或者走 HTTP API：

```bash
curl -X POST http://localhost:8001/api/v1/memory/runs/start
```

### Memory writes 被标成 `unsafe_text`

`write_memory` 工具有 240 字符限制和内容安全过滤。把偏好文本缩短一下，或者换种说法。

## 还卡着？

- 在 [Discord](https://discord.gg/eRsjPgMU4t) 上问 —— 最快的渠道
- 在 [github.com/HKUDS/DeepTutor/issues](https://github.com/HKUDS/DeepTutor/issues) 报 bug
- 长篇问题？开一个 [Discussion](https://github.com/HKUDS/DeepTutor/discussions)

求助时请附上：

- 你的安装路径（PyPI / 从源码 / Docker / 仅 CLI）
- `deeptutor config show` 的输出
- `data/user/logs/ai_tutor_*.log` 的最后 40 行
- Docker 的话：`docker logs deeptutor | tail -40`
