import logging
import hashlib
import json
import os
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, abort, jsonify, render_template, request, send_from_directory, url_for
from werkzeug.utils import secure_filename

from animals import ANIMALS


APP_NAME = os.getenv("APP_NAME", "Animal Sounds")
APP_ENV = os.getenv("APP_ENV", "production")
LOG_LEVEL = os.getenv("LOG_LEVEL", "info")
CONFIG_PATH = os.getenv("CONFIG_PATH", "/config")
ALLOWED_AUDIO_EXTENSIONS = (".aac", ".m4a", ".mp3", ".ogg", ".wav", ".webm")

LOG_LEVELS = {
    "critical": logging.CRITICAL,
    "error": logging.ERROR,
    "warning": logging.WARNING,
    "info": logging.INFO,
    "debug": logging.DEBUG,
}

app = Flask(__name__, static_folder="static", template_folder="templates")
ANIMAL_IDS = {animal["id"] for animal in ANIMALS}
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
SETTINGS_DEFAULTS = {"sound_source": "generated", "volume": 0.75}
SETTINGS_LOCK = threading.Lock()
UI_FILES = list(Path(app.static_folder).rglob("*")) + list((Path(app.root_path) / "templates").rglob("*"))
ASSET_VERSION = hashlib.sha256(b"".join(
    path.read_bytes() for path in sorted(UI_FILES) if path.is_file()
)).hexdigest()[:16]
ANIMAL_GROUPS = {
    "farm": {"cow", "horse", "sheep", "pig", "goat", "donkey", "dog", "cat"},
    "birds": {"chicken", "duck", "rooster", "owl", "roadrunner", "toucan"},
    "water": {"dolphin", "tree-frog", "seal", "narwhal"},
}


def _static_url(filename: str) -> str:
    return url_for("static", filename=filename, v=ASSET_VERSION)


def _read_settings() -> dict:
    try:
        data = json.loads((Path(CONFIG_PATH) / "settings.json").read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return dict(SETTINGS_DEFAULTS)
    except (OSError, ValueError):
        return dict(SETTINGS_DEFAULTS)
    source = data.get("sound_source")
    volume = data.get("volume")
    return {
        "sound_source": source if isinstance(source, str) and source in {"generated", "local"} else "generated",
        "volume": volume if type(volume) in {int, float} and 0 <= volume <= 1 else 0.75,
    }


@app.get("/api/settings")
def get_settings():
    response = jsonify(_read_settings())
    response.headers["Cache-Control"] = "no-store"
    return response


@app.patch("/api/settings")
def update_settings():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not data or set(data) - set(SETTINGS_DEFAULTS):
        return jsonify(error="Choose a sound source or volume to save."), 400
    if "sound_source" in data and not (isinstance(data["sound_source"], str) and data["sound_source"] in {"generated", "local"}):
        return jsonify(error="Choose Generated or Local Files."), 400
    if "volume" in data and not (type(data["volume"]) in {int, float} and 0 <= data["volume"] <= 1):
        return jsonify(error="Volume must be between 0 and 1."), 400
    temporary = None
    try:
        with SETTINGS_LOCK:
            settings = _read_settings() | data
            root = Path(CONFIG_PATH)
            root.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=root,
                                             prefix=".settings-", delete=False) as stream:
                temporary = Path(stream.name)
                json.dump(settings, stream, allow_nan=False)
                stream.flush()
                os.fsync(stream.fileno())
            temporary.replace(root / "settings.json")
        return jsonify(settings)
    except OSError:
        return jsonify(error="Settings could not be saved. Check the config folder permissions."), 503
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


