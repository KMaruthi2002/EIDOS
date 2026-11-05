# Score and sound design, version 8. Band-limited oscillators (no aliasing), real filters, a
# convolution reverb, layered hits. 120 BPM cinematic hybrid: a low pulse and airy pads under the
# narration, a drop on the logo, half-time tension at the alert, a lift at the robot, a quiet close.
import json, os, pathlib, subprocess, numpy as np, wave
from scipy.signal import butter, lfilter, fftconvolve
SR = 44100
V = os.environ.get("VIDEO_DIR", "/home/claude/eidos-video")
sc = json.load(open(f"{V}/music_v8_scenes.json")); st = sc["starts"]; T = sc["total"] + 1.5; drop = sc["drop"]
cues = json.load(open(f"{V}/src/v8_sfx.json"))
n = int(T * SR); t = np.arange(n) / SR
beat = 0.5; bar = 2.0
note = lambda m: 440 * 2 ** ((m - 69) / 12)
rng = np.random.default_rng(8)
out = np.zeros(n)

def lp(x, fc, order=2):
    b, a = butter(order, min(fc, SR / 2 - 100) / (SR / 2)); return lfilter(b, a, x)
def hp(x, fc, order=2):
    b, a = butter(order, max(fc, 10) / (SR / 2), btype="high"); return lfilter(b, a, x)
def bl_saw(f, tt, fmax=5000):
    y = np.zeros_like(tt); k = 1
    while k * f < fmax and k < 60:
        y += np.sin(2 * np.pi * k * f * tt) / k; k += 1
    return y * (2 / np.pi)
# reverb impulse: decaying noise, darker over time
IRL = int(2.2 * SR); irk = np.arange(IRL) / SR
IR = rng.standard_normal(IRL) * np.exp(-irk * 2.6); IR = lp(IR, 5000); IR[:200] *= np.linspace(0, 1, 200); IR /= np.abs(IR).sum() / 40
def verb(x, mix=0.3):
    w = fftconvolve(x, IR)[: len(x)]; return (1 - mix) * x + mix * w
def add(sig, at, gain=1.0):
    s0 = int(at * SR)
    if s0 < 0 or s0 >= n: return
    L = min(len(sig), n - s0); out[s0:s0 + L] += gain * sig[:L]

S = [(0, st[1], 0.3, False), (st[1], st[4], 1.0, False), (st[4], st[5], 0.5, True), (st[5], st[6], 0.95, False), (st[6], st[7], 0.7, False), (st[7], T, 0.45, False)]
def energy(x):
    for a, b, e, h in S:
        if a <= x < b: return e, h
    return 0.3, False
chords = [[57, 60, 64, 67], [53, 57, 60, 64], [60, 64, 67, 71], [55, 59, 62, 67]]; bass = [33, 29, 36, 31]

# pads: band-limited detuned saws through a slowly opening filter, with a sidechain pump
pads = np.zeros(n)
for b in range(int(T / bar) + 1):
    s0 = int(b * bar * SR); s1 = min(n, int((b + 1) * bar * SR) + int(0.5 * SR))
    if s0 >= n: break
    e, half = energy(b * bar); tt = np.arange(s1 - s0) / SR; ch = chords[b % 4]; sig = np.zeros(s1 - s0)
    for m in ch:
        for d in (-0.07, 0.07): sig += bl_saw(note(m + d), tt)
    sig /= 8
    env = np.minimum(1, tt / 0.6) * np.minimum(1, (tt[-1] - tt + 1e-3) / 0.5)
    pump = 1 - (0.5 if e > 0.6 else 0.15) * np.exp(-((tt % (beat * (2 if half else 1))) / 0.14))
    pads[s0:s1] += (0.05 + 0.1 * e) * sig * env * pump
# filter sweep: darker in quiet sections, open in the groove
cut = np.interp(t, [0, drop - 0.1, drop, st[4], st[5], st[7], T], [500, 900, 2600, 2600, 1000, 2200, 700])
seg = int(0.25 * SR); filt = np.zeros(n)
for i in range(0, n, seg):
    j = min(n, i + seg); filt[i:j] = lp(pads[max(0, i - 2000):j], float(cut[i]))[-(j - i):]
out += verb(filt, 0.35)
# sub bass
for b in range(int(T / bar) + 1):
    s0 = int(b * bar * SR); s1 = min(n, int((b + 1) * bar * SR))
    if s0 >= n: break
    e, half = energy(b * bar); tt = np.arange(s1 - s0) / SR
    sub = np.sin(2 * np.pi * note(bass[b % 4]) * tt) * np.minimum(1, tt / 0.03) * np.minimum(1, (tt[-1] - tt + 1e-3) / 0.05)
    pump = 1 - 0.6 * np.exp(-((tt % (beat * (2 if half else 1))) / 0.12))
    out[s0:s1] += (0.04 + 0.2 * e) * sub * pump
# drums
def kick():
    L = int(0.4 * SR); k = np.arange(L) / SR
    body = np.sin(2 * np.pi * (44 + 140 * np.exp(-k * 32)) * k) * np.exp(-k * 9)
    click = hp(rng.standard_normal(int(0.01 * SR)), 2000) * np.exp(-np.arange(int(0.01 * SR)) / SR * 600)
    body[: len(click)] += 0.25 * click; return body
def snare():
    L = int(0.3 * SR); k = np.arange(L) / SR
    nz = hp(rng.standard_normal(L), 900) * np.exp(-k * 18); tone = np.sin(2 * np.pi * 190 * k) * np.exp(-k * 30)
    return verb(0.8 * lp(nz, 7000) + 0.5 * tone, 0.4)
