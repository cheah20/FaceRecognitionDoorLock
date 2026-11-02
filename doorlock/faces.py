# haar cascade + lbph
from pathlib import Path

import cv2
import numpy as np

from . import config

SIZE = (200, 200)


class FaceModel:
    def __init__(self):
        self.detector = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        self.trained = False
        if config.MODEL_PATH.exists():
            self.recognizer.read(str(config.MODEL_PATH))
            self.trained = True

    def find(self, frame):
        # boxes, biggest first
        gray = cv2.equalizeHist(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
        boxes = self.detector.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(80, 80))
        return sorted((tuple(int(v) for v in b) for b in boxes), key=lambda b: -b[2] * b[3]), gray

    @staticmethod
    def crop(gray, box):
        x, y, w, h = box
        return cv2.resize(gray[y:y + h, x:x + w], SIZE)

    def predict(self, face):
        # (id, distance), none before training
        if not self.trained:
            return None, None
        label, distance = self.recognizer.predict(face)
        return int(label), float(distance)

    def train(self):
        # train on data/faces/<id>/
        images, labels = [], []
        for folder in sorted(config.FACES.iterdir()) if config.FACES.exists() else []:
            if folder.is_dir() and folder.name.isdigit():
                for img in sorted(folder.glob("*.jpg")):
                    face = cv2.imread(str(img), cv2.IMREAD_GRAYSCALE)
                    if face is not None:
                        images.append(cv2.resize(face, SIZE))
                        labels.append(int(folder.name))
        if not images:
            self.trained = False
            config.MODEL_PATH.unlink(missing_ok=True)
            return 0
        self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        self.recognizer.train(images, np.array(labels))
        self.recognizer.write(str(config.MODEL_PATH))
        self.trained = True
        return len(images)


def save_face(person_id, face, index):
    folder = config.FACES / str(person_id)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{index:03d}.jpg"
    cv2.imwrite(str(path), face)
    return path


def photo_count(person_id):
    folder = Path(config.FACES) / str(person_id)
    return len(list(folder.glob("*.jpg"))) if folder.exists() else 0
