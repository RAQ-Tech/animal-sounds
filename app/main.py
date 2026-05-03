import os
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, abort, jsonify, render_template, send_from_directory, url_for

from animals import ANIMALS


APP_NAME = os.getenv("APP_NAME", "Animal Sounds")
APP_ENV = os.getenv("APP_ENV", "production")
LOG_LEVEL = os.getenv("LOG_LEVEL", "info")
CONFIG_PATH = os.getenv("CONFIG_PATH", "/config")
ALLOWED_AUDIO_EXTENSIONS = (".aac", ".m4a", ".mp3", ".ogg", ".wav", ".webm")

app = Flask(__name__, static_folder="static", template_folder="templates")
ANIMAL_IDS = {animal["id"] for animal in ANIMALS}


def _audio_root() -> Path:
    return Path(CONFIG_PATH) / "audio"


def _ensure_audio_directories() -> None:
    audio_root = _audio_root()
    audio_root.mkdir(parents=True, exist_ok=True)
    for animal in ANIMALS:
        (audio_root / animal["id"]).mkdir(parents=True, exist_ok=True)


def _is_allowed_audio_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in ALLOWED_AUDIO_EXTENSIONS


def _audio_files_for_animal(animal_id: str) -> list[dict[str, str]]:
    animal_dir = _audio_root() / animal_id
    if not animal_dir.exists():
        return []

    files = []
    for path in sorted(animal_dir.iterdir(), key=lambda item: item.name.lower()):
        if not _is_allowed_audio_file(path):
            continue
        files.append(
            {
                "name": path.name,
                "url": url_for(
                    "config_audio_file",
                    animal_id=animal_id,
                    filename=path.name,
                ),
            }
        )
    return files


def _audio_index() -> dict[str, object]:
    _ensure_audio_directories()
    animals = {}
    for animal in ANIMALS:
        files = _audio_files_for_animal(animal["id"])
        animals[animal["id"]] = {
            "count": len(files),
            "files": files,
        }
    return {
        "allowed_extensions": list(ALLOWED_AUDIO_EXTENSIONS),
        "animals": animals,
    }


try:
    _ensure_audio_directories()
except OSError:
    pass


def _animal_payload(include_sound_pattern: bool = False) -> list[dict[str, str]]:
    animals = []
    for animal in ANIMALS:
        item = {
            "id": animal["id"],
            "name": animal["name"],
            "sound_label": animal["sound_label"],
            "image_url": url_for("static", filename=animal["image_path"]),
        }
        if include_sound_pattern:
            item["sound_pattern"] = animal["sound_pattern"]
        animals.append(item)
    return animals


@app.get("/")
def home():
    return render_template(
        "index.html",
        app_name=APP_NAME,
        app_env=APP_ENV,
        log_level=LOG_LEVEL,
        config_path=CONFIG_PATH,
        animals=_animal_payload(include_sound_pattern=True),
    )


@app.get("/health")
def health():
    return jsonify(
        {
            "status": "healthy",
            "app": APP_NAME,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        }
    )


@app.get("/api/info")
def api_info():
    return jsonify(
        {
            "app_name": APP_NAME,
            "environment": APP_ENV,
            "log_level": LOG_LEVEL,
            "description": "Offline-friendly animal picture and sound WebUI.",
            "animal_count": len(ANIMALS),
            "paths": {
                "config": CONFIG_PATH,
            },
        }
    )


@app.get("/api/animals")
def api_animals():
    return jsonify({"animals": _animal_payload()})


@app.get("/api/audio")
def api_audio():
    return jsonify(_audio_index())


@app.get("/config/audio/<animal_id>/<path:filename>")
def config_audio_file(animal_id: str, filename: str):
    if animal_id not in ANIMAL_IDS:
        abort(404)

    if not filename or "/" in filename or "\\" in filename or filename in {".", ".."}:
        abort(404)

    if Path(filename).suffix.lower() not in ALLOWED_AUDIO_EXTENSIONS:
        abort(404)

    animal_dir = _audio_root() / animal_id
    audio_file = animal_dir / filename
    if not _is_allowed_audio_file(audio_file):
        abort(404)

    return send_from_directory(animal_dir, filename, conditional=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
