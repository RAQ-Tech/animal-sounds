# AGENTS.md

This starter is intended to be cloned into future Python + WebUI Docker projects, especially for Unraid.

## Project goals
- Keep internal app port fixed at `3000`.
- Treat `/config` as the primary persistent path for settings and app state.
- Keep dependencies light and implementation easy to extend.
- Keep the starter reusable, understandable, and quick to adapt into new projects.

## Guardrails for future edits
1. Do not hardcode secrets. Use environment variables.
2. Keep `/health` route functional and fast.
3. Keep the app runnable with `docker compose up --build`.
4. Keep the UI lightweight (HTML/CSS/JS) unless a framework is explicitly required.
5. Preserve Unraid-friendly mappings in `unraid/template.xml` and `README.md`.
6. Do not rewrite unrelated files or reorganize the repo without a clear reason.
7. Keep changes scoped, practical, and easy to review.

## Layout
- `app/main.py`: app routes and config loading.
- `app/templates/`: server-rendered HTML templates.
- `app/static/`: frontend CSS/JS assets.
- `unraid/template.xml`: Unraid Community Apps template scaffold.

## Working style
When starting work:
1. Inspect the repository structure.
2. Identify the relevant files.
3. Briefly summarize the plan.
4. Then implement.

When finishing work:
1. Report which files changed.
2. Explain what was added or adjusted.
3. Call out any env vars, ports, paths, or volume mappings the user must know.
4. Give short run/test instructions.

## Run and verification
- Primary local run command: `docker compose up --build`
- The app should be reachable on the configured host port and internally on port `3000`.
- The `/health` endpoint must respond successfully.
- Changes should preserve a clean initial startup experience for Docker and Unraid use.

## Reuse checklist for new repos
- Rename app/container/image references.
- Update environment variable defaults.
- Update Unraid metadata (template URL, icon, project links).
- Keep internal container port at `3000`.
- Map `/config` to the Unraid appdata location for the new app name.

## Definition of done
A task is complete when:
- The requested change is implemented.
- The app still runs with `docker compose up --build`.
- `/health` still works.
- Unraid mappings and README instructions remain accurate.
- The result is practical for reuse in future starter-based projects.
