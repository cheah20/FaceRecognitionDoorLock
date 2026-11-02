# paths, pins, settings
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = Path(os.environ.get("DOORLOCK_DATA", ROOT / "data"))
FACES = DATA / "faces"
SNAPSHOTS = DATA / "snapshots"
DB_PATH = DATA / "doorlock.db"
MODEL_PATH = DATA / "model.yml"
SETTINGS_PATH = DATA / "settings.json"

# bcm pins
PINS = {"relay": 17, "green_led": 22, "red_led": 23, "buzzer": 27}

DEFAULTS = {
    "unlock_seconds": 5,
    # LBPH gives a distance, lower is a closer match
    "match_threshold": 70,
    "cooldown_seconds": 10,
    "photos_per_person": 20,
}


def ensure_folders():
    for folder in (DATA, FACES, SNAPSHOTS):
        folder.mkdir(parents=True, exist_ok=True)


def load_settings():
    settings = dict(DEFAULTS)
    if SETTINGS_PATH.exists():
        settings.update(json.loads(SETTINGS_PATH.read_text()))
    return settings


def save_settings(new):
    settings = load_settings()
    for key, value in new.items():
        if key in DEFAULTS:
            settings[key] = type(DEFAULTS[key])(value)
    SETTINGS_PATH.write_text(json.dumps(settings, indent=2))
    return settings
