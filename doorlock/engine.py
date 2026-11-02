# main loop
import threading
import time

import cv2

from . import config, db
from .faces import FaceModel, save_face


class Engine:
    def __init__(self, camera, door, model=None):
        self.camera, self.door = camera, door
        self.model = model or FaceModel()
        self.settings = config.load_settings()
        self.jpeg = b""
        self.last = {"text": "Waiting for a face", "kind": "idle", "time": ""}
        self._seen = {}  # person id or "unknown" -> last time we acted
        self._enrol = None  # person id and photos still to take
        self._stop = threading.Event()
        self._lock = threading.Lock()

    # decisions
    def decide(self, person_id, distance, now=None):
        # none while in cooldown
        now = now or time.time()
        known = person_id is not None and distance is not None and distance <= self.settings["match_threshold"]
        key = person_id if known else "unknown"
        if now - self._seen.get(key, 0) < self.settings["cooldown_seconds"]:
            return None
        self._seen[key] = now
        return "granted" if known else "denied"

    def act(self, kind, person_id, distance, frame):
        if kind == "granted":
            person = db.person(person_id)
            name = person["name"] if person else f"Person {person_id}"
            self.door.unlock(self.settings["unlock_seconds"])
            db.log_event("granted", name, person_id, round(distance, 1))
            self.last = {"text": f"Welcome, {name}", "kind": "granted", "time": db.now()}
        else:
            snap = f"{time.strftime('%Y%m%d_%H%M%S')}.jpg"
            cv2.imwrite(str(config.SNAPSHOTS / snap), frame)
            self.door.alarm()
            db.log_event("denied", "Unknown", None, round(distance, 1) if distance is not None else None, snap)
            self.last = {"text": "Unknown face, access denied", "kind": "denied", "time": db.now()}

    def remote_unlock(self, by):
        self.door.unlock(self.settings["unlock_seconds"])
        db.log_event("remote", by)
        self.last = {"text": f"Opened from the dashboard by {by}", "kind": "remote", "time": db.now()}

    # enrolment
    def start_enrol(self, person_id):
        with self._lock:
            self._enrol = [person_id, self.settings["photos_per_person"], 0]

    def enrol_progress(self):
        if not self._enrol:
            return None
        pid, left, taken = self._enrol
        return {"person_id": pid, "taken": taken, "total": taken + left}

    def _take_enrol_photo(self, gray, box):
        pid, left, taken = self._enrol
        save_face(pid, self.model.crop(gray, box), taken)
        self._enrol = [pid, left - 1, taken + 1] if left > 1 else None
        if self._enrol is None:
            self.model.train()

    # loop
    def step(self):
        frame = self.camera.read()
        boxes, gray = self.model.find(frame)
        label = ""
        if boxes:
            box = boxes[0]
            x, y, w, h = box
            with self._lock:
                enrolling = self._enrol is not None
                if enrolling:
                    self._take_enrol_photo(gray, box)
            if enrolling:
                color, label = (255, 180, 60), "Saving photo"
            else:
                pid, dist = self.model.predict(self.model.crop(gray, box))
                kind = self.decide(pid, dist)
                if kind:
                    self.act(kind, pid, dist, frame)
                known = pid is not None and dist is not None and dist <= self.settings["match_threshold"]
                color = (80, 200, 120) if known else (60, 60, 230)
                label = (db.person(pid) or {}).get("name", "Unknown") if known else "Unknown"
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            cv2.putText(frame, label, (x, y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
        if ok:
            self.jpeg = buf.tobytes()

    def run(self):
        while not self._stop.is_set():
            try:
                self.step()
            except Exception as exc:  # keep the door running if one frame fails
                self.last = {"text": f"Camera error: {exc}", "kind": "idle", "time": db.now()}
            time.sleep(0.05)

    def start(self):
        threading.Thread(target=self.run, daemon=True).start()

    def stop(self):
        self._stop.set()
