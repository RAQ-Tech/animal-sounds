"""Shared test setup.

``app/`` is a flat module directory, not a package -- ``main.py`` does
``from animals import ANIMALS`` -- so it goes on ``sys.path`` directly.
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest

APP_DIR = Path(__file__).resolve().parent.parent / "app"
sys.path.insert(0, str(APP_DIR))

# main.py creates its audio folders at import time from CONFIG_PATH. Point that
# at a throwaway directory so importing the app never writes into a real
# /config -- on Windows the default resolves to C:\config.
os.environ["CONFIG_PATH"] = tempfile.mkdtemp(prefix="animal-sounds-tests-")

import main  # noqa: E402
from animals import ANIMALS  # noqa: E402

__all__ = ["main", "ANIMALS", "APP_DIR"]


@pytest.fixture
def client():
    main.app.config["TESTING"] = True
    return main.app.test_client()


@pytest.fixture
def config_dir(tmp_path, monkeypatch):
    """Point the app at an empty, per-test config directory."""
    monkeypatch.setattr(main, "CONFIG_PATH", str(tmp_path))
    return tmp_path


@pytest.fixture
def cow_audio(config_dir):
    """A config directory holding one real audio file for the cow."""
    directory = config_dir / "audio" / "cow"
    directory.mkdir(parents=True)
    (directory / "moo.mp3").write_bytes(b"ID3fake-audio")
    (config_dir / "secret.txt").write_text("SENSITIVE")
    return config_dir
