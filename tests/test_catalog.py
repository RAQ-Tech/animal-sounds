"""Catalog integrity, including the Python-to-JavaScript contract.

Adding an animal means editing animals.py, adding an SVG, and adding a matching
method in app.js. Nothing at runtime checks that those three agree -- a mismatch
shows up as a card that renders but stays silent, or a broken image. These tests
are that check.
"""

import re

from conftest import ANIMALS, APP_DIR


def test_animal_ids_are_unique():
    ids = [animal["id"] for animal in ANIMALS]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    assert not duplicates, f"duplicate animal ids: {duplicates}"


def test_every_animal_has_required_fields():
    required = {"id", "name", "sound_label", "image_path", "sound_pattern"}
    for animal in ANIMALS:
        missing = required - set(animal)
        assert not missing, f"{animal.get('id')} is missing {sorted(missing)}"


def test_every_animal_has_an_svg():
    missing = [
        animal["id"]
        for animal in ANIMALS
        if not (APP_DIR / "static" / animal["image_path"]).is_file()
    ]
    assert not missing, f"animals whose SVG file does not exist: {missing}"


def test_no_orphan_svgs():
    known = {animal["image_path"].split("/")[-1] for animal in ANIMALS}
    on_disk = {path.name for path in (APP_DIR / "static" / "animals").glob("*.svg")}
    orphans = sorted(on_disk - known)
    assert not orphans, f"SVG files with no matching animal entry: {orphans}"


def _implemented_sound_patterns() -> set[str]:
    source = (APP_DIR / "static" / "app.js").read_text(encoding="utf-8")
    block = re.search(r"const soundPatterns = \{(.*?)\n  \};", source, re.S)
    assert block, "could not locate the soundPatterns object in app.js"
    return set(re.findall(r'^    "?([a-z-]+)"?\(context, start\)', block.group(1), re.M))


def test_every_sound_pattern_is_implemented_in_javascript():
    declared = {animal["sound_pattern"] for animal in ANIMALS}
    missing = sorted(declared - _implemented_sound_patterns())
    assert not missing, (
        f"sound patterns declared in animals.py with no method in app.js: {missing} "
        f"-- those cards will render but stay silent"
    )


def test_no_unused_sound_patterns_in_javascript():
    declared = {animal["sound_pattern"] for animal in ANIMALS}
    unused = sorted(_implemented_sound_patterns() - declared)
    assert not unused, f"sound patterns implemented in app.js but unused by animals.py: {unused}"
