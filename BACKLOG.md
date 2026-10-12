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
- [x] **Both Flask security advisories cleared.** Neither could affect this app â€” both
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

## Phase 1 â€” Correctness â€” DONE

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
  the index. Verified on Linux in CI â€” these two tests skip on Windows, so a green local
  run does not prove them.

---

## Phase 2 â€” Production hardening â€” 3 of 4 done

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
  excluded â€” the container healthcheck hits it every 30 seconds and would bury everything
  else.
- [x] **The duplicated healthcheck is gone.** One copy now, in the Dockerfile, so it
  applies wherever the image runs including Unraid.

- [ ] **The container still runs as root.** No `USER` directive, so the app and everything
  it writes into `/config` run as UID 0 â€” the usual cause of Unraid appdata permission
  surprises. Held back deliberately: changing the user changes ownership expectations for
  an appdata share that already exists, which can break a running deployment. See Open
  questions.

---

## Phase 3 â€” Tests â€” DONE

- [x] **pytest suite added** under `tests/`: 41 tests covering catalog integrity, the
  Python-to-JavaScript `sound_pattern` contract, every route's shape, audio serving, nine
  path-traversal attacks, symlink containment, and resilience to an unwritable `/config`.
  Runs in about a quarter of a second with no Docker, and writes nothing outside a temp
  directory.
- [x] **CI runs the suite** before the image build, so unit failures fail fast and the two
  Linux-only symlink tests actually execute.

---

## Phase 4 â€” Accessibility and polish

- [x] **Reduced motion follows the device setting.** Decorative animations/transitions
  are removed and Pokeball travel is skipped, while sound and direct feeding still work.
  *Verified:* browser emulation and computed styles; no thrown ball under reduced motion.
- [x] **Dark mode follows the device setting.** Existing colors are adapted without
  redesigning the board; headings, animal labels, controls and chips remain readable.
  *Verified:* mobile and desktop browser views, including an overflow check.
- [x] **A favicon is served.** The bundled cow SVG is reused for the tab icon;
  `/favicon.ico` also returns successfully. Installation icons are 192 and 512 pixels.
- [x] **Static assets have content versions.** CSS, JavaScript and illustrations include
  a version in their URLs; offline caches also change when bundled UI assets change.
- [x] **README mappings and examples are current.** The tree includes CI, example env,
  tests and installation assets; all 25 animals and their audio folders are documented.

---

## Phase 5 â€” Features

Ordered by improvement relative to effort.

- [x] **Upload audio from the browser.** Choose an animal, an animal/chomp sound and a
  supported recording smaller than 16 MB. Uploads need no login, per the owner decision.
  The index refreshes and Local Files mode starts immediately. Complete bytes publish
  atomically; duplicate names receive a suffix and existing recordings are preserved.
- [x] **Settings are saved in `/config`.** Shared sound source and volume persist in
  `settings.json` with atomic updates, validation, safe defaults and useful write errors.
  *Verified:* a second browser and container recreation retain the selected settings.
- [x] **Volume control and stop-all playback are available.** The slider affects generated
  and recorded sounds; Stop all also cancels pending playback and chomp/throw feedback.
- [x] **Local-file counts appear on each card.** Animal recording counts and per-animal
  chomp counts are refreshed after uploads and when returning to Local Files mode.
- [x] **Animal-group filters are available.** All animals, Farm & pets, Wild, Birds and
  Water filter the 25-card board without changing keyboard activation or sounds.
- [x] **Offline installation support is implemented.** A manifest, icons, install prompt
  and service worker provide the bundled 25-animal board with generated sounds offline.
  *Verified:* a real browser loads and plays the cached board with its network disabled.
  HTTPS or localhost is required; a plain LAN HTTP address remains online-only. Personal
  audio, uploads and server settings are not cached, and actual tablet installation is
  not established by the automated browser checks.

---

## Deliberately not doing

- **Splitting `app.js` into modules.** In one IIFE it is large, but it is
  organised and has no build step, which is a stated project goal. Splitting it adds import
  wiring for no user-visible gain. Revisit only if finding things in it becomes genuinely
  hard.
- **Adding a lockfile.** A real gap, but the runtime dependency list is small. Dependabot plus
  the pinned version covers the risk until there is more to lock.

---

## Assumptions

- The "25 animals" assertion in the CI smoke test is intentional and should be updated by
  hand when the catalog changes. It exists to catch accidental catalog loss.
- `/config` is owned by the person running the container, so the symlink issue above is not
  treated as urgent.
- Fixed internal port `3000` and a framework-free UI are permanent constraints, per
  AGENTS.md, and none of the changes above alter them.

## Owner decisions — resolved

- **Non-root container:** the owner approved necessary ownership changes after inspection
  on 2026-10-12. The implementation matches the existing appdata user/group and preserves
  all original recordings; backup and exact migration details stay in private evidence.
- **Upload feature:** the owner chose browser uploads without a login on 2026-10-12.
  Existing audio allowlists and filesystem containment are retained; no account flow was added.

## Closeout qualification — 2026-10-12

All 27 original checkbox items are resolved, including the 12 previously open items.
Historical 2026-08-18 dependency/security assessments above remain dated evidence;
this closeout does not claim a new dependency or vulnerability audit.

- Windows regression suite: 69 passed, 3 skipped. All three symlink tests execute on Linux.
- Linux container regression suite: 72 passed. JavaScript syntax and Compose configuration pass.
- Isolated empty-appdata Compose startup runs as UID 99/GID 100; browser upload/playback,
  shared settings, filtering, volume and stop controls work. Settings and recordings survive
  container recreation. Dark/mobile/reduced-motion and secure-origin offline journeys pass.
- `/health`, catalog, settings, audio, favicon, manifest and installation assets are exercised.
- All 82 pre-existing deployment files were checksum-verified after the narrow ownership change.
- Physical tablet installation and subjective listening/usability acceptance are not inferred
  from these checks. Plain HTTP cannot provide the browser's offline/installable mode.
- Release/Unraid image identities, backups, preserved template/autostart, container-recreation
  results and targeted test-artifact cleanup are retained in private delivery evidence and
  Houston's report; installation-specific values are excluded from this repository.

The existing reporting plan/task/check IDs are retained. Reporting scope revision 2 reflects
resolved wording, corrected source anchors and implementation authorization; no task or
acceptance check was added, removed or replaced. No successor plan is introduced.
