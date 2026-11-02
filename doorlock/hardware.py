# relay, leds, buzzer
import threading
import time

from .config import PINS


class FakePin:
    def __init__(self):
        self.is_active = False

    def on(self):
        self.is_active = True

    def off(self):
        self.is_active = False

    def close(self):
        pass


class Door:
    def __init__(self):
        try:
            from gpiozero import Buzzer, LED, OutputDevice

            # relay is active low
            self.relay = OutputDevice(PINS["relay"], active_high=False, initial_value=False)
            self.green, self.red, self.buzzer = LED(PINS["green_led"]), LED(PINS["red_led"]), Buzzer(PINS["buzzer"])
            self.simulated = False
        except Exception:
            self.relay, self.green, self.red, self.buzzer = FakePin(), FakePin(), FakePin(), FakePin()
            self.simulated = True
        self._lock = threading.Lock()
        self.unlocked_until = 0.0

    @property
    def is_open(self):
        return time.time() < self.unlocked_until

    def pins(self):
        return {"relay": self.relay.is_active, "green_led": self.green.is_active,
                "red_led": self.red.is_active, "buzzer": self.buzzer.is_active}

    def _beep(self, seconds):
        self.buzzer.on()
        time.sleep(seconds)
        self.buzzer.off()

    def unlock(self, seconds):
        # open for a few seconds
        def run():
            with self._lock:
                self.unlocked_until = time.time() + seconds
                self.relay.on()
                self.green.on()
                self._beep(0.15)
                time.sleep(max(0, seconds - 0.15))
                self.relay.off()
                self.green.off()

        threading.Thread(target=run, daemon=True).start()

    def alarm(self):
        # unknown face
        def run():
            self.red.on()
            self._beep(1.0)
            time.sleep(1.0)
            self.red.off()

        threading.Thread(target=run, daemon=True).start()

    def close(self):
        for part in (self.relay, self.green, self.red, self.buzzer):
            part.off()
            part.close()
