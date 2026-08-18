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

## Phase 1 — Correctness

Three confirmed defects plus one read-verified risk. None is a security hole; all are
silent failures, which is why they have gone unnoticed.

- [ ] **`/api/audio` returns 500 when `/config` is read-only or full.**
  `_audio_index()` calls `_ensure_audio_directories()` with no error handling, while the
  identical call at import time is wrapped in `try/except OSError`. On a read-only volume
  the whole endpoint dies, so Local Files mode breaks with a server error instead of
  degrading to generated sounds.
  *Verified:* patched `Path.mkdir` to raise `OSError(30)`, then requested `/api/audio` —
  the exception propagated. `/health` correctly survived the same test.
  *Fix:* wrap the call the same way the import-time one is wrapped. One line.

- [ ] **Local audio files added while the page is open are never seen.**
  `refreshLocalAudioIndex()` is called exactly once, at the bottom of the IIFE on page
  load. Switching to Local Files mode does not re-fetch. The documented workflow — drop
  files into `/config/audio/<id>/`, then switch the UI to Local Files — silently fails
  unless the user reloads, and the UI reports "No local audio files" instead of explaining
  why. This quietly undermines the app's main optional feature.
  *Verified:* searching `app/static/app.js` for `refreshLocalAudioIndex` returns only the
  definition (line 108) and the load-time call (line 968); `setSoundSourceMode` does not
  call it.
  *Fix:* re-fetch the index when switching to Local Files mode, and add a visible refresh
  control. Small.

- [ ] **`/api/audio` can advertise URLs that are guaranteed to 404.**
  The index (`_audio_files_in_dir`) filters only on extension, but the serving route
  rejects any filename containing a backslash. A backslash is a legal filename character
  on Linux, which is what the container runs, so such a file is listed in the catalog and
  then 404s when played.
  *Verified:* simulated a Linux directory listing; `/api/audio` advertised
  `/config/audio/cow/back%5Cslash.mp3` while `_is_safe_audio_filename` rejected that same
  name. Twelve other awkward names (spaces, `#`, `%`, `+`, `&`, `;`, quotes, CJK,
  combining accents, uppercase extensions) all round-trip correctly.
  *Fix:* apply the same filename check in the indexer that the route already applies, so
  the two agree. One line, and it removes a whole class of future mismatch.

- [ ] **A symlink inside the audio folder is followed and served.**
  Werkzeug's `safe_join` blocks `..` in the path string, but `send_from_directory` then
  calls `os.path.isfile()`, which follows symlinks; there is no containment check on the
  resolved path. A symlink at `/config/audio/cow/x.mp3` pointing anywhere on the container
  filesystem would be served.
  *Verified:* read the installed Werkzeug source for both functions. **Not** verified by
  execution — Windows would not allow creating the symlink, so this rests on reading the
  implementation, not on a passing test.
  *Severity:* low. Only reachable by someone who can already write into the config volume,
  which on Unraid is the owner. Worth a resolved-path check when the audio routes are next
  touched.

---

## Phase 2 — Production hardening

- [ ] **The container serves production traffic from Flask's development server.**
  `app/main.py` ends in `app.run(...)` (line 238), which Flask itself warns is not for
  production: it is not built for concurrency or hostile input.
  *Fix:* add `waitress` (pure Python, no compiler needed) and change the Dockerfile `CMD`.
  Keep `app.run` behind `__main__` for local development. ~5 lines.

- [ ] **The container runs as root.** No `USER` directive in the Dockerfile, so the app and
  everything it writes into `/config` run as UID 0 — the usual cause of Unraid appdata
  permission surprises.
  *Fix:* create a non-root user and adjust ownership of `/config`. Changes ownership on an
  existing appdata share, so this one needs confirming before it ships.

- [ ] **`LOG_LEVEL` does nothing.** It is read, shown in the UI and returned by
  `/api/info`, but never passed to `logging`. Setting it to `debug` changes nothing.
  *Verified:* the three references in `app/main.py` are all display-only.
  *Fix:* wire it to `logging.basicConfig`, or stop advertising it. Wiring it up also gives
  the app real request logging, which it has none of today.

- [ ] **The healthcheck is duplicated** in [Dockerfile](Dockerfile) and
  [docker-compose.yml](docker-compose.yml) with identical commands. They will drift.

---

## Phase 3 — Tests

- [ ] **Add the pytest suite.** A 25-test suite was written and run green during the
  2026-08-18 audit but not committed, since it belongs with a decision about test layout.
  It covers catalog integrity (unique ids, every animal has an SVG, no orphan SVGs), the
  Python-to-JavaScript `sound_pattern` contract, every route's shape, audio serving, and
  nine path-traversal attacks. It runs in 0.4 seconds and needs no Docker.
  The two highest-value tests are the ones no person will remember to run by hand:
  - the `sound_pattern` contract, which is the four-file trap documented in CLAUDE.md and
    is currently enforced only by convention;
  - index/route agreement, which is what caught the backslash defect above.
- [ ] **Run the suite in CI** alongside the container smoke test, so unit failures are
  caught before the slower image build.

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
