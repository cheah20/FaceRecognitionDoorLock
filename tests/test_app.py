import io

import pytest

from doorlock import db


@pytest.fixture
def client(engine, monkeypatch):
    monkeypatch.setenv("DOORLOCK_PASSWORD", "secret1")
    from app import create_app

    app = create_app(engine, start=False)
    app.config["TESTING"] = True
    return app.test_client()


def login(client, password="secret1"):
    return client.post("/login", data={"password": password})


def test_pages_need_login(client):
    for url in ("/", "/people", "/logs", "/settings", "/api/status"):
        r = client.get(url)
        assert r.status_code == 302 and "/login" in r.headers["Location"]


def test_unlock_needs_login(client):
    assert client.post("/api/unlock").status_code == 302


def test_wrong_password(client):
    assert "Wrong password" in login(client, "nope").get_data(as_text=True)


def test_dashboard_and_status(client):
    login(client)
    assert client.get("/").status_code == 200
    s = client.get("/api/status").get_json()
    assert s["open"] is False and s["simulated"] is True and set(s["pins"]) == {"relay", "green_led", "red_led", "buzzer"}


def test_remote_unlock(client, engine):
    login(client)
    assert client.post("/api/unlock").get_json() == {"ok": True}
    assert engine.door.unlocks and db.events()[0]["kind"] == "remote"


def test_add_person_without_photos_starts_camera_enrol(client, engine):
    login(client)
    client.post("/people", data={"name": "Siti", "role": "Family"})
    assert engine.enrol_progress()["total"] == engine.settings["photos_per_person"]
    assert db.people()[0]["name"] == "Siti"


def test_upload_without_a_face(client):
    login(client)
    r = client.post("/people", data={"name": "Wong", "photos": (io.BytesIO(b"not an image"), "x.jpg")},
                    content_type="multipart/form-data", follow_redirects=True)
    assert "no face was found" in r.get_data(as_text=True)


def test_delete_person(client):
    login(client)
    pid = db.add_person("Raju", "Guest")
    client.post(f"/people/{pid}/delete")
    assert db.person(pid) is None


def test_settings_save(client, engine):
    login(client)
    client.post("/settings", data={"unlock_seconds": "8", "match_threshold": "65", "cooldown_seconds": "12", "photos_per_person": "15"})
    assert engine.settings["unlock_seconds"] == 8 and engine.settings["match_threshold"] == 65


def test_csv_export(client, engine):
    login(client)
    engine.remote_unlock("Admin")
    text = client.get("/logs.csv").get_data(as_text=True)
    assert text.splitlines()[0] == "time,result,name,distance" and "remote,Admin" in text
