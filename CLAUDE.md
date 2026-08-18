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

Useful when Docker Desktop isn't running.

The container serves with **waitress**, not `app.run()` — Flask's development server is not
built for production traffic. `main.py` keeps `app.run()` under `__main__`, so the loop
below is still the quickest way to iterate locally; it is just not what ships.

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

`pytest` covers the catalog, the routes, and audio serving:

```bash
pip install -r app/requirements.txt -r app/requirements-dev.txt
```

```bash
python -m pytest tests -q
```

It runs in well under a second, needs no Docker, and writes nothing outside a temp
directory — `tests/conftest.py` repoints `CONFIG_PATH` before importing the app, which
also keeps a Windows run from creating `C:\config`.

Two symlink tests skip on Windows and execute only on Linux, so CI is where they are
actually proven. A green local run is not proof those two passed.

There is no linter or formatter configured.

`/health` must return `200` with `"status": "healthy"` — the Docker and Unraid healthchecks
both depend on it, so never let it get slow or add a dependency to it.

### CI

[.github/workflows/publish-ghcr.yml](.github/workflows/publish-ghcr.yml) runs the unit
tests, builds the image, smoke tests it, and pushes it to `ghcr.io/raq-tech/animal-sounds` on pushes to `main` and on
`v*` tags. Pull requests run the same build and smoke test but skip the push.

The smoke test is the only automated check in the repo: it starts the built container and
asserts `/health` reports healthy, `/api/animals` returns 22 animals, `/api/info` and
`/api/audio` return JSON, and `/` renders animal cards. It runs **before** the push step, so
an image that fails it never reaches GHCR and the previously published image stays live.
If you change the animal count, update the assertion there too.

## Layout

| Path | Responsibility |
|---|---|
| [app/main.py](app/main.py) | All Flask routes, env config, audio-file discovery and safe serving. ~260 lines. |
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

**The audio routes are the only place user input touches the filesystem.** Every check
lives in one helper, `_servable_audio_file()`, called by the serving routes *and* by the
`/api/audio` index. It rejects unsafe filenames, disallowed extensions, non-files, and
symlinks resolving outside their directory. Route decisions through that helper instead of
re-implementing them: the index and the routes sharing a single gate is what guarantees
anything listed is playable and anything playable is listed. They disagreed once, and the
result was a catalog full of URLs that 404. Unknown animal IDs are still checked
separately in each route.

**Sound falls back rather than failing.** Animal sounds: local file → generated tone. Chomp
sounds: `/config/audio/<id>/chomp/` → `/config/audio/chomp/` → generated. Every failure path
also writes a message to the `#sound-status` live region for screen readers. Preserve that
pattern when adding audio features.

**Mode precedence in `activateCard`:** feed mode wins and consumes the click (and disarms
itself); otherwise the sound plays and, if throw mode is armed, the Pokeball animation runs
after it. Throw mode stays armed across clicks by design; feed mode does not.

**Port 3000 is fixed** inside the container, in the Dockerfile `CMD` and `EXPOSE`, in
`app.run()`, in the healthcheck, and in the Unraid template. Change it in one place and
deployments break.

**The healthcheck lives only in the Dockerfile.** It used to be duplicated in
`docker-compose.yml`; there is now one copy, so it applies wherever the image runs. Do not
add a second one to compose.

**`LOG_LEVEL` is wired to real logging.** `_configure_logging()` applies it at import and
returns the level actually in effect, which is what `/api/info` reports — an unrecognised
value falls back to `info` with a warning rather than refusing to start. Requests are
access logged, except `/health`, which the container healthcheck hits every 30 seconds.

## Conventions

- Python: standard library, Flask and waitress only. No ORM, no blueprints. Private helpers are
  prefixed with `_`. Type hints on function signatures.
- JavaScript: no framework, no build step, no `npm`. Everything lives inside the single IIFE
  in `app.js`; `const`/`let`, optional chaining, and `async`/`await` are used freely.
- CSS: plain CSS with custom properties, no preprocessor.
- Never hardcode secrets; read configuration from environment variables.
