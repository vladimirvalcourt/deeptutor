---
title: Install from Source
description: Option 2 — clone, install editable, hot-reload the frontend. For contributors and power users.
---

For development against a checkout. Use **Python 3.11+** and **Node.js 22 LTS** to match CI and Docker.

## Install

```bash
git clone https://github.com/HKUDS/DeepTutor.git
cd DeepTutor

# Create a venv (macOS / Linux)
# Windows PowerShell:
#   py -3.11 -m venv .venv ; .\.venv\Scripts\Activate.ps1
python3 -m venv .venv && source .venv/bin/activate
python -m pip install --upgrade pip

# Install backend + frontend deps
python -m pip install -e .
( cd web && npm ci --legacy-peer-deps )

deeptutor init
deeptutor start
```

Source installs run Next.js in dev mode against the local `web/` directory; everything else (config layout, ports, stop with `Ctrl+C`) matches the [**PyPI install**](/docs/get-started/pypi/).

## Conda instead of venv

```bash
conda create -n deeptutor python=3.11
conda activate deeptutor
python -m pip install --upgrade pip
# ...then continue with `pip install -e .` and `npm ci`
```

## Optional install extras

`pyproject.toml` exposes layered extras:

```bash
pip install -e ".[dev]"             # tests / lint tools
pip install -e ".[partners]"        # Partner channel SDKs + MCP client
pip install -e ".[matrix]"          # Matrix channel without E2EE / libolm
pip install -e ".[matrix-e2e]"      # Matrix E2EE; requires libolm
pip install -e ".[math-animator]"   # Manim addon; requires LaTeX / ffmpeg / system libs
```

Compose them: `pip install -e ".[dev,tutorbot,math-animator]"`.

### System dependencies for some extras

| Extra | System library |
|-------|----------------|
| `matrix-e2e` | **libolm**: `brew install libolm` (macOS) / `sudo apt install libolm-dev` (Debian) |
| `math-animator` | **LaTeX + ffmpeg**: `brew install --cask mactex && brew install ffmpeg` (macOS) / `sudo apt install texlive-full ffmpeg` (Linux) |

## Frontend dependency tweaks

When you add or upgrade a frontend dependency:

```bash
cd web
npm install --legacy-peer-deps
# commit both web/package.json and web/package-lock.json
```

## Dev-server troubleshooting

**Stuck dev server:** if `deeptutor start` reports an existing frontend that isn't responding, stop the PID it prints. If no Next.js process is actually running, the lock files are stale — remove them and retry:

```bash
rm -f web/.next/dev/lock web/.next/lock
deeptutor start
```

## Hot reload

The backend supports `--reload`. Start backend and frontend in separate terminals for the best dev loop:

```bash
# Terminal A — backend with hot reload
python -m uvicorn deeptutor.api.main:app \
  --host 0.0.0.0 --port 8001 \
  --reload --reload-exclude "web/*" --reload-exclude "data/*"

# Terminal B — frontend dev server
cd web && npm run dev -- -p 3782
```

## Updating

```bash
git pull
pip install -e . --upgrade
cd web && npm ci --legacy-peer-deps
```

If a release bumped settings schema, also re-run `deeptutor init` to fill in newly-introduced fields. Existing config is preserved.

## Common errors

### `error: Microsoft Visual C++ 14.0 is required` (Windows)

Some Python deps compile C extensions. Install [**Build Tools for Visual Studio**](https://visualstudio.microsoft.com/visual-cpp-build-tools/) with "Desktop development with C++".

### `libolm` not found (when `matrix-e2e` is installed)

```bash
brew install libolm                   # macOS
sudo apt install libolm-dev           # Debian / Ubuntu
pip install -e ".[matrix-e2e]" --force-reinstall
```

### `npm ci` slow or times out

```bash
npm config set fetch-timeout 600000
cd web && npm ci --legacy-peer-deps
```

### Backend `--reload` thrashes on every save

You forgot the `--reload-exclude` flags. Restart with:

```bash
python -m uvicorn deeptutor.api.main:app \
  --host 0.0.0.0 --port 8001 \
  --reload --reload-exclude "web/*" --reload-exclude "data/*"
```

More fixes: [**Troubleshooting**](/docs/get-started/troubleshooting/).

## Next

- [**DeepTutor CLI**](/docs/cli/) — drive the CLI from the same workspace
- [**Explore DeepTutor**](/docs/explore/) — tour the running app
