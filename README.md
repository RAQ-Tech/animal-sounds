# Animal Sounds

Animal Sounds is a lightweight, offline-friendly Flask WebUI for animal pictures and generated animal noises. It is designed to run cleanly in Docker and Unraid with a fixed internal app port of `3000`.

## What It Does

- Shows 25 bundled animal illustrations: cow, horse, sheep, pig, chicken, duck, goat, donkey, dog, cat, lion, monkey, gorilla, tiger, dolphin, elephant, cricket, coyote, rooster, tree frog, owl, seal, roadrunner, toucan, and narwhal.
- Plays a distinct generated sound when an animal card is activated.
- Can switch to local audio files dropped into `/config/audio/<animal-id>/`.
- Includes a Throw Pokeball mode that launches a local CSS/JS animation at the next selected animal.
- Includes a fixed feed pile with draggable pellets and chomp sounds.
- Uses local HTML, CSS, JavaScript, and SVG assets only.
- Saves shared sound-source and volume settings in `/config/settings.json`.
- Uploads animal and chomp recordings from the browser without a login, preserving existing files.
- Offers volume/stop controls, animal-group filters, local-file counts, dark mode, and reduced motion.
- Supports home-screen installation and an offline generated-sound board on HTTPS or localhost.
- Provides fast health and catalog API endpoints.

## Local Docker Quick Start

1. Copy the example env file:

   ```bash
   cp .env.example .env
   ```

2. Build and run:

   ```bash
   docker compose up --build
   ```

3. Open the WebUI:

   ```text
   http://localhost:8080
   ```

4. Check health:

   ```text
   http://localhost:8080/health
   ```

   Expected response includes `"status": "healthy"`.

## Endpoints

| Route | Purpose |
|---|---|
| `/` | Animal picture and sound WebUI |
| `/health` | Container healthcheck endpoint |
| `/api/info` | App metadata, config path, and animal count |
| `/api/animals` | Public animal catalog with names, labels, and image URLs |
| `/api/audio` | Local audio file index and supported extensions |
| `/config/audio/<animal-id>/<filename>` | Safe local audio file serving for known animals |
| `/config/audio/chomp/<filename>` | Safe shared chomp audio file serving |
| `/config/audio/<animal-id>/chomp/<filename>` | Safe per-animal chomp audio file serving |

## Local Audio Files

The app creates one folder per animal under `/config/audio/`:

```text
/config/audio/
├── chomp/
├── cat/
├── chicken/
├── cow/
├── coyote/
├── cricket/
├── dog/
├── dolphin/
├── donkey/
├── duck/
├── elephant/
├── goat/
├── gorilla/
├── horse/
├── lion/
├── monkey/
├── owl/
├── pig/
├── rooster/
├── roadrunner/
├── toucan/
├── narwhal/
├── seal/
├── sheep/
├── tiger/
└── tree-frog/
```

Each animal folder also gets a `chomp/` subfolder for per-animal feeding sounds:

```text
/config/audio/cow/chomp/
/config/audio/dog/chomp/
/config/audio/tree-frog/chomp/
```

Drop audio files into the matching animal folder. Supported file types are:

```text
.mp3 .wav .ogg .m4a .aac .webm
```

A fresh installation starts in **Generated** mode at 75% volume. The mode and volume are shared by browsers and saved on the server; existing browser-only mode is used as an offline fallback. Switch to **Local Files** mode to play files from `/config/audio`. If an animal has more than one file, repeated clicks cycle through the files in filename order. If an animal has no local files, the generated sound plays as a fallback.

For feeding, drag a pellet from the fixed feed pile onto an animal. Feeding uses per-animal chomp files first, then shared files from `/config/audio/chomp/`, then a generated chomp fallback. Keyboard users can focus the feed pile, press Enter or Space, then activate an animal card to feed it.

## Uploads and playback

Open **Add your own sounds**, choose an animal, choose **Animal sound** or **Chomp sound**, select a supported audio file smaller than 16 MB, and press **Upload sound**. No login is required. Duplicate filenames receive a numbered suffix; existing recordings are never overwritten. A successful upload refreshes counts and switches to **Local Files** mode. Local files cycle in filename order.

The volume slider affects both generated and recorded sounds. **Stop all sounds** stops animal and chomp playback. Group buttons filter the board; **All animals** restores every card. Dark mode follows your device, and reduced-motion mode removes decorative throwing/chomping movement.

