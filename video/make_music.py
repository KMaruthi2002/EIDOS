# Original background track for the explainer: warm pads, a soft pulse, light arpeggio,
# a riser into each scene change and a soft hit on it. Pure synthesis, no samples.
import json, numpy as np, wave
SR = 44100
sc = json.load(open("music_scenes.json")); T = sc["total"] + 1.0; starts = sc["starts"]
n = int(T * SR); t = np.arange(n) / SR
BPM = 104; beat = 60 / BPM; bar = 4 * beat
def note(m): return 440 * 2 ** ((m - 69) / 12)
# I - V - vi - IV in D major
chords = [[62, 66, 69, 74], [57, 61, 64, 69], [59, 62, 66, 71], [55, 59, 62, 67]]
bass = [38, 33, 35, 31]
out = np.zeros(n)
def env_adsr(length, a=0.02, r=0.3):
    k = np.arange(length) / SR; e = np.minimum(1, k / a); e *= np.exp(-k / r); return e
# pads: detuned saws, filtered by simple one-pole smoothing, one chord per bar
nb = int(T / bar) + 1
for b in range(nb):
    s0 = int(b * bar * SR); s1 = min(n, int((b + 1) * bar * SR) + int(0.3 * SR))
    if s0 >= n: break
    tt = np.arange(s1 - s0) / SR
    ch = chords[b % 4]; sig = np.zeros(s1 - s0)
    for m in ch:
        for d in (-0.08, 0.0, 0.08):
            f = note(m + d)
            sig += 2 * ((tt * f) % 1) - 1
    sig /= 12
    # soften: moving average low-pass
    k = 40; sig = np.convolve(sig, np.ones(k) / k, mode="same")
    e = np.minimum(1, tt / 0.6) * np.minimum(1, (tt[-1] - tt + 1e-3) / 0.4)
    out[s0:s1] += 0.16 * sig * e
    # bass
    fb = note(bass[b % 4]); bs = np.sin(2 * np.pi * fb * tt) * np.minimum(1, tt / 0.02) * np.exp(-tt / 1.4)
    out[s0:s1] += 0.22 * bs
# pulse: soft kick on each beat after the intro, light hat on off-beats
for i in range(int(T / beat)):
    tb = i * beat
    if tb < 3.5 or tb > T - 6: continue
    s0 = int(tb * SR); L = int(0.35 * SR)
    if s0 + L >= n: break
    k = np.arange(L) / SR
    kick = np.sin(2 * np.pi * (50 + 90 * np.exp(-k * 30)) * k) * np.exp(-k * 9)
    out[s0:s0 + L] += 0.30 * kick
    h0 = int((tb + beat / 2) * SR); HL = int(0.05 * SR)
    if h0 + HL < n:
        out[h0:h0 + HL] += 0.035 * np.random.default_rng(i).standard_normal(HL) * np.exp(-np.arange(HL) / SR * 70)
# arpeggio plucks (16ths) in the middle sections
rng = np.random.default_rng(7)
for i in range(int(T / (beat / 2))):
    tb = i * beat / 2
    if tb < 22 or tb > T - 10: continue
    b = int(tb / bar); ch = chords[b % 4]; m = ch[(i * 3) % 4] + 12
    s0 = int(tb * SR); L = int(0.4 * SR)
    if s0 + L >= n: break
    k = np.arange(L) / SR
    out[s0:s0 + L] += 0.05 * np.sin(2 * np.pi * note(m) * k) * np.exp(-k * 8)
# risers and hits at scene changes
for st in starts[1:]:
    R = int(1.0 * SR); s1 = int(st * SR); s0 = s1 - R
    if s0 > 0:
        k = np.arange(R) / SR
        noise = np.random.default_rng(int(st * 10)).standard_normal(R)
        noise = np.convolve(noise, np.ones(6) / 6, mode="same")
        out[s0:s1] += 0.06 * noise * (k / 1.0) ** 2
    L = int(0.8 * SR)
    if s1 + L < n:
        k = np.arange(L) / SR
        out[s1:s1 + L] += 0.18 * np.sin(2 * np.pi * 55 * k) * np.exp(-k * 5) + 0.04 * np.random.default_rng(int(st)).standard_normal(L) * np.exp(-k * 18)
# fade in/out and normalize
fade = np.minimum(1, t / 2.0) * np.minimum(1, (T - t) / 3.0)
out *= fade
out /= np.max(np.abs(out)) + 1e-9; out *= 0.7
stereo = np.stack([out, np.roll(out, 300)], axis=1)
with wave.open("public/music/bed.wav", "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((stereo * 32767).astype(np.int16).tobytes())
print("ok", T)
