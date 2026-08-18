"""Audio serving: the only place user input reaches the filesystem.

Includes regression tests for three defects found on 2026-08-18:
  * /api/audio returned 500 when /config was read-only
  * /api/audio could advertise URLs the serving route was certain to reject
  * a symlink inside the audio folder was followed out of it
"""

from pathlib import Path
from unittest import mock

import pytest

from conftest import main


# --------------------------------------------------------------------------
# serving
# --------------------------------------------------------------------------

def test_serves_a_real_file(client, cow_audio):
    response = client.get("/config/audio/cow/moo.mp3")
    assert response.status_code == 200
    assert response.get_data() == b"ID3fake-audio"


def test_rejects_an_unknown_animal(client, cow_audio):
    assert client.get("/config/audio/wyvern/moo.mp3").status_code == 404


def test_rejects_a_disallowed_extension(client, cow_audio):
    (cow_audio / "audio" / "cow" / "notes.txt").write_text("not audio")
    assert client.get("/config/audio/cow/notes.txt").status_code == 404


def test_uppercase_extensions_are_accepted(client, cow_audio):
    (cow_audio / "audio" / "cow" / "LOUD.MP3").write_bytes(b"AUDIO")
    assert client.get("/config/audio/cow/LOUD.MP3").status_code == 200


def test_chomp_routes_serve(client, config_dir):
    shared = config_dir / "audio" / "chomp"
    shared.mkdir(parents=True)
    (shared / "crunch.wav").write_bytes(b"RIFFshared")
    assert client.get("/config/audio/chomp/crunch.wav").status_code == 200

    per_animal = config_dir / "audio" / "cow" / "chomp"
    per_animal.mkdir(parents=True)
    (per_animal / "munch.wav").write_bytes(b"RIFFanimal")
    assert client.get("/config/audio/cow/chomp/munch.wav").status_code == 200


# --------------------------------------------------------------------------
# security
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "attack",
    [
        "../secret.txt",
        "..%2fsecret.txt",
        "..%252fsecret.txt",
        "....//secret.txt",
        "%2e%2e%2fsecret.txt",
        "..\\secret.txt",
        "..%5csecret.txt",
        "/etc/passwd",
        "%2e%2e/%2e%2e/secret.txt",
    ],
)
def test_path_traversal_is_blocked(client, cow_audio, attack):
    response = client.get(f"/config/audio/cow/{attack}")
    assert response.status_code in (301, 308, 404), f"traversal not blocked: {attack}"
    assert b"SENSITIVE" not in response.get_data()


def test_symlink_out_of_the_audio_folder_is_not_served(client, config_dir):
    """Regression: send_from_directory follows symlinks, so the app checks the
    resolved path stays inside the directory."""
    cow = config_dir / "audio" / "cow"
    cow.mkdir(parents=True)
    secret = config_dir.parent / "outside_secret.txt"
    secret.write_text("SENSITIVE")

    try:
        (cow / "escape.mp3").symlink_to(secret)
    except (OSError, NotImplementedError) as exc:  # pragma: no cover - Windows
        pytest.skip(f"cannot create a symlink in this environment: {exc}")

    response = client.get("/config/audio/cow/escape.mp3")
    assert response.status_code == 404
    assert b"SENSITIVE" not in response.get_data()


def test_symlinked_file_is_not_listed_either(client, config_dir):
    cow = config_dir / "audio" / "cow"
    cow.mkdir(parents=True)
    secret = config_dir.parent / "outside_secret.mp3"
    secret.write_bytes(b"SENSITIVE")

    try:
        (cow / "escape.mp3").symlink_to(secret)
    except (OSError, NotImplementedError) as exc:  # pragma: no cover - Windows
        pytest.skip(f"cannot create a symlink in this environment: {exc}")

    listed = [f["name"] for f in client.get("/api/audio").get_json()["animals"]["cow"]["files"]]
    assert "escape.mp3" not in listed


# --------------------------------------------------------------------------
# the index and the routes must agree
# --------------------------------------------------------------------------

def test_index_is_sorted_and_every_url_resolves(client, config_dir):
    cow = config_dir / "audio" / "cow"
    cow.mkdir(parents=True)
    for name in ["z.mp3", "a.mp3", "M.mp3", "my song #1.mp3", "100% moo.mp3", "a+b.mp3"]:
        (cow / name).write_bytes(b"AUDIO")

    files = client.get("/api/audio").get_json()["animals"]["cow"]["files"]
    names = [f["name"] for f in files]
    assert names == sorted(names, key=str.lower), f"index not sorted case-insensitively: {names}"

    for entry in files:
        assert client.get(entry["url"]).status_code == 200, (
            f"/api/audio advertised {entry['url']} for {entry['name']} but it does not resolve"
        )


# Every one of these is a legal filename on Linux, which is what the container
# runs, even though Windows cannot create most of them.
LINUX_LEGAL_NAMES = [
    "back\\slash.mp3",
    "track?2.mp3",
    "star*.mp3",
    "pipe|x.mp3",
    "colon:x.mp3",
    'quote".mp3',
    "new\nline.mp3",
]


@pytest.mark.parametrize("name", LINUX_LEGAL_NAMES)
def test_listed_files_are_always_servable(config_dir, monkeypatch, name):
    """Regression: the index once listed names the route would always reject.

    Fakes the directory listing so these run on any host filesystem.
    """
    cow = config_dir / "audio" / "cow"
    cow.mkdir(parents=True)

    entry = mock.MagicMock(spec=Path)
    entry.name = name
    entry.is_file.return_value = True
    entry.suffix = Path(name).suffix

    real_iterdir = Path.iterdir

    def fake_iterdir(self):
        if self.name == "cow":
            return iter([entry])
        return real_iterdir(self)

    monkeypatch.setattr(Path, "iterdir", fake_iterdir)

    with main.app.test_request_context():
        listed = [f["name"] for f in main._audio_files_for_animal("cow")]

    if name in listed:
        assert main._servable_audio_file(cow, name) is not None, (
            f"/api/audio lists {name!r} but the serving route rejects it -- guaranteed 404"
        )


# --------------------------------------------------------------------------
# resilience
# --------------------------------------------------------------------------

def test_api_audio_survives_a_readonly_config(client, config_dir, monkeypatch):
    """Regression: this returned 500 when /config could not be written to."""
    monkeypatch.setattr(Path, "mkdir", mock.Mock(side_effect=OSError(30, "Read-only file system")))

    response = client.get("/api/audio")
    assert response.status_code == 200, (
        "/api/audio must degrade to generated sounds on a read-only /config, not 500"
    )


def test_api_audio_survives_an_unreadable_directory(client, config_dir, monkeypatch):
    cow = config_dir / "audio" / "cow"
    cow.mkdir(parents=True)
    monkeypatch.setattr(Path, "iterdir", mock.Mock(side_effect=OSError(13, "Permission denied")))

    assert client.get("/api/audio").status_code == 200


def test_existing_files_still_serve_when_config_is_readonly(client, cow_audio, monkeypatch):
    monkeypatch.setattr(Path, "mkdir", mock.Mock(side_effect=OSError(30, "Read-only file system")))

    assert client.get("/config/audio/cow/moo.mp3").status_code == 200
    listed = [f["name"] for f in client.get("/api/audio").get_json()["animals"]["cow"]["files"]]
    assert "moo.mp3" in listed
