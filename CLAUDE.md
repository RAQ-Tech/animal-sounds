# CLAUDE.md

Guidance for Claude Code when working in this repository.

See also [AGENTS.md](AGENTS.md) for the starter-project guardrails (fixed port `3000`,
`/config` as the persistent path, keep the UI framework-free). This file covers how the
app actually builds, runs, and gets verified.

## What this project is

A single-page Flask WebUI that shows 22 animal illustrations. Clicking a card plays that
animal's sound, synthesized in the browser with the Web Audio API — there are no bundled
audio files. Users can optionally drop their own audio files into `/config/audio/<animal-id>/`
and switch the UI to "Local Files" mode. Two extras layer on top: a Pokeball throw
animation and a draggable feed pile that makes animals chomp.

Everything is offline-friendly: no CDNs, no external media, no frontend build step.

## Build, run, verify

### Primary path — Docker (this is what ships)

```bash
docker compose up --build
```

Then open `http://localhost:8080` (host port from `HOST_PORT`, mapped to container port `3000`).
`docker compose` bind-mounts `./config` into the container at `/config`; that folder is
gitignored. Copy `.env.example` to `.env` first if you want to change ports or names.

### Fast local loop — plain Python (no Docker)

Useful when Docker Desktop isn't running. Flask is the only dependency.

```bash
pip install -r app/requirements.txt
```

```bash
CONFIG_PATH=./config python app/main.py
```

Then open `http://localhost:3000`. **Always set `CONFIG_PATH`** when running outside a
container: the default is the absolute path `/config`, which on Windows resolves to
`C:\config` and will get 46 audio folders created inside it on import.

### Tests

There is no test suite, no linter, and no formatter configured. Verification is a smoke
test. This snippet exercises every route without binding a port:

```bash
cd app && CONFIG_PATH=../config python -c "import main; c=main.app.test_client(); [print(r, c.get(r).status_code) for r in ['/','/health','/api/info','/api/animals','/api/audio']]"
```

`/health` must return `200` with `"status": "healthy"` — the Docker and Unraid healthchecks
both depend on it, so never let it get slow or add a dependency to it.

### CI

[.github/workflows/publish-ghcr.yml](.github/workflows/publish-ghcr.yml) builds the image and
pushes it to `ghcr.io/raq-tech/animal-sounds` on every push to `main` and on `v*` tags.
It only builds — it runs no tests, so a broken app will publish successfully.

## Layout

| Path | Responsibility |
|---|---|
| [app/main.py](app/main.py) | All Flask routes, env config, audio-file discovery and safe serving. ~240 lines. |
| [app/animals.py](app/animals.py) | The `ANIMALS` tuple — the single source of truth for the catalog. |
| [app/templates/index.html](app/templates/index.html) | Server-renders one `<button class="animal-card">` per animal, with sound data in `data-*` attributes. |
| [app/static/app.js](app/static/app.js) | Everything interactive: sound synthesis, local-file playback, throw mode, feed drag. One big IIFE, ~970 lines. |
| [app/static/styles.css](app/static/styles.css) | All styling and animations. |
| [app/static/animals/](app/static/animals/) | One hand-authored SVG per animal, named `<animal-id>.svg`. |
| [unraid/template.xml](unraid/template.xml) | Unraid Community Apps template. Must stay in sync with ports/env vars. |

Data flows one way: `animals.py` → `index.html` `data-*` attributes → `app.js` reads them off
the clicked card. `app.js` never fetches the animal list; it only fetches `/api/audio`.

## Things that will bite you

**Adding an animal requires four edits, and three of them are in different files.** Miss one
and the card renders but stays silent, or shows a broken image:

1. An entry in the `ANIMALS` tuple in [app/animals.py](app/animals.py).
2. A matching SVG at `app/static/animals/<id>.svg`.
3. A method named exactly like the entry's `sound_pattern` in the `soundPatterns` object in
   [app/static/app.js](app/static/app.js) (around line 235). Nothing validates this link —
   Python and JavaScript agree only by convention. Both sides currently list the same 22.
4. The animal list and folder tree in [README.md](README.md).

The `/config/audio/<id>/` folders are created automatically at import and on every
`/api/audio` request, so no filesystem edit is needed.

**The audio routes are the only place user input touches the filesystem.** They reject
unknown animal IDs, filenames containing slashes or `..`, and extensions outside
`ALLOWED_AUDIO_EXTENSIONS`. Keep all three checks if you refactor those routes.

**Sound falls back rather than failing.** Animal sounds: local file → generated tone. Chomp
sounds: `/config/audio/<id>/chomp/` → `/config/audio/chomp/` → generated. Every failure path
also writes a message to the `#sound-status` live region for screen readers. Preserve that
pattern when adding audio features.

**Mode precedence in `activateCard`:** feed mode wins and consumes the click (and disarms
itself); otherwise the sound plays and, if throw mode is armed, the Pokeball animation runs
after it. Throw mode stays armed across clicks by design; feed mode does not.

**Port 3000 is fixed** inside the container, in the Dockerfile, in `app.run()`, in the
healthchecks, and in the Unraid template. Change it in one place and deployments break.

## Conventions

- Python: standard library plus Flask only, no ORM, no blueprints. Private helpers are
  prefixed with `_`. Type hints on function signatures.
- JavaScript: no framework, no build step, no `npm`. Everything lives inside the single IIFE
  in `app.js`; `const`/`let`, optional chaining, and `async`/`await` are used freely.
- CSS: plain CSS with custom properties, no preprocessor.
- Never hardcode secrets; read configuration from environment variables.
