# door lock dashboard
import csv
import io
import os
import time
from functools import wraps

import cv2
import numpy as np
from flask import (Flask, Response, abort, flash, jsonify, redirect, render_template, request, send_from_directory,
                   session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

from doorlock import config, db
from doorlock.camera import Camera
from doorlock.engine import Engine
from doorlock.faces import photo_count, save_face
from doorlock.hardware import Door


def create_app(engine=None, start=True):
    app = Flask(__name__)
    app.secret_key = os.environ.get("DOORLOCK_SECRET", os.urandom(16).hex())
    password_hash = generate_password_hash(os.environ.get("DOORLOCK_PASSWORD", "admin"))
    db.init()
    if engine is None:
        engine = Engine(Camera(), Door())
    if start:
        engine.start()
    app.engine = engine

    @app.context_processor
    def status_bar():
        return {"cam": engine.camera.source, "gpio": "simulated" if engine.door.simulated else "live"}

    def login_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not session.get("admin"):
                return redirect(url_for("login", next=request.path))
            return view(*args, **kwargs)
        return wrapped

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            if check_password_hash(password_hash, request.form.get("password", "")):
                session["admin"] = True
                return redirect(request.args.get("next") or url_for("dashboard"))
            flash("Wrong password, try again.")
        return render_template("login.html")

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.route("/")
    @login_required
    def dashboard():
        return render_template("dashboard.html", page="dashboard", events=db.events(limit=8))

    @app.route("/video_feed")
    @login_required
    def video_feed():
        def frames():
            while True:
                if engine.jpeg:
                    yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + engine.jpeg + b"\r\n"
                time.sleep(0.1)
        return Response(frames(), mimetype="multipart/x-mixed-replace; boundary=frame")

    @app.route("/api/status")
    @login_required
    def status():
        door = engine.door
        return jsonify(open=door.is_open, seconds_left=max(0, round(door.unlocked_until - time.time(), 1)),
                       pins=door.pins(), simulated=door.simulated, camera=engine.camera.source,
                       last=engine.last, today=db.today_counts(), enrol=engine.enrol_progress(),
                       people=len(db.people()), trained=engine.model.trained)

    @app.route("/api/unlock", methods=["POST"])
    @login_required
    def unlock():
        engine.remote_unlock("Admin")
        return jsonify(ok=True)

    @app.route("/people", methods=["GET", "POST"])
    @login_required
    def people():
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            if not name:
                flash("Please type a name.")
                return redirect(url_for("people"))
            pid = db.add_person(name, request.form.get("role", "Resident"))
            uploads = [f for f in request.files.getlist("photos") if f.filename]
            if uploads:
                saved = save_uploads(pid, uploads)
                engine.model.train()
                flash(f"{name} added with {saved} photos." if saved else f"{name} added, but no face was found in the photos.")
            else:
                engine.start_enrol(pid)
                flash(f"{name} added. Look at the camera while it takes {engine.settings['photos_per_person']} photos.")
                return redirect(url_for("dashboard"))
            return redirect(url_for("people"))
        rows = [dict(p, photos=photo_count(p["id"])) for p in db.people()]
        return render_template("people.html", page="people", people=rows)

    def save_uploads(pid, uploads):
        saved = 0
        for f in uploads:
            img = cv2.imdecode(np.frombuffer(f.read(), np.uint8), cv2.IMREAD_COLOR)
            if img is None:
                continue
            boxes, gray = engine.model.find(img)
            if boxes:
                save_face(pid, engine.model.crop(gray, boxes[0]), photo_count(pid))
                saved += 1
        return saved

    @app.route("/people/<int:pid>/retake", methods=["POST"])
    @login_required
    def retake(pid):
        if not db.person(pid):
            abort(404)
        engine.start_enrol(pid)
        flash("Look at the camera while it takes new photos.")
        return redirect(url_for("dashboard"))

    @app.route("/people/<int:pid>/delete", methods=["POST"])
    @login_required
    def delete_person(pid):
        person = db.person(pid) or abort(404)
        folder = config.FACES / str(pid)
        for img in folder.glob("*.jpg") if folder.exists() else []:
            img.unlink()
        db.delete_person(pid)
        engine.model.train()
        flash(f"{person['name']} removed.")
        return redirect(url_for("people"))

    @app.route("/logs")
    @login_required
    def logs():
        kind = request.args.get("kind") or None
        return render_template("logs.html", page="logs", events=db.events(kind), kind=kind)

    @app.route("/logs.csv")
    @login_required
    def logs_csv():
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(["time", "result", "name", "distance"])
        for e in db.events(limit=10000):
            writer.writerow([e["time"], e["kind"], e["name"], e["distance"] if e["distance"] is not None else ""])
        return Response(out.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=access_log.csv"})

    @app.route("/snapshots/<path:name>")
    @login_required
    def snapshot(name):
        return send_from_directory(config.SNAPSHOTS, name)

    @app.route("/settings", methods=["GET", "POST"])
    @login_required
    def settings():
        if request.method == "POST":
            engine.settings = config.save_settings(request.form)
            flash("Settings saved.")
            return redirect(url_for("settings"))
        return render_template("settings.html", page="settings", settings=engine.settings, pins=config.PINS)

    return app


if __name__ == "__main__":
    # threaded so the stream won't block other pages
    create_app().run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), threaded=True)
