---
title: 从源码安装
description: 选项 2 —— clone 仓库、editable 安装、前端热重载。适合贡献者和高阶用户。
---

适合基于 checkout 做开发。使用 **Python 3.11+** 和 **Node.js 22 LTS**，与 CI 和 Docker 保持一致。

## 安装

```bash
git clone https://github.com/HKUDS/DeepTutor.git
cd DeepTutor

# 创建 venv（macOS / Linux）
# Windows PowerShell：
#   py -3.11 -m venv .venv ; .\.venv\Scripts\Activate.ps1
python3 -m venv .venv && source .venv/bin/activate
python -m pip install --upgrade pip

# 安装后端 + 前端依赖
python -m pip install -e .
( cd web && npm ci --legacy-peer-deps )

deeptutor init
deeptutor start
```

源码安装会以 dev 模式跑 Next.js，指向本地 `web/` 目录；其它行为（配置目录结构、端口、`Ctrl+C` 停止）和 [**PyPI 安装**](/zh-cn/docs/get-started/pypi/) 一致。

## 用 Conda 代替 venv

```bash
conda create -n deeptutor python=3.11
conda activate deeptutor
python -m pip install --upgrade pip
# ...然后继续 `pip install -e .` 和 `npm ci`
```

## 可选的安装 extras

`pyproject.toml` 暴露了分层的 extras：

```bash
pip install -e ".[dev]"             # 测试 / lint 工具
pip install -e ".[partners]"        # Partners 渠道 SDK + MCP 客户端
pip install -e ".[matrix]"          # 不带 E2EE / libolm 的 Matrix channel
pip install -e ".[matrix-e2e]"      # 带 E2EE 的 Matrix；需要 libolm
pip install -e ".[math-animator]"   # Manim 插件；需要 LaTeX / ffmpeg / 系统库
```

也可以组合：`pip install -e ".[dev,tutorbot,math-animator]"`。

### 部分 extras 需要的系统依赖

| Extra | 系统库 |
|-------|--------|
| `matrix-e2e` | **libolm**：`brew install libolm`（macOS）/ `sudo apt install libolm-dev`（Debian） |
| `math-animator` | **LaTeX + ffmpeg**：`brew install --cask mactex && brew install ffmpeg`（macOS）/ `sudo apt install texlive-full ffmpeg`（Linux） |

## 前端依赖调整

新增或升级前端依赖时：

```bash
cd web
npm install --legacy-peer-deps
# 同时提交 web/package.json 和 web/package-lock.json
```

## Dev server 故障排查

**dev server 卡住**：如果 `deeptutor start` 报告已有前端但实际无响应，先停掉它打印出的 PID。如果根本没有 Next.js 进程在跑，那是 lock 文件过期了 —— 删掉重试：

```bash
rm -f web/.next/dev/lock web/.next/lock
deeptutor start
```

## 热重载

后端支持 `--reload`。在两个独立终端里分别启后端和前端，开发体验最好：

```bash
# 终端 A —— 带热重载的后端
python -m uvicorn deeptutor.api.main:app \
  --host 0.0.0.0 --port 8001 \
  --reload --reload-exclude "web/*" --reload-exclude "data/*"

# 终端 B —— 前端 dev server
cd web && npm run dev -- -p 3782
```

## 升级

```bash
git pull
pip install -e . --upgrade
cd web && npm ci --legacy-peer-deps
```

如果某次发布动了配置 schema，再跑一次 `deeptutor init` 把新增字段补上。已有配置会保留。

## 常见错误

### `error: Microsoft Visual C++ 14.0 is required`（Windows）

部分 Python 依赖会编译 C 扩展。装 [**Build Tools for Visual Studio**](https://visualstudio.microsoft.com/visual-cpp-build-tools/)，勾选 "Desktop development with C++"。

### 找不到 `libolm`（装了 `matrix-e2e` 时）

```bash
brew install libolm                   # macOS
sudo apt install libolm-dev           # Debian / Ubuntu
pip install -e ".[matrix-e2e]" --force-reinstall
```

### `npm ci` 慢或超时

```bash
npm config set fetch-timeout 600000
cd web && npm ci --legacy-peer-deps
```

### 后端 `--reload` 每次保存都疯狂重启

`--reload-exclude` 漏了。用下面命令重启：

```bash
python -m uvicorn deeptutor.api.main:app \
  --host 0.0.0.0 --port 8001 \
  --reload --reload-exclude "web/*" --reload-exclude "data/*"
```

更多修复方法：[**故障排查**](/zh-cn/docs/get-started/troubleshooting/)。

## 下一步

- [**DeepTutor CLI**](/zh-cn/docs/cli/) —— 在同一个工作区里使用 CLI
- [**探索 DeepTutor**](/zh-cn/docs/explore/) —— 看看跑起来的应用
