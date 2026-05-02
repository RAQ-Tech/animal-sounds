import os
from datetime import datetime, timezone

from flask import Flask, jsonify, render_template


def _as_bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


APP_NAME = os.getenv("APP_NAME", "Starter WebUI App")
APP_ENV = os.getenv("APP_ENV", "production")
LOG_LEVEL = os.getenv("LOG_LEVEL", "info")
FEATURE_PLACEHOLDER = _as_bool(os.getenv("FEATURE_PLACEHOLDER", "true"), True)
CONFIG_PATH = os.getenv("CONFIG_PATH", "/config")

app = Flask(__name__, static_folder="static", template_folder="templates")


@app.get("/")
def home():
    return render_template(
        "index.html",
        app_name=APP_NAME,
        app_env=APP_ENV,
        log_level=LOG_LEVEL,
        feature_placeholder=FEATURE_PLACEHOLDER,
        config_path=CONFIG_PATH,
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
            "feature_placeholder_enabled": FEATURE_PLACEHOLDER,
            "paths": {
                "config": CONFIG_PATH,
            },
            "message": "Starter API route is working.",
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