def hat(open_=False):
    L = int((0.22 if open_ else 0.05) * SR); k = np.arange(L) / SR
    return hp(rng.standard_normal(L), 7000) * np.exp(-k * (12 if open_ else 70))
K, SN, HT, HO = kick(), snare(), hat(), hat(True)
for i in range(int(T / beat)):
    tb = i * beat; e, half = energy(tb)
    if tb < 2.0 or tb > T - 7: continue
    if e > 0.6:
        add(K, tb, 0.5)
        if i % 2 == 1: add(SN, tb, 0.42)
        add(HT, tb + beat / 2, 0.06)
        if i % 8 == 7: add(HO, tb + beat / 2, 0.05)
    elif half:
        if i % 2 == 0: add(K, tb, 0.42)
        if i % 4 == 2: add(SN, tb, 0.3)
    else:
        if i % 2 == 0: add(K, tb, 0.22 * e / 0.3 * 0.5)
# felt piano, sparse, over the quiet sections and the groove
def piano(m, dur=1.6):
    L = int(dur * SR); k = np.arange(L) / SR; f = note(m)
    y = sum(np.sin(2 * np.pi * f * h * k) * (0.6 ** h) for h in range(1, 6)) * np.exp(-k * (2.2 + m / 40))
    return verb(lp(y, 3200), 0.5) * 0.18
pattern = [(0, 0), (1.5, 2), (2.0, 1), (3.0, 3)]   # (beat offset in bar, chord tone)
for b in range(int(T / bar)):
    e, half = energy(b * bar)
    if half or (b * bar < 3) or b * bar > T - 6: continue
    ch = chords[b % 4]
    for off, tone in pattern:
        if e < 0.6 and off not in (0, 2.0): continue
        add(piano(ch[tone] + 12), b * bar + off * beat, 0.9 if e > 0.6 else 0.6)
# ---- sound design
def whoosh(dur=0.6):
    L = int(dur * SR); k = np.arange(L) / SR; x = rng.standard_normal(L)
    y = np.zeros(L); seg_ = int(0.03 * SR)
    for i in range(0, L, seg_):
        fc = 300 + 5000 * (i / L) ** 2; y[i:i + seg_] = lp(hp(x[max(0, i - 500):i + seg_], fc * 0.5), fc * 1.6)[-(min(seg_, L - i)):]
    return verb(y * np.sin(np.pi * k / dur) ** 1.5, 0.4) / (np.max(np.abs(y)) + 1e-9)
def impact(big=1.0):
    L = int(1.6 * SR); k = np.arange(L) / SR
    sub = np.sin(2 * np.pi * (40 + 25 * np.exp(-k * 18)) * k) * np.exp(-k * 3)
    body = lp(rng.standard_normal(L), 400) * np.exp(-k * 10)
    crack = hp(rng.standard_normal(L), 1500) * np.exp(-k * 40)
    return verb(big * (1.0 * sub + 0.7 * body + 0.3 * crack), 0.45)
def riser(dur=2.0):
    L = int(dur * SR); k = np.arange(L) / SR
    x = lp(hp(rng.standard_normal(L), 200), 6000)
    tone = np.sin(2 * np.pi * (90 + 700 * (k / dur) ** 2) * k)
    return verb((0.7 * x + 0.3 * tone) * (k / dur) ** 2.5, 0.4)
def tick():
    L = int(0.05 * SR); k = np.arange(L) / SR
    return lp(hp(rng.standard_normal(L), 2500), 9000) * np.exp(-k * 120) * 0.7
def ding():
    L = int(1.2 * SR); k = np.arange(L) / SR
    return verb((np.sin(2 * np.pi * 1046 * k) + 0.4 * np.sin(2 * np.pi * 2093 * k)) * np.exp(-k * 4) * 0.4, 0.5)
def glitch():
    L = int(0.4 * SR); x = hp(rng.standard_normal(L), 1200)
    gate = (np.sin(np.arange(L) / SR * 2 * np.pi * 27) > 0.3).astype(float)
    return x * gate * np.exp(-np.arange(L) / SR * 5) * 0.7
def flash():
    L = int(0.3 * SR); k = np.arange(L) / SR
    return verb(hp(rng.standard_normal(L), 3000) * np.exp(-k * 35) * 0.6, 0.3)
W_, I_, R_, T_, D_, G_, F_ = whoosh(), impact(), riser(), tick(), ding(), glitch(), flash()
for c in cues:
    kind, at = c["kind"], c["t"]; g = c.get("gain", 1.0)
    if kind == "whoosh": add(whoosh(c.get("dur", 0.6)), at - 0.35, 0.35 * g)
    elif kind == "impact": add(I_, at, 0.7 * g)
    elif kind == "riser": add(riser(c.get("dur", 2.0)), at - c.get("dur", 2.0), 0.35 * g)
    elif kind == "tick": add(T_, at, 0.3 * g)
    elif kind == "ding": add(D_, at, 0.45 * g)
    elif kind == "glitch": add(G_, at, 0.5 * g)
    elif kind == "flash": add(F_, at, 0.35 * g)
# master: fades, gentle saturation, band limits
fade = np.minimum(1, t / 1.2) * np.minimum(1, (T - t) / 3.5)
out *= fade; out = hp(out, 28, 2); out = lp(out, 11000, 4)
out = np.tanh(out * 1.6) / 1.6
out /= np.max(np.abs(out)) + 1e-9; out *= 0.85
stereo = np.stack([out, np.roll(out, 220)], axis=1)
with wave.open(f"{V}/public/music/bed_v8.wav", "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((stereo * 32767).astype(np.int16).tobytes())
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", f"{V}/public/music/bed_v8.wav", "-b:a", "192k", f"{V}/public/music/bed_v8.mp3"], check=True)
print("music ok", round(T, 1), len(cues), "cues")
