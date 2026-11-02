// poll door status
const $ = (id) => document.getElementById(id);

async function refresh() {
  let s;
  try {
    s = await (await fetch("/api/status")).json();
  } catch (e) {
    $("camSource").textContent = "offline";
    return;
  }
  $("camSource").textContent = s.camera;
  $("mode").textContent = s.simulated ? "simulated GPIO" : "GPIO live";
  $("sbCam").textContent = "Camera: " + s.camera;
  $("sbMode").textContent = s.simulated ? "GPIO: simulated" : "GPIO: live";

  $("lock").classList.toggle("open", s.open);
  $("lockText").textContent = s.open ? "Unlocked" : "Locked";
  $("lockSub").textContent = s.open ? `Relay on, locks again in ${s.seconds_left}s` : "Relay off";
  document.querySelectorAll(".led").forEach((led) => led.classList.toggle("on", !!s.pins[led.dataset.pin]));

  const msg = $("lastMsg");
  msg.textContent = s.last.time ? `${s.last.text} · ${s.last.time.slice(11)}` : s.last.text;
  msg.className = "feed-msg " + s.last.kind;

  $("cGranted").textContent = s.today.granted;
  $("cDenied").textContent = s.today.denied;
  $("cRemote").textContent = s.today.remote;

  $("enrol").hidden = !s.enrol;
  if (s.enrol) {
    $("enrolText").textContent = `Taking photos ${s.enrol.taken} of ${s.enrol.total}, keep looking at the camera`;
    $("enrolBar").style.width = (s.enrol.taken / s.enrol.total) * 100 + "%";
  }
}

$("unlockBtn").addEventListener("click", async () => {
  const btn = $("unlockBtn");
  btn.disabled = true;
  await fetch("/api/unlock", { method: "POST" });
  setTimeout(() => (btn.disabled = false), 1500);
  refresh();
});

refresh();
setInterval(refresh, 1000);