## Offline installation

On HTTPS or localhost, the browser can install the app from its install menu; supporting browsers also show **Install app**. On iPhone/iPad, use Safari's **Add to Home Screen**. Load the board once while connected before going offline. The offline board includes all 25 pictures and generated sounds. Uploads, shared settings, and personal recordings require a connection; personal audio is not copied into the offline cache.

A plain HTTP address on your LAN continues to work as an online soundboard, but browsers do not permit its offline worker. This release does not configure HTTPS, certificates, or a reverse proxy on your server. [Browser installation requirements](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Making_PWAs_installable).

## Container file ownership

The image runs as UID `99`, GID `100`, matching common Unraid appdata ownership. Compose can override these with `APP_UID` and `APP_GID` in `.env` to match an existing Linux folder. These variables are Compose options, not settings that change the running process inside an already-created container. Unraid can override the same identity through Docker's `--user UID:GID` extra parameter when needed.

For an existing installation, back up appdata and inspect ownership before updating. The configured user must be able to create folders and files under `/config`; preserve recordings and unrelated files. Correct only the affected appdata permissions if needed, rather than changing an entire share. New Docker named volumes inherit the image's prepared `/config` ownership. With a fresh Linux bind mount, create the host directory with the intended owner before starting Compose. Windows Docker Desktop manages bind-mount permissions itself.

## Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `APP_NAME` | `Animal Sounds` | UI/API app display name |
| `APP_ENV` | `production` | Environment label |
| `LOG_LEVEL` | `info` | Application log level |
| `HOST_PORT` | `8080` | Host-exposed port mapped to container `3000` |
| `CONFIG_PATH` | `/config` | Primary persistent path; Compose and Unraid map `/config` read/write |
| `APP_UID` | `99` | Optional Compose runtime user ID; use the existing Linux folder owner |
| `APP_GID` | `100` | Optional Compose runtime group ID |

## Unraid Install

Use the template at:

```text
https://raw.githubusercontent.com/RAQ-Tech/animal-sounds/main/unraid/template.xml
```

Required values:

- **WebUI Port**: defaults to `8080`, mapped to internal container port `3000`.
- **App Config (Primary)**: defaults to `/mnt/user/appdata/animal-sounds`, mapped to `/config`.

After the container starts, open the WebUI from the Docker tab or browse directly to:

```text
http://<your-unraid-ip>:8080
```

Health check:

```text
http://<your-unraid-ip>:8080/health
```

## Project Structure

```text
.
├── .github/                 # CI publication gates and Dependabot
├── .dockerignore
├── .env.example
├── AGENTS.md
├── BACKLOG.md               # Existing phased plan and qualification record
├── Dockerfile
├── docker-compose.yml
├── README.md
├── tests/                   # Route, audio, settings, upload and catalog tests
├── unraid/
│   ├── animal-sounds-icon.png
│   └── template.xml
└── app/
    ├── animals.py
    ├── main.py
    ├── requirements.txt
    ├── requirements-dev.txt
    ├── static/
    │   ├── app.js
    │   ├── styles.css
    │   ├── icon.svg
    │   ├── icon-192.png
    │   ├── icon-512.png
    │   └── animals/          # One SVG for each of the 25 catalog entries
    └── templates/
        ├── index.html
        └── service-worker.js
```

## Verification

```bash
python -m pytest tests -q
node --check app/static/app.js
docker compose config --quiet
docker compose up --build
```

Unit tests cover upload preservation, invalid/oversize uploads, folder containment, persistent settings and existing audio behavior. Linux CI also runs symlink tests that skip on Windows. The release workflow builds and smoke-tests the non-root container before publishing.

## Notes

- Sounds are generated in the browser with the Web Audio API. No audio files or network media are required.
- Local audio files are user-managed under `/config/audio/<animal-id>/` and are not committed to the repo.
- Chomp audio files are user-managed under `/config/audio/chomp/` and `/config/audio/<animal-id>/chomp/`.
- Pokeball throwing is animation-only; it does not save capture state or write to `/config`.
- The app keeps the internal container port fixed at `3000` and exposes it on the configured host port.
- `/config` stores shared settings and recordings and must remain mapped read/write across Docker/Unraid updates. Static asset URLs include a content version to avoid stale scripts after updates.
- The UI intentionally stays framework-free to keep the project easy to extend.
