import numpy as np

from doorlock import db


def test_known_face_inside_threshold_opens(engine):
    assert engine.decide(1, 40, now=100) == "granted"


def test_far_match_counts_as_unknown(engine):
    assert engine.decide(1, 95, now=100) == "denied"


def test_no_model_yet_is_unknown(engine):
    assert engine.decide(None, None, now=100) == "denied"


def test_cooldown_stops_repeat_unlocks(engine):
    assert engine.decide(1, 40, now=100) == "granted"
    assert engine.decide(1, 40, now=105) is None
    assert engine.decide(1, 40, now=111) == "granted"


def test_cooldown_is_per_person(engine):
    assert engine.decide(1, 40, now=100) == "granted"
    assert engine.decide(2, 40, now=101) == "granted"
    assert engine.decide(None, None, now=102) == "denied"


def test_granted_unlocks_and_logs(engine):
    pid = db.add_person("Ali", "Resident")
    engine.act("granted", pid, 42.3, np.zeros((10, 10, 3), np.uint8))
    assert engine.door.unlocks == [engine.settings["unlock_seconds"]]
    e = db.events()[0]
    assert (e["kind"], e["name"], e["distance"]) == ("granted", "Ali", 42.3)


def test_denied_sounds_alarm_and_saves_snapshot(engine, data_dir):
    engine.act("denied", None, None, np.zeros((10, 10, 3), np.uint8))
    assert engine.door.alarms == 1
    e = db.events()[0]
    assert e["kind"] == "denied" and e["name"] == "Unknown"
    assert (data_dir / "snapshots" / e["snapshot"]).exists()


def test_remote_unlock_is_logged(engine):
    engine.remote_unlock("Admin")
    assert engine.door.unlocks and db.events()[0]["kind"] == "remote"
    assert db.today_counts()["remote"] == 1
