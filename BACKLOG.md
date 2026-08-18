# BACKLOG.md

Work queue for animal-sounds, most valuable first.

Every open item below was **verified by running something**, and the check that
established it is named. Items that could not be verified in this environment say so
explicitly rather than assuming. Tick items off or delete them as they land.

---

## Done

- [x] **Dependencies are current.** Verified against the registries on 2026-08-18:
  Flask `3.1.3` is the latest on PyPI; Python `3.14` is the newest release cycle
  (supported to 2030-10-31); all five GitHub Actions are pinned to their latest major
  (`checkout@v7`, `setup-buildx-action@v4`, `build-push-action@v7`, `login-action@v4`,
  `metadata-action@v6`).
- [x] **Both Flask security advisories cleared.** Neither could affect this app — both
  concern signed session cookies, and a search for `session`, `secret_key` and
  `set_cookie` across `app/` returns nothing.
- [x] **Dependency updates automated.** [.github/dependabot.yml](.github/dependabot.yml)
  watches pip, GitHub Actions and the Docker base image weekly, opening PRs only.
- [x] **CI no longer publishes blind.** The workflow builds, starts the container, and
  smoke tests `/health`, `/api/animals`, `/api/info`, `/api/audio` and `/` *before* the
  push step. A broken image cannot reach GHCR; the previous image stays live.
- [x] **Pull requests are built and tested** via a `pull_request` trigger, so dependency
  bumps are verified before merge.

---

## Phase 1 — Correctness — DONE

All four items shipped 2026-08-18, each with a regression test.

- [x] **`/api/audio` no longer 500s on a read-only or full `/config`.**
  `_ensure_audio_directories()` now handles `OSError` itself, so both call sites are
  covered, and logs a warning instead of failing silently. Existing files still serve and
  still list; only the folder creation is skipped.
- [x] **Local audio files added while the page is open are now picked up.**
  The index is re-fetched when the user switches to Local Files mode, and again when the
  tab regains focus. No new UI was needed, and the load-time double fetch is avoided.
- [x] **The index and the serving routes can no longer disagree.**
  Both now call a single `_servable_audio_file()` gate, so anything listed is playable and
  anything playable is listed. This replaces three copies of the same checks that had
  drifted apart. Covered by a test over seven Linux-legal filenames Windows cannot create.
- [x] **Symlinks resolving outside their directory are rejected**, by both the routes and
  the index. Verified on Linux in CI — these two tests skip on Windows, so a green local
  run does not prove them.

---

## Phase 2 — Production hardening — 3 of 4 done

- [x] **The container no longer runs Flask's development server.** It serves with
  `waitress` (pure Python, no compiler, works on Windows too). `app.run()` stays under
  `__main__` for local development. Waitress declares support only up to Python 3.13 while
  the image is on 3.14, so this was not taken on trust: the app was run under waitress on
  Python 3.14.6 and all five routes returned 200 before the change was committed.
- [x] **`LOG_LEVEL` does something.** `_configure_logging()` applies it at import and
  returns the level actually in effect, which is what `/api/info` now reports rather than
  echoing back a value that may not have been understood. An unrecognised value falls back
  to `info` with a warning instead of refusing to start. Verified end to end: at `info` the
  access log shows each request, at `warning` those lines disappear.
- [x] **The app has access logging**, which it previously had none of. `/health` is
  excluded — the container healthcheck hits it every 30 seconds and would bury everything
  else.
- [x] **The duplicated healthcheck is gone.** One copy now, in the Dockerfile, so it
  applies wherever the image runs including Unraid.

- [ ] **The container still runs as root.** No `USER` directive, so the app and everything
  it writes into `/config` run as UID 0 — the usual cause of Unraid appdata permission
  surprises. Held back deliberately: changing the user changes ownership expectations for
  an appdata share that already exists, which can break a running deployment. See Open
  questions.

---

## Phase 3 — Tests — DONE

