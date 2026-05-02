import os
from datetime import datetime, timezone

from flask import Flask, jsonify, render_template, url_for

from animals import ANIMALS


APP_NAME = os.getenv("APP_NAME", "Animal Sounds")
APP_ENV = os.getenv("APP_ENV", "production")
LOG_LEVEL = os.getenv("LOG_LEVEL", "info")
CONFIG_PATH = os.getenv("CONFIG_PATH", "/config")

app = Flask(__name__, static_folder="static", template_folder="templates")


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
            "description": "Offline-friendly farm animal picture and sound WebUI.",
            "animal_count": len(ANIMALS),
            "paths": {
                "config": CONFIG_PATH,
            },
        }
    )


@app.get("/api/animals")
def api_animals():
    return jsonify({"animals": _animal_payload()})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
