# Animal Sounds

Animal Sounds is a lightweight, offline-friendly Flask WebUI for animal pictures and generated animal noises. It is designed to run cleanly in Docker and Unraid with a fixed internal app port of `3000`.

## What It Does

- Shows 14 bundled animal illustrations: cow, horse, sheep, pig, chicken, duck, goat, donkey, dog, cat, lion, monkey, gorilla, and tiger.
- Plays a distinct generated sound when an animal card is activated.
- Includes a Throw Pokeball mode that launches a local CSS/JS animation at the next selected animal.
- Uses local HTML, CSS, JavaScript, and SVG assets only.
- Keeps `/config` reserved as the primary persistent path for future settings and app state.
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

## Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `APP_NAME` | `Animal Sounds` | UI/API app display name |
| `APP_ENV` | `production` | Environment label |
| `LOG_LEVEL` | `info` | Application log level |
| `HOST_PORT` | `8080` | Host-exposed port mapped to container `3000` |
| `CONFIG_PATH` | `/config` | Primary persistent config/state path in container |

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
├── Dockerfile
├── docker-compose.yml
├── README.md
├── unraid/
│   ├── animal-sounds-icon.png
│   └── template.xml
└── app/
    ├── animals.py
    ├── main.py
    ├── requirements.txt
    ├── static/
    │   ├── app.js
    │   ├── styles.css
    │   └── animals/
    │       ├── cat.svg
    │       ├── chicken.svg
    │       ├── cow.svg
    │       ├── dog.svg
    │       ├── donkey.svg
    │       ├── duck.svg
    │       ├── goat.svg
    │       ├── gorilla.svg
    │       ├── horse.svg
    │       ├── lion.svg
    │       ├── monkey.svg
    │       ├── pig.svg
    │       ├── sheep.svg
    │       └── tiger.svg
    └── templates/
        └── index.html
```

## Notes

- Sounds are generated in the browser with the Web Audio API. No audio files or network media are required.
- Pokeball throwing is animation-only; it does not save capture state or write to `/config`.
- The app keeps the internal container port fixed at `3000`.
- `/config` is currently reserved for future settings/state and should remain mapped in Docker/Unraid deployments.
- The UI intentionally stays framework-free to keep the project easy to extend.