@app.post("/api/audio/upload")
def upload_audio():
    animal_id = request.form.get("animal_id", "")
    kind = request.form.get("kind", "sound")
    upload = request.files.get("file")
    if animal_id not in ANIMAL_IDS or kind not in {"sound", "chomp"}:
        return jsonify(error="Choose an animal and sound type."), 400
    if upload is None or not _is_safe_audio_filename(upload.filename or ""):
        return jsonify(error="Choose an audio file with a plain filename."), 400
    filename = secure_filename(upload.filename)
    if not filename or Path(filename).suffix.lower() not in ALLOWED_AUDIO_EXTENSIONS:
        return jsonify(error="Choose MP3, WAV, OGG, M4A, AAC, or WebM audio."), 400
    directory = _animal_chomp_dir(animal_id) if kind == "chomp" else _audio_root() / animal_id
    temporary = None
    try:
        audio_root = _audio_root().resolve()
        if not audio_root.is_relative_to(Path(CONFIG_PATH).resolve()) or not directory.resolve().is_relative_to(audio_root):
            return jsonify(error="The audio folder is outside the app's config folder."), 400
        directory.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=directory, prefix=".audio-upload-", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            upload.save(stream)
            stream.flush()
            os.fsync(stream.fileno())
        if temporary.stat().st_size == 0:
            return jsonify(error="That file is empty. Choose a recording with sound."), 400
        # Keep browser-created recordings usable from the existing appdata share.
        temporary.chmod(0o664)
        # Publish complete bytes atomically without overwriting recordings or symlinks.
        for suffix in range(10000):
            name = filename if suffix == 0 else f"{Path(filename).stem}-{suffix}{Path(filename).suffix}"
            target = directory / name
            try:
                os.link(temporary, target)
            except FileExistsError:
                continue
            break
        else:
            return jsonify(error="Too many files have this name. Rename your file."), 409
        return jsonify(animal_id=animal_id, kind=kind, filename=target.name), 201
    except OSError:
        return jsonify(error="Audio could not be saved. Check the audio folder permissions."), 503
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


@app.errorhandler(413)
def upload_too_large(error):
    return jsonify(error="Choose a file smaller than 16 MB."), 413


@app.get("/favicon.ico")
def favicon():
    return send_from_directory(app.static_folder, "icon.svg", mimetype="image/svg+xml")


@app.get("/manifest.webmanifest")
def manifest():
    response = jsonify(name=APP_NAME, short_name="Animal Sounds", id="/", start_url="/",
                       scope="/", display="standalone", background_color="#dff6ff",
                       theme_color="#16353a", icons=[
                           {"src": _static_url("icon-192.png"), "sizes": "192x192", "type": "image/png"},
                           {"src": _static_url("icon-512.png"), "sizes": "512x512", "type": "image/png"},
                       ])
    response.mimetype = "application/manifest+json"
    return response


@app.get("/service-worker.js")
def service_worker():
    assets = ["/", "/manifest.webmanifest", _static_url("app.js"), _static_url("styles.css"),
              _static_url("icon.svg"), _static_url("icon-192.png"), _static_url("icon-512.png")]
    assets.extend(_static_url(animal["image_path"]) for animal in ANIMALS)
    response = app.response_class(render_template("service-worker.js", assets=assets,
                                  version=ASSET_VERSION), mimetype="application/javascript")
    response.headers["Cache-Control"] = "no-cache"
    return response


def _configure_logging() -> str:
    """Apply LOG_LEVEL to the root logger; return the level actually in effect.

    An unrecognised value falls back to info rather than failing to start, and
    the effective level is what gets reported by /api/info -- reporting the
    requested value would be a lie when it was not understood.
    """
    requested = LOG_LEVEL.strip().lower()
    level = LOG_LEVELS.get(requested)
    logging.basicConfig(
        level=level if level is not None else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if level is None:
        app.logger.warning(
            "Unknown LOG_LEVEL %r; expected one of %s. Falling back to info.",
            LOG_LEVEL,
            ", ".join(sorted(LOG_LEVELS)),
        )
        return "info"

    app.logger.setLevel(level)
    return requested


EFFECTIVE_LOG_LEVEL = _configure_logging()


@app.after_request
def _log_request(response):
    """Basic access logging; the app had none.

    /health is skipped: the container healthcheck hits it every 30 seconds and
    would drown out everything worth reading.
    """
    if request.path != "/health":
        app.logger.info("%s %s -> %s", request.method, request.path, response.status_code)
    return response


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
            "image_url": _static_url(animal["image_path"]),
        }
        if include_sound_pattern:
            item["sound_pattern"] = animal["sound_pattern"]
            item["group"] = next((group for group, ids in ANIMAL_GROUPS.items()
                                  if animal["id"] in ids), "wild")
        animals.append(item)
    return animals


@app.get("/")
def home():
    return render_template(
        "index.html",
        app_name=APP_NAME,
        app_env=APP_ENV,
        log_level=EFFECTIVE_LOG_LEVEL,
        config_path=CONFIG_PATH,
        animals=_animal_payload(include_sound_pattern=True),
        static_url=_static_url,
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
            "log_level": EFFECTIVE_LOG_LEVEL,
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
