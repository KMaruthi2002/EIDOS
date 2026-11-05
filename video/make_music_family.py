# Energetic cinematic bed for the family cut: A minor, 118 BPM, pumping pads, sub bass,
# kick/hat/clap, pluck arps, risers and impacts on scene changes, a big drop at the name reveal.
import json, sys, numpy as np, wave, subprocess
SR = 44100
import os, pathlib
V = os.environ.get("VIDEO_DIR", str(pathlib.Path(__file__).resolve().parent))
starts = json.load(open(f"{V}/music_family_scenes.json"))
T = starts["total"] + 1.0; st = starts["starts"]; drop = starts["drop"]
n = int(T * SR); t = np.arange(n) / SR
BPM = 118; beat = 60 / BPM; bar = 4 * beat
note = lambda m: 440 * 2 ** ((m - 69) / 12)
chords = [[57, 60, 64, 67], [53, 57, 60, 64], [60, 64, 67, 71], [55, 59, 62, 67]]   # Am F C G
bass = [33, 29, 36, 31]
out = np.zeros(n)
nb = int(T / bar) + 1
for b in range(nb):
    s0 = int(b * bar * SR); s1 = min(n, int((b + 1) * bar * SR) + int(0.25 * SR))
    if s0 >= n: break
    tt = np.arange(s1 - s0) / SR; ch = chords[b % 4]; sig = np.zeros(s1 - s0)
    for m in ch:
        for d in (-0.1, 0.0, 0.1):
            sig += 2 * ((tt * note(m + d)) % 1) - 1
    sig /= 12; sig = np.convolve(sig, np.ones(30) / 30, mode="same")
    # sidechain pump on each beat
    pump = 1 - 0.55 * np.exp(-((tt % beat) / 0.12))
    e = np.minimum(1, tt / 0.4) * np.minimum(1, (tt[-1] - tt + 1e-3) / 0.3)
    amp = 0.10 if b * bar < drop else 0.18
    out[s0:s1] += amp * sig * e * pump
    fb = note(bass[b % 4]); sub = np.sin(2 * np.pi * fb * tt) * np.minimum(1, tt / 0.02)
    out[s0:s1] += (0.08 if b * bar < drop else 0.26) * sub * pump
for i in range(int(T / beat)):
    tb = i * beat
    if tb < drop - 0.01 or tb > T - 7: continue
    s0 = int(tb * SR); L = int(0.3 * SR)
    if s0 + L >= n: break
    k = np.arange(L) / SR
    out[s0:s0 + L] += 0.38 * np.sin(2 * np.pi * (48 + 110 * np.exp(-k * 35)) * k) * np.exp(-k * 10)
    for q in (0.25, 0.5, 0.75):
        h0 = int((tb + beat * q) * SR); HL = int(0.04 * SR)
        if h0 + HL < n: out[h0:h0 + HL] += (0.05 if q == 0.5 else 0.028) * np.random.default_rng(i * 7 + int(q * 4)).standard_normal(HL) * np.exp(-np.arange(HL) / SR * 90)
    if i % 2 == 1:   # clap on 2 and 4
        c0 = s0; CL = int(0.12 * SR)
        if c0 + CL < n: out[c0:c0 + CL] += 0.12 * np.random.default_rng(i).standard_normal(CL) * np.exp(-np.arange(CL) / SR * 30)
for i in range(int(T / (beat / 4))):
    tb = i * beat / 4
    if tb < drop or tb > T - 8: continue
    b = int(tb / bar); ch = chords[b % 4]; m = ch[(i * 5) % 4] + 12 + (12 if i % 8 == 3 else 0)
    s0 = int(tb * SR); L = int(0.25 * SR)
    if s0 + L >= n: break
    k = np.arange(L) / SR
    out[s0:s0 + L] += 0.045 * np.sin(2 * np.pi * note(m) * k) * np.exp(-k * 14)
for s in st[1:]:
    R = int(1.2 * SR); s1 = int(s * SR); s0 = s1 - R
    if s0 > 0:
        k = np.arange(R) / SR
        noise = np.convolve(np.random.default_rng(int(s * 10)).standard_normal(R), np.ones(5) / 5, mode="same")
        out[s0:s1] += 0.09 * noise * (k / 1.2) ** 2.5
    L = int(1.0 * SR)
    if s1 + L < n:
        k = np.arange(L) / SR
        big = 1.6 if abs(s - drop) < 0.2 else 1.0
        out[s1:s1 + L] += big * (0.22 * np.sin(2 * np.pi * 45 * k) * np.exp(-k * 4) + 0.05 * np.random.default_rng(int(s)).standard_normal(L) * np.exp(-k * 15))
fade = np.minimum(1, t / 1.5) * np.minimum(1, (T - t) / 3.5)
out *= fade; out /= np.max(np.abs(out)) + 1e-9; out *= 0.7
stereo = np.stack([out, np.roll(out, 260)], axis=1)
with wave.open(f"{V}/public/music/bed_family.wav", "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((stereo * 32767).astype(np.int16).tobytes())
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", f"{V}/public/music/bed_family.wav", "-b:a", "192k", f"{V}/public/music/bed_family.mp3"], check=True)
print("music ok", round(T, 1))