- [x] **pytest suite added** under `tests/`: 41 tests covering catalog integrity, the
  Python-to-JavaScript `sound_pattern` contract, every route's shape, audio serving, nine
  path-traversal attacks, symlink containment, and resilience to an unwritable `/config`.
  Runs in about a quarter of a second with no Docker, and writes nothing outside a temp
  directory.
- [x] **CI runs the suite** before the image build, so unit failures fail fast and the two
  Linux-only symlink tests actually execute.

---

## Phase 4 — Accessibility and polish

- [ ] **No `prefers-reduced-motion` support.** The Pokeball throw, pellet drag and chomp
  crumbs animate unconditionally, ignoring an explicit OS-level accessibility request. For
  an app aimed partly at children, some of whom are motion-sensitive, this is the most
  meaningful item in this phase.
  *Verified:* `app/static/styles.css` contains exactly one media query
  (`max-width: 520px`).
  *Fix:* one media query shortening or disabling the transforms.
- [ ] **No dark mode.** Same check: no `prefers-color-scheme` anywhere. The palette is
  already driven by CSS custom properties, so this is a variable swap, not a redesign.
- [ ] **No favicon**, so every page load logs a `/favicon.ico` 404. An existing animal SVG
  can serve as one.
- [ ] **Static assets have no cache-busting**, so returning users can get a stale `app.js`
  or `styles.css` after an update.
- [ ] **`README.md`'s project tree is out of date** — it omits `.github/`, `.env.example`,
  `.dockerignore` and `AGENTS.md`. The animal list and count *are* accurate: verified by
  diffing the README against `ANIMALS`, 22 on both sides with no discrepancies.

---

## Phase 5 — Features

Ordered by improvement relative to effort.

- [ ] **Upload audio from the browser.** Today, using Local Files mode means reaching the
  container filesystem or the Unraid appdata share. A small upload form writing into
  `/config/audio/<id>/`, reusing the existing extension allowlist, is what makes the
  feature usable by anyone not comfortable with a file share. Pairs naturally with the
  index-refresh fix in Phase 1.
- [ ] **Put settings in `/config`.** Both README and AGENTS.md describe `/config` as
  reserved for future state, but the only setting — sound source mode — lives in browser
  `localStorage`, so it does not follow the user between devices. A small JSON file gives
  the reserved path an actual purpose.
- [ ] **Volume control and a stop-all button.** Generated gains are hardcoded per pattern
  in `app.js`; there is currently no way to turn anything down.
- [ ] **Show local-file status per card.** The `has-local-audio` class is already applied,
  it just is not surfaced. Showing the file count lets users see their files registered.
- [ ] **Group the animals** (farm / wild / birds / water) or add a filter. At 22 cards the
  grid is fine; this matters if the catalog grows.
- [ ] **Offline install (PWA).** The app is already fully offline-capable — no CDNs, no
  external media — so a manifest and service worker would make it installable on a tablet,
  which is the obvious use for a children's soundboard.

---

## Deliberately not doing

- **Splitting `app.js` into modules.** At ~970 lines in one IIFE it is large, but it is
  organised and has no build step, which is a stated project goal. Splitting it adds import
  wiring for no user-visible gain. Revisit only if finding things in it becomes genuinely
  hard.
- **Adding a lockfile.** A real gap, but the dependency list is one line. Dependabot plus
  the pinned version covers the risk until there is more to lock.

---

## Assumptions

- The "22 animals" assertion in the CI smoke test is intentional and should be updated by
  hand when the catalog changes. It exists to catch accidental catalog loss.
- `/config` is owned by the person running the container, so the symlink issue above is not
  treated as urgent.
- Fixed internal port `3000` and a framework-free UI are permanent constraints, per
  AGENTS.md, and none of the changes above alter them.

## Open questions

- **Non-root container:** changing the user changes ownership of files already written into
  the Unraid appdata share. Confirm before shipping, and confirm whether a one-time
  ownership fix on the existing share is acceptable.
- **Upload feature:** should uploads be open to anyone who can reach the WebUI? The app has
  no authentication today, and adding write access to disk is the first feature where that
  matters.
