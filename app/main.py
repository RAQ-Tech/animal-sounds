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


def _global_chomp_dir() -> Path:
    return _audio_root() / "chomp"


def _animal_chomp_dir(animal_id: str) -> Path:
    return _audio_root() / animal_id / "chomp"


def _ensure_audio_directories() -> None:
    """Create the per-animal audio folders.

    Tolerates a read-only or full volume: the app can still serve whatever
    already exists, so a bad mount must not take down /api/audio.
    """
    try:
        audio_root = _audio_root()
        audio_root.mkdir(parents=True, exist_ok=True)
        _global_chomp_dir().mkdir(parents=True, exist_ok=True)
        for animal in ANIMALS:
            animal_dir = audio_root / animal["id"]
            animal_dir.mkdir(parents=True, exist_ok=True)
            (animal_dir / "chomp").mkdir(parents=True, exist_ok=True)
    except OSError as error:
        app.logger.warning("Could not create audio directories under %s: %s", _audio_root(), error)


def _is_allowed_audio_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in ALLOWED_AUDIO_EXTENSIONS


def _is_safe_audio_filename(filename: str) -> bool:
    return bool(filename) and "/" not in filename and "\\" not in filename and filename not in {".", ".."}


def _servable_audio_file(directory: Path, filename: str) -> Path | None:
    """Return the path only if it is safe to serve from ``directory``.

    This is the single gate used by both the audio index and the serving
    routes, so the two cannot disagree about a file: anything listed is
    fetchable, and anything fetchable is listed.

    Rejects unsafe filenames, disallowed extensions, non-files, and symlinks
    resolving outside ``directory`` -- send_from_directory blocks ".." in the
    URL but still follows links on disk.
    """
    if not _is_safe_audio_filename(filename):
        return None

    if Path(filename).suffix.lower() not in ALLOWED_AUDIO_EXTENSIONS:
        return None

    candidate = directory / filename
    if not _is_allowed_audio_file(candidate):
        return None

    try:
        if not candidate.resolve(strict=True).is_relative_to(directory.resolve(strict=True)):
            return None
    except OSError:
        return None

    return candidate


def _audio_files_in_dir(directory: Path, endpoint: str, **url_values: str) -> list[dict[str, str]]:
    if not directory.exists():
        return []

    try:
        entries = sorted(directory.iterdir(), key=lambda item: item.name.lower())
    except OSError:
        return []

    files = []
    for path in entries:
        if _servable_audio_file(directory, path.name) is None:
            continue
        files.append(
            {
                "name": path.name,
                "url": url_for(
                    endpoint,
                    filename=path.name,
                    **url_values,
                ),
            }
        )
    return files


def _audio_files_for_animal(animal_id: str) -> list[dict[str, str]]:
    return _audio_files_in_dir(_audio_root() / animal_id, "config_audio_file", animal_id=animal_id)


def _global_chomp_files() -> list[dict[str, str]]:
    return _audio_files_in_dir(_global_chomp_dir(), "config_chomp_audio_file")


def _chomp_files_for_animal(animal_id: str) -> list[dict[str, str]]:
    return _audio_files_in_dir(
        _animal_chomp_dir(animal_id),
        "config_animal_chomp_audio_file",
        animal_id=animal_id,
    )


def _audio_index() -> dict[str, object]:
    _ensure_audio_directories()
    animals = {}
    for animal in ANIMALS:
        files = _audio_files_for_animal(animal["id"])
        chomp_files = _chomp_files_for_animal(animal["id"])
        animals[animal["id"]] = {
            "count": len(files),
            "files": files,
            "chomp": {
                "count": len(chomp_files),
                "files": chomp_files,
            },
        }
    global_chomp_files = _global_chomp_files()
    return {
        "allowed_extensions": list(ALLOWED_AUDIO_EXTENSIONS),
        "animals": animals,
        "effects": {
            "chomp": {
                "count": len(global_chomp_files),
                "files": global_chomp_files,
            },
        },
    }


_ensure_audio_directories()


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


@app.get("/config/audio/chomp/<filename>")
def config_chomp_audio_file(filename: str):
    chomp_dir = _global_chomp_dir()
    if _servable_audio_file(chomp_dir, filename) is None:
        abort(404)

    return send_from_directory(chomp_dir, filename, conditional=True)


@app.get("/config/audio/<animal_id>/chomp/<filename>")
def config_animal_chomp_audio_file(animal_id: str, filename: str):
    if animal_id not in ANIMAL_IDS:
        abort(404)

    animal_chomp_dir = _animal_chomp_dir(animal_id)
    if _servable_audio_file(animal_chomp_dir, filename) is None:
        abort(404)

    return send_from_directory(animal_chomp_dir, filename, conditional=True)


@app.get("/config/audio/<animal_id>/<filename>")
def config_audio_file(animal_id: str, filename: str):
    if animal_id not in ANIMAL_IDS:
        abort(404)

    animal_dir = _audio_root() / animal_id
    if _servable_audio_file(animal_dir, filename) is None:
        abort(404)

    return send_from_directory(animal_dir, filename, conditional=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
