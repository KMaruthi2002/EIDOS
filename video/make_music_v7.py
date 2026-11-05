# Score and sound design for the v7 cut, 120 BPM. Cinematic hybrid: pulsing pads, sub bass, a hard
# drop on the logo, half-time tension at the alert, a lift at the robot. Sound design: whooshes on
# every cut, impacts on stamps, risers into drops, ticks on steps, a glitch burst at the alert.
import json, numpy as np, wave, subprocess
SR = 44100
V = "/home/claude/eidos-video"
sc = json.load(open(f"{V}/music_v7_scenes.json")); st = sc["starts"]; T = sc["total"] + 1.0; drop = sc["drop"]
cues = json.load(open(f"{V}/src/v7_sfx.json"))
n = int(T * SR); t = np.arange(n) / SR
beat = 0.5; bar = 2.0
note = lambda m: 440 * 2 ** ((m - 69) / 12)
rng = np.random.default_rng(11)
out = np.zeros(n)
def add(sig, at, gain=1.0):
    s0 = int(at * SR)
    if s0 < 0 or s0 >= n: return
    L = min(len(sig), n - s0); out[s0:s0 + L] += gain * sig[:L]
# sections: (start, end, energy 0..1, halftime)
S = [(0, st[1], 0.35, False), (st[1], st[4], 1.0, False), (st[4], st[5], 0.55, True), (st[5], st[6], 1.0, False), (st[6], st[7], 0.75, False), (st[7], T, 0.5, False)]
def energy(x):
    for a, b, e, h in S:
        if a <= x < b: return e, h
    return 0.3, False
chords = [[57, 60, 64, 67], [53, 57, 60, 64], [60, 64, 67, 71], [55, 59, 62, 67]]; bass = [33, 29, 36, 31]
# pads with sidechain pump
for b in range(int(T / bar) + 1):
    s0 = int(b * bar * SR); s1 = min(n, int((b + 1) * bar * SR) + int(0.3 * SR))
    if s0 >= n: break
    e, half = energy(b * bar); tt = np.arange(s1 - s0) / SR; ch = chords[b % 4]; sig = np.zeros(s1 - s0)
    for m in ch:
        for d in (-0.12, 0, 0.12): sig += 2 * ((tt * note(m + d)) % 1) - 1
    sig /= 12; k = 24 if e > 0.6 else 60; sig = np.convolve(sig, np.ones(k) / k, mode="same")
    pump = 1 - (0.6 if e > 0.6 else 0.25) * np.exp(-((tt % (beat * (2 if half else 1))) / 0.13))
    env = np.minimum(1, tt / 0.3) * np.minimum(1, (tt[-1] - tt + 1e-3) / 0.3)
    out[s0:s1] += (0.07 + 0.13 * e) * sig * env * pump
    sub = np.sin(2 * np.pi * note(bass[b % 4]) * tt) * np.minimum(1, tt / 0.02)
    out[s0:s1] += (0.05 + 0.22 * e) * sub * pump
# drums
for i in range(int(T / beat)):
    tb = i * beat; e, half = energy(tb)
    if tb < 3.0 or tb > T - 6: continue
    if half and i % 2: pass
    s0 = int(tb * SR); L = int(0.32 * SR)
    if s0 + L >= n: break
    k = np.arange(L) / SR
    if e > 0.6 or (half and i % 2 == 0) or (e <= 0.6 and i % 2 == 0):
        out[s0:s0 + L] += (0.18 + 0.22 * e) * np.sin(2 * np.pi * (46 + 120 * np.exp(-k * 38)) * k) * np.exp(-k * 11)
    if e > 0.6:
        for q in (0.5,) if not half else ():
            h0 = int((tb + beat * q) * SR); HL = int(0.05 * SR)
            if h0 + HL < n: out[h0:h0 + HL] += 0.04 * rng.standard_normal(HL) * np.exp(-np.arange(HL) / SR * 80)
        if i % 2 == 1:
            CL = int(0.14 * SR); out[s0:s0 + CL] += 0.14 * rng.standard_normal(CL) * np.exp(-np.arange(CL) / SR * 28)
    elif half and i % 4 == 2:
        CL = int(0.25 * SR); out[s0:s0 + CL] += 0.12 * rng.standard_normal(CL) * np.exp(-np.arange(CL) / SR * 14)
