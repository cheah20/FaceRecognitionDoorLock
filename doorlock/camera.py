# pi camera, webcam or test pattern
import time

import cv2
import numpy as np


class Camera:
    def __init__(self, width=640, height=480):
        self.width, self.height = width, height
        self.source = "none"
        self._pi = self._cv = None
        try:
            from picamera2 import Picamera2

            self._pi = Picamera2()
            self._pi.configure(self._pi.create_preview_configuration(main={"size": (width, height), "format": "RGB888"}))
            self._pi.start()
            self.source = "pi camera"
        except Exception:
            cap = cv2.VideoCapture(0)
            if cap.isOpened():
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
                self._cv, self.source = cap, "webcam"

    def read(self):
        # bgr frame
        if self._pi:
            # picamera2 gives RGB, opencv works in BGR
            return cv2.cvtColor(self._pi.capture_array(), cv2.COLOR_RGB2BGR)
        if self._cv:
            ok, frame = self._cv.read()
            if ok:
                return frame
        return self._pattern()

    def _pattern(self):
        frame = np.full((self.height, self.width, 3), (40, 32, 24), np.uint8)
        cv2.putText(frame, "No camera found", (150, 230), cv2.FONT_HERSHEY_SIMPLEX, 1, (200, 200, 200), 2)
        cv2.putText(frame, time.strftime("%H:%M:%S"), (250, 280), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (120, 160, 200), 2)
        return frame

    def close(self):
        if self._pi:
            self._pi.stop()
        if self._cv:
            self._cv.release()
