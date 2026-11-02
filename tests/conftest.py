import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class FakeCamera:
    source = "test"

    def read(self):
        return np.zeros((480, 640, 3), np.uint8)


class FakeDoor:
    simulated = True
    unlocked_until = 0.0
    is_open = False

    def __init__(self):
        self.unlocks, self.alarms = [], 0

    def unlock(self, seconds):
        self.unlocks.append(seconds)

    def alarm(self):
        self.alarms += 1

    def pins(self):
        return {"relay": False, "green_led": False, "red_led": False, "buzzer": False}


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    from doorlock import config, db

    monkeypatch.setattr(config, "DATA", tmp_path)
    monkeypatch.setattr(config, "FACES", tmp_path / "faces")
    monkeypatch.setattr(config, "SNAPSHOTS", tmp_path / "snapshots")
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "doorlock.db")
    monkeypatch.setattr(config, "MODEL_PATH", tmp_path / "model.yml")
    monkeypatch.setattr(config, "SETTINGS_PATH", tmp_path / "settings.json")
    db.init()
    return tmp_path


@pytest.fixture
def engine(data_dir):
    from doorlock.engine import Engine

    return Engine(FakeCamera(), FakeDoor())