# plucks in high-energy sections
for i in range(int(T / (beat / 4))):
    tb = i * beat / 4; e, half = energy(tb)
    if e < 0.9 or tb > T - 8: continue
    b = int(tb / bar); ch = chords[b % 4]; m = ch[(i * 5) % 4] + 12 + (12 if i % 8 in (3, 6) else 0)
    L = int(0.22 * SR); k = np.arange(L) / SR
    add(0.04 * np.sin(2 * np.pi * note(m) * k) * np.exp(-k * 16), tb)
# ---- sound design
def whoosh(dur=0.55, up=True):
    L = int(dur * SR); k = np.arange(L) / SR; x = rng.standard_normal(L)
    # band-sweep by mixing two moving averages
    f = (k / dur) if up else (1 - k / dur)
    w = 6 + int(40 * (1 - f[len(f) // 2]))
    x = np.convolve(x, np.ones(w) / w, mode="same") - np.convolve(x, np.ones(w * 4) / (w * 4), mode="same")
    env = np.sin(np.pi * k / dur) ** 2
    return x / (np.max(np.abs(x)) + 1e-9) * env
def impact(big=1.0):
    L = int(1.2 * SR); k = np.arange(L) / SR
    sub = np.sin(2 * np.pi * (42 + 30 * np.exp(-k * 20)) * k) * np.exp(-k * 3.2)
    nz = rng.standard_normal(L) * np.exp(-k * 22)
    return big * (0.9 * sub + 0.25 * nz)
def riser(dur=2.0):
    L = int(dur * SR); k = np.arange(L) / SR; x = rng.standard_normal(L)
    x = np.convolve(x, np.ones(8) / 8, mode="same")
    tone = np.sin(2 * np.pi * (120 + 900 * (k / dur) ** 2) * k)
    return (0.6 * x + 0.4 * tone) * (k / dur) ** 2.2
def tick():
    L = int(0.06 * SR); k = np.arange(L) / SR
    return np.sin(2 * np.pi * 2600 * k) * np.exp(-k * 90) * 0.8
def ding():
    L = int(0.9 * SR); k = np.arange(L) / SR
    return (np.sin(2 * np.pi * 1318 * k) + 0.5 * np.sin(2 * np.pi * 2637 * k)) * np.exp(-k * 5) * 0.5
def glitch():
    L = int(0.45 * SR); x = rng.standard_normal(L)
    gate = (np.sin(np.arange(L) / SR * 2 * np.pi * 23) > 0.2).astype(float)
    return x * gate * np.exp(-np.arange(L) / SR * 4) * 0.8
def flash():
    L = int(0.35 * SR); k = np.arange(L) / SR
    return rng.standard_normal(L) * np.exp(-k * 30) * 0.6
for c in cues:
    kind, at = c["kind"], c["t"]; g = c.get("gain", 1.0)
    if kind == "whoosh": add(whoosh(c.get("dur", 0.55)), at - 0.3, 0.5 * g)
    elif kind == "impact": add(impact(), at, 0.9 * g)
    elif kind == "riser": add(riser(c.get("dur", 2.0)), at - c.get("dur", 2.0), 0.45 * g)
    elif kind == "tick": add(tick(), at, 0.35 * g)
    elif kind == "ding": add(ding(), at, 0.5 * g)
    elif kind == "glitch": add(glitch(), at, 0.6 * g)
    elif kind == "flash": add(flash(), at, 0.5 * g)
fade = np.minimum(1, t / 1.0) * np.minimum(1, (T - t) / 3.0)
out *= fade; out /= np.max(np.abs(out)) + 1e-9; out *= 0.8
stereo = np.stack([out, np.roll(out, 240)], axis=1)
with wave.open(f"{V}/public/music/bed_v7.wav", "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((stereo * 32767).astype(np.int16).tobytes())
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", f"{V}/public/music/bed_v7.wav", "-b:a", "192k", f"{V}/public/music/bed_v7.mp3"], check=True)
print("music ok", round(T, 1), len(cues), "cues")
