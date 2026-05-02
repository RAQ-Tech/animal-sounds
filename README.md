# Starter WebUI Unraid (Python)

A reusable, Unraid-first Docker starter for Python backend + lightweight web UI projects.

> Goal: help you go from opening this GitHub page to seeing a working container WebUI in Unraid as fast as possible.

---

## TL;DR (fast path)

If you already have Unraid running and Community Applications installed:

1. In Unraid, open **Docker**.
2. Click **Add Container** (or **Install via Template URL** depending on your CA view).
3. Paste the raw template URL for your repo's `unraid/template.xml`.
4. Set only two required values:
   - **WebUI Port** (example: `8080`)
   - **App Config (Primary)** (example: `/mnt/user/appdata/starter-webui-app`)
5. Click **Apply**.
6. Open the app from the Docker page using the container icon -> **WebUI**.

If this is your first Unraid container setup, use the full step-by-step below.

---

## What this starter optimizes for

- Fast bootstrap for new app repos.
- Clean container behavior and minimal dependencies.
- Simple Unraid mapping model.
- Easy cloning/adaptation by changing only names, ports, paths, and env vars.

## Core conventions

- Internal app port is fixed: **`3000`**.
- Primary persistent path: **`/config`** (settings/state; map to Unraid `appdata`).
- Environment-variable-driven configuration.
- Health endpoint at **`/health`**.

---

## Super-detailed Unraid install guide (non-technical friendly)

### Before you start (one-time checks)

1. **Confirm Unraid is running** and you can open its web dashboard in your browser.
2. **Confirm Docker is enabled**:
   - Go to **Settings -> Docker**.
   - If Docker is disabled, enable it and start the Docker service.
3. **Confirm Community Applications plugin is installed**:
   - You should have an **Apps** tab in the top menu.
   - If not, install Community Applications first (from the Unraid Plugins page).

---

### Install this app template in Unraid

#### Method A (recommended): install from Template URL

1. Open Unraid dashboard.
2. Click **Apps**.
3. Find the option for **Install via Template URL** (wording can vary by UI version).
4. Paste your raw template URL:
   - `https://raw.githubusercontent.com/<your-org>/<your-repo>/main/unraid/template.xml`
5. Click **Install** or **Proceed**.

Unraid should open a container setup form pre-filled from the template.

#### Method B (fallback): add manually from Docker tab

Use this only if Template URL import is unavailable.

1. Go to **Docker** tab.
2. Click **Add Container**.
3. Fill in:
   - **Name**: `starter-webui-app` (or your preferred name)
   - **Repository**: your published image, e.g. `yourdockerhubuser/starter-webui-app:latest`
   - **Network Type**: `bridge`
4. Add port mapping:
   - **Container Port**: `3000`
   - **Host Port**: `8080` (or any unused port)
5. Add path mapping:
   - **Container Path**: `/config`
   - **Host Path**: `/mnt/user/appdata/starter-webui-app`
6. Add variables (optional but recommended):
   - `APP_NAME=Starter WebUI App`
   - `APP_ENV=production`
   - `LOG_LEVEL=info`
   - `FEATURE_PLACEHOLDER=true`
7. Click **Apply**.

---

### Required values (what you must set)

You only need these two for a working install:

1. **WebUI Port**
   - Suggested: `8080`
   - If `8080` is in use, choose another free port like `8090` or `8181`.
2. **App Config (Primary)**
   - Suggested: `/mnt/user/appdata/starter-webui-app`
   - This keeps app settings persistent across updates/restarts.

---

### First launch checklist (takes ~1 minute)

After clicking **Apply**:

1. Go to **Docker** tab.
2. Wait for container status to show **started/running**.
3. Click the container icon.
4. Click **WebUI**.
5. Confirm page loads with starter UI.

If WebUI does not open, test directly in browser:

- `http://<your-unraid-ip>:8080`

Health endpoint test:

- `http://<your-unraid-ip>:8080/health`
- Expected: JSON containing `"status": "healthy"`

---

### If something fails (simple troubleshooting)

1. **Container won’t start**
   - Open container logs from Docker tab.
   - Most common issue: port conflict. Change host port to another number.
2. **WebUI button opens blank/error page**
   - Confirm container is running.
   - Confirm host port matches the one you set.
   - Try direct URL: `http://<unraid-ip>:<host-port>`.
3. **Settings reset after restart**
   - Confirm `/config` is mapped to `/mnt/user/appdata/<app-name>`.
4. **Still stuck**
   - Re-apply container with default values from template, then change one setting at a time.

---

## Local Docker quick start (for developers)

1. Copy env file:

   ```bash
   cp .env.example .env
   ```

2. Build and run:

   ```bash
   docker compose up --build
   ```

3. Open UI:
   - `http://localhost:8080` (or your `HOST_PORT`)

4. Health check:
   - `http://localhost:8080/health`

---

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `APP_NAME` | `Starter WebUI App` | UI/API app display name |
| `APP_ENV` | `production` | Environment label |
| `LOG_LEVEL` | `info` | Logging placeholder |
| `FEATURE_PLACEHOLDER` | `true` | Example feature flag |
| `HOST_PORT` | `8080` | Host-exposed port mapped to container `3000` |
| `CONFIG_PATH` | `/config` | Primary persistent config/state path in container |

---

## Project structure

```text
.
├── AGENTS.md
├── Dockerfile
├── .dockerignore
├── .env.example
├── docker-compose.yml
├── README.md
├── unraid/
│   └── template.xml
└── app/
    ├── main.py
    ├── requirements.txt
    ├── templates/
    │   └── index.html
    └── static/
        └── styles.css
```

---

## What to edit first when cloning this starter

1. **App/repo identity**
   - Rename repo, update image/repository references in `unraid/template.xml`.
2. **Container naming**
   - Update `container_name` in `docker-compose.yml`.
3. **Host port**
   - Change `HOST_PORT` in `.env` for each deployment.
4. **Persistent paths**
   - In Unraid, map `/config` to appdata path first.
5. **Runtime config**
   - Add your project-specific env vars to `.env.example`, compose, and docs.

---

## Security and secrets

- Do not hardcode secrets in source files.
- Pass secrets using environment variables or external secret managers.

## Included starter behavior

- Homepage (`/`) with app metadata and starter workspace.
- Health endpoint (`/health`) for healthchecks.
- Example API route (`/api/info`).
- Lightweight modern CSS shell.
