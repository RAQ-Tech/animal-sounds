"""Route behaviour: the shapes the UI and the healthchecks depend on."""

from pathlib import Path
from unittest import mock

from conftest import ANIMALS, main


def test_health_reports_healthy(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "healthy"


def test_health_does_not_touch_the_filesystem(client):
    """The Docker and Unraid healthchecks depend on /health staying trivial."""
    with mock.patch.object(
        main,
        "_ensure_audio_directories",
        side_effect=AssertionError("/health touched the filesystem"),
    ):
        assert client.get("/health").status_code == 200


def test_health_survives_an_unwritable_config(client, config_dir, monkeypatch):
    monkeypatch.setattr(Path, "mkdir", mock.Mock(side_effect=OSError(30, "Read-only file system")))
    assert client.get("/health").status_code == 200


def test_api_info_animal_count_matches_catalog(client):
    assert client.get("/api/info").get_json()["animal_count"] == len(ANIMALS)


def test_api_animals_matches_catalog(client):
    animals = client.get("/api/animals").get_json()["animals"]
    assert len(animals) == len(ANIMALS)
    assert {a["id"] for a in animals} == {a["id"] for a in ANIMALS}


def test_api_animals_does_not_leak_sound_pattern(client):
    """sound_pattern is an internal implementation detail of the frontend."""
    animals = client.get("/api/animals").get_json()["animals"]
    assert all("sound_pattern" not in animal for animal in animals)


def test_home_renders_a_card_for_every_animal(client):
    html = client.get("/").get_data(as_text=True)
    missing = [a["id"] for a in ANIMALS if f'data-animal-id="{a["id"]}"' not in html]
    assert not missing, f"animals missing from the rendered page: {missing}"


def test_api_audio_covers_every_animal(client):
    payload = client.get("/api/audio").get_json()
    assert set(payload["animals"]) == {a["id"] for a in ANIMALS}
    assert payload["allowed_extensions"]
