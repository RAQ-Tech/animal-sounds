# BACKLOG.md

Known gaps and improvement ideas, ordered roughly by value. Nothing here is a promise —
it is a running list so future work does not have to re-derive it. Tick items off or delete
them as they land.

## High — correctness and safety

- [x] **CI no longer publishes blind.** The publish workflow now builds the image, starts it,
  and smoke tests `/health`, `/api/animals`, `/api/info`, `/api/audio` and `/` before the push
  step runs. A broken image fails the job and never reaches GHCR.
- [x] **Pull requests are built and tested.** The workflow gained a `pull_request` trigger and
  runs the same build and smoke test with the push steps skipped, so dependency bumps are
  verified before merge instead of after.
- [ ] **Still no unit test suite.** The CI smoke test covers the routes end to end but nothing
  tests the pieces: the filename validation in the audio routes, the `_audio_files_in_dir`
  sorting, or the sound-pattern fallbacks. `pytest` with `app.test_client()` would cover these
  in seconds and run locally without Docker.
- [ ] **Nothing checks that Python and JavaScript agree on sound patterns.** Every
  `sound_pattern` in [app/animals.py](app/animals.py) must have a matching key in the
  `soundPatterns` object in [app/static/app.js](app/static/app.js), and every animal needs an
  SVG. All 22 line up today, purely by hand. A test that parses both files would make adding
  an animal safe.
- [ ] **The production container runs Flask's development server.**
  [app/main.py](app/main.py) ends with `app.run(...)`, which Flask itself warns is not for
  production use — it is single-threaded-ish and lacks hardening. Switching to `waitress`
  (pure Python, Windows-friendly) or `gunicorn` is a one-line dependency and a one-line CMD
  change.
- [ ] **The container runs as root.** [Dockerfile](Dockerfile) never sets `USER`, so the app
  and everything it writes into `/config` run as UID 0. Adding a non-root user is standard
  practice for Unraid images and avoids appdata permission surprises.

## Medium — behaviour that does not match the docs

- [ ] **`LOG_LEVEL` does nothing.** It is read, displayed in the UI, and returned by
  `/api/info`, but never passed to `logging.basicConfig()` or Flask's logger. Setting it to
  `debug` changes nothing. Either wire it up or stop advertising it.
- [ ] **No `prefers-reduced-motion` support.** The Pokeball throw, the feed-pellet drag, and
  the chomp crumbs all animate unconditionally. Users who ask their OS for reduced motion
  still get the full effect. A single media query in
  [app/static/styles.css](app/static/styles.css) that shortens or disables the transforms
  would fix it.
- [ ] **No favicon.** Every page load produces a `/favicon.ico` 404 in the logs.
- [ ] **`README.md` project tree is out of date.** It omits `.github/`, `.env.example`,
  `.dockerignore`, and `AGENTS.md`.
- [ ] **The healthcheck is duplicated** in [Dockerfile](Dockerfile) and
  [docker-compose.yml](docker-compose.yml) with identical commands. They will drift. Keep one.

## Medium — features that fit the app's direction

- [ ] **Upload audio from the UI.** Today users must reach the container filesystem or the
  Unraid appdata share to add sounds. A small upload form writing into
  `/config/audio/<id>/` (reusing the existing extension allowlist) would make "Local Files"
  mode usable by non-technical users.
- [ ] **`/config` holds no settings yet.** Both README and AGENTS.md describe it as reserved
  for future state, but sound-source mode is stored in browser `localStorage`, so it does not
  follow the user across devices. A small JSON settings file is the obvious next step.
- [ ] **Volume control and a stop-all control.** Generated sound gains are hardcoded per
  pattern in `app.js`; there is no way to turn things down.
- [ ] **Show which animals have local audio more clearly.** The `has-local-audio` class is
  already applied to cards, but the styling for it is subtle. Worth surfacing the file count.

## Low — cleanups and hardening

- [ ] **`app.js` is ~970 lines in a single IIFE.** The sound-synthesis table, the feed/drag
  logic, and the throw animation are independent and could be separate ES modules loaded with
  `<script type="module">` — still no build step required.
- [ ] **`/api/audio` rescans the filesystem on every request** — it creates and lists 46
  directories per call. Fine at this size, but it runs on every page load; a short-lived cache
  or an explicit refresh button would cut the churn.
- [ ] **Static assets have no cache-busting.** `styles.css` and `app.js` are served without a
  version query string, so returning users can get stale files after an update.
- [x] **Dependency updates are automated.** [.github/dependabot.yml](.github/dependabot.yml)
  now watches three things weekly: the pip requirements, the GitHub Actions used by the
  publish workflow, and the `python:3.12-slim` base image in the Dockerfile. It opens pull
  requests rather than merging anything, so updates still get reviewed.
- [x] **The two open Flask advisories are cleared.** Both were low severity and both were
  fixed in Flask 3.1.3; [app/requirements.txt](app/requirements.txt) is pinned there now.
  Neither could affect this app in practice — both concern signing session cookies, and the
  app has no sessions, no cookies, and no secret key.
- [ ] **Still no lockfile.** The single pin in `requirements.txt` does not capture transitive
  dependencies (Werkzeug, Jinja2, click, itsdangerous, blinker), so two builds a month apart
  can ship different code. `pip-tools` or `uv` would produce a fully pinned
  `requirements.lock`. Low priority while the dependency list is one line long.
- [ ] **No structured logging or request logging.** Debugging a misbehaving container
  currently means guessing.
- [ ] **The Unraid template has no test path.** Nothing verifies `unraid/template.xml` still
  matches the ports and environment variables in `docker-compose.yml`.
