"""Persistent writes must work without losing existing recordings or settings."""

import io
import json
from pathlib import Path
from unittest import mock

import pytest

from conftest import main


def upload(client, name="voice.wav", data=b"RIFFaudio", animal="cow", kind="sound"):
    return client.post("/api/audio/upload", data={
        "animal_id": animal, "kind": kind, "file": (io.BytesIO(data), name),
    })


def test_upload_is_listed_playable_and_never_overwrites(client, config_dir):
    first = upload(client)
    second = upload(client, data=b"RIFFsecond")
    assert first.status_code == second.status_code == 201
    assert first.json["filename"] != second.json["filename"]
    files = client.get("/api/audio").json["animals"]["cow"]["files"]
    assert len(files) == 2
    assert {client.get(file["url"]).data for file in files} == {b"RIFFaudio", b"RIFFsecond"}


def test_chomp_upload_uses_existing_chomp_index(client, config_dir):
    assert upload(client, kind="chomp").status_code == 201
    chomp = client.get("/api/audio").json["animals"]["cow"]["chomp"]
    assert chomp["count"] == 1
    assert client.get(chomp["files"][0]["url"]).data == b"RIFFaudio"


@pytest.mark.parametrize("kwargs", [
    {"name": "../escape.wav"}, {"name": "bad.exe"}, {"animal": "unknown"},
    {"kind": "unknown"}, {"data": b""},
])
def test_bad_uploads_fail_without_creating_files(client, config_dir, kwargs):
    assert upload(client, **kwargs).status_code == 400
    assert not list(config_dir.rglob("*.wav"))


def test_oversize_upload_returns_a_useful_error(client, config_dir, monkeypatch):
    monkeypatch.setitem(main.app.config, "MAX_CONTENT_LENGTH", 1024)
    response = upload(client, data=b"x" * 2048)
    assert response.status_code == 413
    assert response.json["error"]


def test_unwritable_upload_does_not_break_the_app(client, config_dir, monkeypatch):
    monkeypatch.setattr(Path, "mkdir", mock.Mock(side_effect=PermissionError()))
    assert upload(client).status_code == 503
    assert client.get("/health").status_code == 200


def test_upload_rejects_a_directory_link_outside_config(client, config_dir, tmp_path):
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir()
    audio = config_dir / "audio"
    audio.mkdir()
    try:
        (audio / "cow").symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"cannot create a symlink: {exc}")
    assert upload(client).status_code == 400
    assert not list(outside.iterdir())


def test_settings_survive_fresh_read_and_partial_updates(client, config_dir):
    assert client.get("/api/settings").json == {"sound_source": "generated", "volume": 0.75}
    assert client.patch("/api/settings", json={"sound_source": "local"}).status_code == 200
    assert client.patch("/api/settings", json={"volume": 0}).status_code == 200
    saved = {"sound_source": "local", "volume": 0}
    assert client.get("/api/settings").json == saved
    assert json.loads((config_dir / "settings.json").read_text()) == saved


@pytest.mark.parametrize("data", [[], {}, {"sound_source": []}, {"sound_source": "other"},
                                       {"volume": True}, {"volume": 2}, {"path": "elsewhere"}])
def test_invalid_settings_preserve_the_saved_choice(client, config_dir, data):
    client.patch("/api/settings", json={"sound_source": "local"})
    assert client.patch("/api/settings", json=data).status_code == 400
    assert client.get("/api/settings").json["sound_source"] == "local"


def test_corrupt_settings_have_safe_defaults(client, config_dir):
    (config_dir / "settings.json").write_text('{"sound_source": [], "volume": null}')
    assert client.get("/api/settings").json == main.SETTINGS_DEFAULTS
    (config_dir / "settings.json").write_text("broken")
    assert client.get("/api/settings").json == main.SETTINGS_DEFAULTS


def test_failed_settings_save_preserves_previous_settings(client, config_dir, monkeypatch):
    client.patch("/api/settings", json={"sound_source": "local"})
    monkeypatch.setattr(Path, "replace", mock.Mock(side_effect=PermissionError()))
    assert client.patch("/api/settings", json={"sound_source": "generated"}).status_code == 503
    assert client.get("/api/settings").json["sound_source"] == "local"
    assert not list(config_dir.glob(".settings-*"))


def test_offline_manifest_and_worker_serve_all_bundled_assets(client):
    manifest = client.get("/manifest.webmanifest")
    assert manifest.status_code == 200
    assert manifest.json["display"] == "standalone"
    for icon in manifest.json["icons"]:
        assert client.get(icon["src"]).status_code == 200
    worker = client.get("/service-worker.js")
    assert worker.status_code == 200
    assert worker.headers["Cache-Control"] == "no-cache"
    assert b'/config/' in worker.data and b'/api/' in worker.data
    assert client.get("/favicon.ico").status_code == 200
