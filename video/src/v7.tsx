// EIDOS, version 7: a beat-locked cinematic cut. Letterboxed, one hot accent, footage inside type,
// hard cuts with white flashes, a glitch hit, a speed-ramped robot shot, synthesized sound design.
import React from "react";
import { AbsoluteFill, Img, interpolate, Sequence, spring, staticFile, useCurrentFrame } from "remotion";
import { Audio, Video } from "@remotion/media";
import { TransitionSeries, linearTiming } from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";
import { FONT, MONO, ease } from "./ui";
import timeline from "./timeline7.json";
import timing from "./v7_timing.json";
import sent from "./v7_sent.json";
import world from "./world_data.json";

const FPS = 30, W = 1920, H = 1080, BAR = 84;
const INK = "#050608", WHITE = "#f6f7fb", DIM = "rgba(246,247,251,.6)";
const CYAN = "#1ee3ff", COBALT = "#2a5bff", CORAL = "#ff3b4e", GREEN = "#2bf0a6";
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const useT = () => useCurrentFrame() / FPS;
const ramp = (t: number, a: number, b: number) => interpolate(t, [a, b], [0, 1], { ...clamp, easing: ease });
const lin = (t: number, a: number, b: number) => interpolate(t, [a, b], [0, 1], clamp);
const sp = (f: number, at: number, cfg: { damping?: number; mass?: number; stiffness?: number } = {}) =>
  spring({ frame: f - at * FPS, fps: FPS, config: { damping: 14, stiffness: 160, ...cfg } });
const SNAP = { damping: 100, stiffness: 200, mass: 0.5 };
const rnd = (i: number, k = 0) => { const x = Math.sin(i * 127.1 + k * 311.7) * 43758.5453; return x - Math.floor(x); };
const LEAD = timing.lead;
const VO = (id: string) => timeline.find((s) => s.id === id)!;
const S = (id: string, k: number) => LEAD + (sent as any)[id][k];          // when sentence k of a scene starts
const shake = (t: number, at: number, amp = 14, dur = 0.5) => (t > at && t < at + dur ? Math.sin((t - at) * 110) * amp * (1 - lin(t, at, at + dur)) : 0);

/* ------------------------------------------------------------------ film layer */

const Film: React.FC = () => {
  const t = useT();
  return (
    <>
      <AbsoluteFill style={{ backgroundImage: `url(${staticFile("noise.png")})`, backgroundSize: 420, backgroundPosition: `${(t * 113) % 420}px ${(t * 71) % 420}px`, opacity: 0.075, mixBlendMode: "overlay", pointerEvents: "none" }} />
      <AbsoluteFill style={{ background: "radial-gradient(80% 70% at 50% 50%, transparent 55%, rgba(0,0,0,.7))", pointerEvents: "none" }} />
      <div style={{ position: "absolute", left: 0, right: 0, top: 0, height: BAR, background: INK }} />
      <div style={{ position: "absolute", left: 0, right: 0, bottom: 0, height: BAR, background: INK }} />
    </>
  );
};

const Flash: React.FC<{ at: number; dur?: number; color?: string }> = ({ at, dur = 0.22, color = "#fff" }) => {
  const t = useT();
  const o = t >= at && t < at + dur ? 1 - lin(t, at, at + dur) : 0;
  return o > 0 ? <AbsoluteFill style={{ background: color, opacity: o * 0.95 }} /> : null;
};

const Flare: React.FC<{ at: number; x?: number; y?: number; dur?: number }> = ({ at, x = W / 2, y = H / 2, dur = 1.2 }) => {
  const t = useT();
  if (t < at || t > at + dur) return null;
  const p = lin(t, at, at + dur), o = Math.sin(Math.PI * p) ** 0.7;
  return (
    <>
      <div style={{ position: "absolute", left: x - 1400, top: y - 3, width: 2800, height: 6, background: `linear-gradient(90deg, transparent, ${CYAN}, #fff, ${CYAN}, transparent)`, opacity: o, transform: `scaleX(${0.3 + 0.9 * p})`, filter: "blur(1px)", mixBlendMode: "screen" }} />
      <div style={{ position: "absolute", left: x - 300, top: y - 300, width: 600, height: 600, borderRadius: "50%", background: `radial-gradient(circle, rgba(255,255,255,.9), ${CYAN}55 30%, transparent 70%)`, opacity: o, mixBlendMode: "screen" }} />
    </>
  );
};

const Bg: React.FC<{ hero?: string; glow?: number }> = ({ hero, glow = 1 }) => {
  const t = useT();
  return (
    <AbsoluteFill style={{ background: INK, overflow: "hidden" }}>
      {hero && <Img src={staticFile(hero)} style={{ position: "absolute", width: "110%", height: "110%", left: "-5%", top: "-5%", objectFit: "cover", transform: `scale(${1 + t * 0.006}) translateX(${-t * 1.5}px)`, opacity: 0.55, filter: "saturate(.8) contrast(1.05)" }} />}
      {hero && <AbsoluteFill style={{ background: "linear-gradient(180deg, rgba(5,6,8,.55), rgba(5,6,8,.25) 45%, rgba(5,6,8,.85))" }} />}
      <div style={{ position: "absolute", width: 1500, height: 900, borderRadius: "50%", background: COBALT, filter: "blur(230px)", opacity: 0.22 * glow, left: `calc(${25 + Math.sin(t * 0.25) * 6}% - 750px)`, top: `calc(${40 + Math.cos(t * 0.2) * 6}% - 450px)` }} />
      <div style={{ position: "absolute", width: 900, height: 900, borderRadius: "50%", background: CYAN, filter: "blur(220px)", opacity: 0.1 * glow, left: `calc(${80 + Math.cos(t * 0.22) * 6}% - 450px)`, top: `calc(${65 + Math.sin(t * 0.27) * 6}% - 450px)` }} />
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ type and chrome */

const Kinetic: React.FC<{ text: string; at: number; step?: number; size?: number; weight?: number; color?: string; hot?: string[]; style?: React.CSSProperties; align?: string; wide?: boolean }> =
  ({ text, at, step = 0.06, size = 96, weight = 850, color = WHITE, hot = [], style, align = "center", wide }) => {
    const t = useT();
    return (
      <div style={{ display: "flex", flexWrap: "wrap", justifyContent: align, columnGap: "0.26em", fontFamily: FONT, fontSize: size, fontWeight: weight, letterSpacing: wide ? "0.02em" : "-0.035em", lineHeight: 1.04, color, fontVariationSettings: wide ? '"wdth" 125' : undefined, ...style }}>
        {text.split(" ").map((w, i) => {
          const p = ramp(t, at + i * step, at + i * step + 0.6);
          const h = hot.includes(w.replace(/[.,?!]/g, ""));
          return <span key={i} style={{ display: "inline-block", transform: `translateY(${(1 - p) * 60}px) scale(${0.9 + 0.1 * p})`, opacity: p, filter: `blur(${(1 - p) * 12}px)`, ...(h ? { color: CYAN, textShadow: `0 0 28px ${CYAN}77` } : {}) }}>{w}</span>;
        })}
      </div>
    );
  };

const Stamp: React.FC<{ at: number; children: React.ReactNode; color?: string; size?: number; rot?: number; style?: React.CSSProperties; ghost?: boolean }> = ({ at, children, color = CORAL, size = 54, rot = -4, style, ghost }) => {
  const f = useCurrentFrame();
  const s = sp(f, at, { damping: 9, stiffness: 260 });
  return (
    <div style={{ display: "inline-block", fontFamily: FONT, fontSize: size, fontWeight: 900, letterSpacing: "-0.02em", color: ghost ? WHITE : "#fff", padding: `${size * 0.28}px ${size * 0.55}px`, borderRadius: size * 0.22,
      background: ghost ? "rgba(246,247,251,.08)" : color, border: ghost ? "1.5px solid rgba(246,247,251,.35)" : "none", backdropFilter: ghost ? "blur(12px)" : undefined,
      boxShadow: ghost ? "none" : `0 0 70px ${color}88, 0 30px 60px -20px rgba(0,0,0,.8)`, transform: `scale(${0.3 + 0.7 * s}) rotate(${rot * (1.8 - 0.8 * s)}deg)`, opacity: Math.min(1, s * 2), whiteSpace: "nowrap", ...style }}>{children}</div>
  );
};

const Ants: React.FC<{ color: string; draw?: number; width?: number; radius?: number; glow?: boolean }> = ({ color, draw = 1, width = 4, radius = 18, glow }) => {
  const t = useT();
  return (
    <svg width="100%" height="100%" style={{ position: "absolute", inset: 0, overflow: "visible", filter: glow ? `drop-shadow(0 0 10px ${color})` : undefined }}>
      <rect x={0} y={0} width="100%" height="100%" rx={radius} fill="none" stroke={color} strokeWidth={width} pathLength={100} strokeDasharray={draw < 1 ? `${100 * draw} 100` : "1.4 0.9"} strokeDashoffset={draw < 1 ? 0 : -t * 3} />
    </svg>
  );
};

const Brackets: React.FC<{ color?: string; size?: number; inset?: number }> = ({ color = CYAN, size = 40, inset = 16 }) => (
  <>{[[0, 0], [1, 0], [0, 1], [1, 1]].map(([x, y], i) => (
    <div key={i} style={{ position: "absolute", width: size, height: size, left: x ? undefined : inset, right: x ? inset : undefined, top: y ? undefined : inset, bottom: y ? inset : undefined,
      borderLeft: x ? undefined : `3px solid ${color}`, borderRight: x ? `3px solid ${color}` : undefined, borderTop: y ? undefined : `3px solid ${color}`, borderBottom: y ? `3px solid ${color}` : undefined, filter: `drop-shadow(0 0 6px ${color})` }} />
  ))}</>
);

const Frame: React.FC<{ w: number; h: number; children: React.ReactNode; style?: React.CSSProperties; radius?: number }> = ({ w, h, children, style, radius = 24 }) => (
  <div style={{ position: "relative", width: w, height: h, borderRadius: radius, overflow: "hidden", background: "#000",
    boxShadow: `0 0 0 1.5px rgba(255,255,255,.16), 0 70px 120px -50px rgba(0,0,0,.95), 0 0 120px -40px ${COBALT}99`, ...style }}>{children}</div>
);

const Clip: React.FC<{ src: string; w: number; h: number; rate?: number; from?: number; grade?: boolean }> = ({ src, w, h, rate = 1, from = 0, grade = true }) => (
  <Video src={staticFile(`clips/${src}.mp4`)} muted playbackRate={rate} trimBefore={Math.round(from * FPS)} style={{ width: w, height: h, display: "block", objectFit: "cover", filter: grade ? "contrast(1.08) saturate(.9)" : undefined }} />
);

const Scan: React.FC<{ period?: number; color?: string }> = ({ period = 2.4, color = CYAN }) => {
  const t = useT(); const y = (t / period) % 1;
  return <div style={{ position: "absolute", left: 0, right: 0, top: `${y * 100}%`, height: 80, transform: "translateY(-80px)", background: `linear-gradient(180deg, transparent, ${color}2e)`, borderBottom: `2px solid ${color}`, boxShadow: `0 0 22px ${color}` }} />;
};

const Caption: React.FC<{ id: string }> = ({ id }) => {
  const t = useT() - LEAD;
  const vo = VO(id);
  const parts = (vo.text.replace(/Pulse Parallax/g, "PULSE - Parallax").match(/[^.!?]+[.!?]+/g) || [vo.text]);
  const total = parts.reduce((a, p) => a + p.length, 0);
  let acc = 0, cur = "";
  for (const p of parts) { const s = (acc / total) * vo.seconds, e = ((acc + p.length) / total) * vo.seconds; if (t >= s - 0.05 && t < e + 0.2) cur = p.trim(); acc += p.length; }
  if (t > vo.seconds + 0.3 || t < 0) cur = "";
  return (
    <div style={{ position: "absolute", left: 0, right: 0, bottom: 0, height: BAR, display: "flex", alignItems: "center", justifyContent: "center", zIndex: 20 }}>
      {cur && <div style={{ fontFamily: FONT, fontSize: 25, fontWeight: 560, color: "rgba(246,247,251,.85)", letterSpacing: "0.005em", maxWidth: 1500, textAlign: "center" }}>{cur}</div>}
    </div>
  );
};

/* footage visible only inside giant letters: white text on black, multiplied over the video */
const MaskWord: React.FC<{ word: string; reveal: number; size?: number }> = ({ word, reveal, size = 215 }) => {
  const t = useT();
  const o = 1 - ramp(t, reveal, reveal + 0.5);
  return (
    <AbsoluteFill style={{ background: "#000", mixBlendMode: "multiply", opacity: o, alignItems: "center", justifyContent: "center" }}>
      <div style={{ fontFamily: FONT, fontSize: size, fontWeight: 900, fontVariationSettings: '"wdth" 125', letterSpacing: "0.02em", color: "#fff", lineHeight: 1, transform: `scale(${1.08 - 0.08 * ramp(t, reveal - 1.2, reveal + 0.5)})` }}>{word}</div>
    </AbsoluteFill>
  );
};

const Logo: React.FC<{ at: number; size?: number; footage?: boolean; flare?: number }> = ({ at, size = 240, footage, flare }) => {
  const t = useT(); const f = useCurrentFrame();
  const solid = footage ? ramp(t, at + 1.7, at + 2.2) : 1;
  const clips = ["tomato_demo", "cabinet_power_on", "gpu_demo"];
  const k = Math.floor(((t - at) / 0.45)) % 3;
  return (
    <div style={{ position: "relative", padding: `${size * 0.1}px ${size * 0.24}px` }}>
      <Ants color={CYAN} draw={ramp(t, at + 0.2, at + 1.2)} width={5} radius={size * 0.1} glow />
      <div style={{ position: "relative", display: "flex", fontFamily: FONT, fontSize: size, fontWeight: 900, letterSpacing: "0.08em", fontVariationSettings: '"wdth" 125', lineHeight: 1, color: "#fff" }}>
        {footage && solid < 1 && (
          <div style={{ position: "absolute", inset: -20, overflow: "hidden", opacity: 1 - solid }}>
            <Video src={staticFile(`clips/${clips[((k % 3) + 3) % 3]}.mp4`)} muted playbackRate={3} trimBefore={Math.round(12 * FPS)} style={{ width: "100%", height: "100%", objectFit: "cover", filter: "contrast(1.1) saturate(1.1)" }} />
            <AbsoluteFill style={{ background: "#000", mixBlendMode: "multiply", display: "flex", alignItems: "center", justifyContent: "center", padding: 20 }}>
              <div style={{ display: "flex", fontFamily: FONT, fontSize: size, fontWeight: 900, letterSpacing: "0.08em", fontVariationSettings: '"wdth" 125', lineHeight: 1, color: "#fff" }}>
                {"EIDOS".split("").map((l, i) => { const s = sp(f, at + i * 0.07, { damping: 8, mass: 0.7 }); return <span key={i} style={{ display: "inline-block", transform: `translateY(${(1 - s) * 160}px) scale(${0.3 + 0.7 * s})`, opacity: Math.min(1, s * 1.6) }}>{l}</span>; })}
              </div>
            </AbsoluteFill>
          </div>
        )}
        {"EIDOS".split("").map((l, i) => {
          const s = sp(f, at + i * 0.07, { damping: 8, mass: 0.7 });
          return <span key={i} style={{ display: "inline-block", position: "relative", transform: `translateY(${(1 - s) * 160}px) scale(${0.3 + 0.7 * s})`, opacity: Math.min(1, s * 1.6) * (footage ? solid : 1), textShadow: `0 0 40px ${COBALT}88` }}>{l}</span>;
        })}
      </div>
      {flare != null && <Flare at={flare} x={size * 2.6} y={size * 0.6} />}
    </div>
  );
};

const Cam: React.FC<{ children: React.ReactNode; push?: number; shakeAt?: number; amp?: number }> = ({ children, push = 0.035, shakeAt, amp = 14 }) => {
  const t = useT();
  const sx = shakeAt != null ? shake(t, shakeAt, amp) : 0;
  return <AbsoluteFill style={{ transform: `scale(${1 + push * lin(t, 0, 12)}) translate(${sx}px, ${sx * 0.6}px)` }}>{children}</AbsoluteFill>;
};

/* ------------------------------------------------------------------ 1. hook */

const CUTS: [string, string, number, number][] = [["COOKING.", "tomato_demo", 0, S("hook", 2)], ["FIXING.", "cabinet_power_on", 22, S("hook", 3)], ["BUILDING.", "gpu_demo", 34, S("hook", 4)]];
const Hook: React.FC = () => {
  const t = useT(); const f = useCurrentFrame();
  const s1 = S("hook", 1), s5 = S("hook", 5);
  const wall = t >= s1 - 0.2 && t < CUTS[0][3];
  const cardsAt = s5, flipAt = s5 + 4.6, dotAt = s5 + 8.2;
  return (
    <AbsoluteFill>
      <Bg hero="hero/workshop.jpg" glow={0.8} />
      {/* opening dot and line */}
      {t < s1 + 0.4 && (
        <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
          <div style={{ width: 14 + 6 * Math.sin(t * 6), height: 14 + 6 * Math.sin(t * 6), borderRadius: "50%", background: CYAN, boxShadow: `0 0 30px ${CYAN}, 0 0 80px ${CYAN}66`, opacity: ramp(t, 0.1, 0.5) * (1 - ramp(t, s1, s1 + 0.4)) }} />
          <div style={{ marginTop: 30, opacity: 1 - ramp(t, s1, s1 + 0.3) }}><Kinetic text="Here's a thought." at={0.6} size={54} weight={600} color={DIM} /></div>
        </AbsoluteFill>
      )}
      {/* a wall of footage */}
      {wall && (
        <AbsoluteFill style={{ perspective: 1400 }}>
          {Array.from({ length: 12 }, (_, i) => {
            const col = i % 4, row = Math.floor(i / 4);
            const s = sp(f, s1 + 0.1 + i * 0.07, { damping: 16 });
            const x = 120 + col * 440 + (row % 2) * 90, y = 150 + row * 270;
            return <div key={i} style={{ position: "absolute", left: x, top: y, width: 360, height: 220, borderRadius: 14, overflow: "hidden", transform: `translateZ(${(1 - s) * -900}px) translateY(${Math.sin(t * 0.9 + i) * 8}px)`, opacity: s * 0.8, boxShadow: "0 30px 60px -30px rgba(0,0,0,.9), 0 0 0 1px rgba(255,255,255,.1)" }}>
              <Img src={staticFile(`thumbs/w${i}.jpg`)} style={{ width: "100%", height: "100%", objectFit: "cover", filter: "saturate(.75) brightness(.8)" }} />
            </div>;
          })}
          <AbsoluteFill style={{ background: "rgba(5,6,8,.35)" }} />
          <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", padding: "0 120px" }}>
            <Kinetic text="Millions of people, every day," at={s1 + 0.3} size={74} weight={700} color={DIM} />
            <Kinetic text="film themselves doing things." at={s1 + 1.3} size={104} hot={["film"]} />
          </AbsoluteFill>
        </AbsoluteFill>
      )}
      {/* three hard cuts with the word cut out of the footage */}
      {CUTS.map(([word, src, from, at], i) => {
        const end = i < 2 ? CUTS[i + 1][3] : cardsAt;
        if (t < at || t >= end) return null;
        return <AbsoluteFill key={word}>
          <div style={{ width: W, height: H, transform: `scale(${1.02 + 0.06 * lin(t, at, end)})` }}><Clip src={src} w={W} h={H} rate={1.3} from={from} /></div>
          <MaskWord word={word} reveal={at + 0.95} />
          <Flash at={at} dur={0.18} />
        </AbsoluteFill>;
      })}
      {/* the three collapse into one card */}
      {t >= cardsAt && (
        <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", perspective: 1800 }}>
          <AbsoluteFill style={{ background: INK, opacity: ramp(t, cardsAt, cardsAt + 0.4) }} />
          {CUTS.map(([, src, from], i) => {
            const gather = ramp(t, cardsAt + 1.4, cardsAt + 2.3), s = sp(f, cardsAt + 0.1 + i * 0.1, { damping: 16 });
            const keep = i === 0;
            const x = (i - 1) * 560 * (1 - gather), rot = (i - 1) * -12 * (1 - gather);
            const flip = ramp(t, flipAt, flipAt + 0.7);
            const shrink = ramp(t, dotAt, dotAt + 0.6);
            if (!keep && gather >= 1) return null;
            const xk = keep ? (i - 1) * 560 * (1 - gather) : x;
            return <div key={src} style={{ position: "absolute", width: 520, height: 300, left: W / 2 - 260, top: H / 2 - 150 - 40,
              transform: `translateX(${xk}px) scale(${(0.7 + 0.3 * s) * (1 - shrink * 0.97)}) rotateY(${rot + (keep ? flip * 180 : 0)}deg)`, opacity: Math.min(1, s * 1.5) * (keep ? 1 : 1 - gather), transformStyle: "preserve-3d" }}>
              <div style={{ position: "absolute", inset: 0, borderRadius: 22, overflow: "hidden", backfaceVisibility: "hidden", boxShadow: `0 40px 80px -30px rgba(0,0,0,.9), 0 0 0 1.5px rgba(255,255,255,.2), 0 0 ${60 * gather}px -10px ${CYAN}88` }}><Clip src={src} w={520} h={300} rate={1.2} from={from + 6} /></div>
              <div style={{ position: "absolute", inset: 0, borderRadius: 22, backfaceVisibility: "hidden", transform: "rotateY(180deg)", background: "#0b0d14", padding: 22, display: "grid", gap: 8, alignContent: "start", boxShadow: `0 0 0 1.5px ${CYAN}88, 0 0 60px -10px ${CYAN}88` }}>
                <div style={{ fontFamily: FONT, fontSize: 20, fontWeight: 800, color: CYAN }}>A skill it can check</div>
                {world.steps.slice(0, 5).map((st, j) => <div key={st.id} style={{ display: "flex", gap: 10, alignItems: "center", fontFamily: FONT, fontSize: 17, fontWeight: 600, color: WHITE, opacity: ramp(t, flipAt + 0.5 + j * 0.12, flipAt + 0.8 + j * 0.12) }}>
                  <span style={{ width: 22, height: 22, borderRadius: 11, background: GREEN, color: INK, display: "grid", placeItems: "center", fontSize: 13, fontWeight: 900 }}>✓</span><span style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{st.do.replace(/\{(\w+)\}/g, (_: string, n: string) => String((world as any).inputs?.[n] ?? n))}</span>
                </div>)}
              </div>
            </div>;
          })}
          <div style={{ position: "absolute", top: 740, left: 0, right: 0, display: "flex", justifyContent: "center", opacity: 1 - ramp(t, dotAt, dotAt + 0.4) }}>
            <Kinetic text="What if a computer could watch just one of these," at={cardsAt + 0.3} size={54} weight={700} color={DIM} hot={["one"]} />
          </div>
          <div style={{ position: "absolute", top: 810, left: 0, right: 0, display: "flex", justifyContent: "center", opacity: 1 - ramp(t, dotAt, dotAt + 0.4) }}>
            <Kinetic text="and actually learn the skill?" at={flipAt + 0.2} size={70} hot={["learn"]} />
          </div>
          {t > dotAt + 0.4 && <div style={{ position: "absolute", left: W / 2 - 9, top: H / 2 - 49, width: 18, height: 18, borderRadius: 9, background: CYAN, boxShadow: `0 0 40px ${CYAN}, 0 0 90px ${CYAN}88`, transform: `scale(${1 + 2 * ramp(t, dotAt + 0.4, timing.durations[0])})` }} />}
        </AbsoluteFill>
      )}
      <Flash at={S("hook", 2) - 0.03} dur={0.1} />
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ 2. name */

const Name: React.FC = () => {
  const t = useT();
  return (
    <AbsoluteFill>
      <Bg glow={1.3} />
      <Flash at={0} dur={0.3} />
      {[0, 0.18, 0.36].map((d, i) => { const p = lin(t, d, d + 1.5); return <div key={i} style={{ position: "absolute", left: W / 2, top: H / 2 - 20, width: 40 + p * 2600, height: 40 + p * 2600, borderRadius: "50%", transform: "translate(-50%,-50%)", border: `${3 - 2.5 * p}px solid ${CYAN}`, opacity: (1 - p) * 0.9 }} />; })}
      {Array.from({ length: 60 }, (_, i) => { const p = lin(t, 0.05, 1.5); const a = rnd(i, 3) * Math.PI * 2, r = p * (300 + rnd(i) * 900); return <div key={i} style={{ position: "absolute", left: W / 2 + Math.cos(a) * r, top: H / 2 - 20 + Math.sin(a) * r * 0.7, width: 3 + rnd(i, 2) * 4, height: 3 + rnd(i, 2) * 4, borderRadius: "50%", background: i % 4 ? WHITE : CYAN, opacity: (1 - p) * 0.9 }} />; })}
      <Cam push={0.03} shakeAt={0.02} amp={10}>
        <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
          <Logo at={0.05} footage flare={2.0} />
          <div style={{ marginTop: 40 }}><Kinetic text="Show it once. It learns the skill." at={S("name", 1)} size={56} weight={700} color={DIM} hot={["once"]} /></div>
        </AbsoluteFill>
      </Cam>
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ 3. learn */

const Learn: React.FC = () => {
  const t = useT(); const f = useCurrentFrame();
  const VW = 900, VH = 506;
  const s = sp(f, 0.15, { damping: 16 });
  const listAt = S("learn", 1) + 0.4, recipeAt = S("learn", 2);
  const notes = world.notes.filter((_, i) => i % 2 === 0).slice(2, 10);
  return (
    <AbsoluteFill>
      <Bg hero="hero/kitchen.jpg" glow={0.7} />
      <Cam push={0.03}>
        <div style={{ position: "absolute", left: 90, top: 118 }}>
          <Kinetic text="First, it watches." at={0.5} size={64} align="flex-start" />
        </div>
        <div style={{ position: "absolute", left: 90, top: 250, transform: `translateX(${(1 - s) * -500}px) perspective(1800px) rotateY(${5 + 10 * (1 - s)}deg)`, opacity: s }}>
          <Frame w={VW} h={VH}>
            <Clip src="tomato_demo" w={VW} h={VH} rate={1.5} />
            <Scan />
            <Brackets />
            <div style={{ position: "absolute", left: 20, top: 18, display: "flex", gap: 8, alignItems: "center", fontFamily: MONO, fontSize: 16, color: CYAN, background: "rgba(5,6,8,.65)", padding: "6px 12px", borderRadius: 8 }}><span style={{ width: 8, height: 8, borderRadius: 4, background: CYAN, opacity: 0.5 + 0.5 * Math.sin(t * 5) }} />WATCHING · 1 FRAME / SEC</div>
          </Frame>
          {/* notes fly off the frame */}
          {notes.map((n, i) => {
            const at = 1.0 + i * 0.55; if (t < at || t > at + 1.4) return null;
            const p = ramp(t, at, at + 1.2);
            return <div key={i} style={{ position: "absolute", left: VW - 40 + p * 160, top: 80 + i * 44 - p * 60, fontFamily: FONT, fontSize: 18, fontWeight: 700, color: INK, background: CYAN, padding: "6px 12px", borderRadius: 10, opacity: Math.sin(Math.PI * p), transform: `scale(${0.8 + 0.3 * p})`, whiteSpace: "nowrap", boxShadow: `0 0 20px ${CYAN}88` }}>{n.a}</div>;
          })}
        </div>
        <div style={{ position: "absolute", left: 1070, top: 118, width: 780 }}>
          <Kinetic text="Then it writes the recipe." at={S("learn", 1)} size={64} align="flex-start" hot={["recipe."]} />
          <div style={{ position: "relative", marginTop: 34, display: "grid", gap: 9 }}>
            <div style={{ position: "absolute", left: 17, top: 10, bottom: 10, width: 2, background: `linear-gradient(180deg, ${CYAN}, transparent)`, transform: `scaleY(${ramp(t, listAt, listAt + 3)})`, transformOrigin: "top" }} />
            {world.steps.slice(0, 9).map((st, i) => {
              const at = listAt + i * 0.28, p = sp(f, at, SNAP), ok = sp(f, at + 0.45, { damping: 7, stiffness: 260 }), done = t > at + 0.45;
              return <div key={st.id} style={{ display: "flex", alignItems: "center", gap: 14, padding: "10px 14px 10px 4px", transform: `translateY(${(1 - p) * 50}px) translateX(${(1 - p) * 120}px)`, opacity: Math.min(1, p * 1.5) }}>
                <span style={{ width: 30, height: 30, borderRadius: 15, display: "grid", placeItems: "center", background: done ? GREEN : "#13161f", border: done ? "none" : `2px solid ${CYAN}`, color: done ? INK : CYAN, fontFamily: FONT, fontWeight: 900, fontSize: 15, transform: `scale(${done ? 0.6 + 0.4 * ok : 1})`, boxShadow: done ? `0 0 16px ${GREEN}` : "none", flex: "none" }}>{done ? "✓" : st.id}</span>
                <span style={{ fontFamily: FONT, fontSize: 24, fontWeight: 650, color: WHITE, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{st.do.replace(/\{(\w+)\}/g, (_: string, n: string) => String((world as any).inputs?.[n] ?? n))}</span>
              </div>;
            })}
          </div>
        </div>
        <div style={{ position: "absolute", left: 90, top: 800 }}>{t > recipeAt && <Stamp at={recipeAt} ghost size={30} rot={0}>Steps · order · what "done" looks like</Stamp>}</div>
      </Cam>
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ 4-5. live, alert */

const PW = 430, PH = 860;
const Phone: React.FC<{ from: number; rate: number; tilt?: number; shake?: number; glitch?: number; children?: React.ReactNode }> = ({ from, rate, tilt = -12, shake: sh = 0, glitch = 0, children }) => {
  const iw = PW - 26, ih = PH - 26, vw = Math.round(ih * 16 / 9);
  const t = useT();
  const inner = (extra?: React.CSSProperties, key?: string) => (
    <div key={key} style={{ position: "absolute", inset: 0, ...extra }}>
      <Video src={staticFile("clips/cabinet_power_on.mp4")} muted playbackRate={rate} trimBefore={Math.round(from * FPS)} style={{ width: vw, height: ih, display: "block", marginLeft: -Math.round((vw - iw) / 2), filter: "contrast(1.08) saturate(.9)" }} />
    </div>
  );
  return (
    <div style={{ transform: `perspective(2200px) rotateY(${tilt}deg) rotateX(2deg) translate(${sh}px, ${sh * 0.5}px)` }}>
      <div style={{ position: "relative", width: PW, height: PH, borderRadius: 52, background: "linear-gradient(160deg, #1a1d29, #07080d)", padding: 13, boxShadow: `0 0 0 1.5px rgba(255,255,255,.25), inset 0 0 0 1px rgba(0,0,0,.6), 0 90px 150px -40px rgba(0,0,0,.95), 0 0 180px -40px ${COBALT}99` }}>
        <div style={{ position: "relative", width: iw, height: ih, borderRadius: 40, overflow: "hidden", background: "#000" }}>
          {inner()}
          {glitch > 0 && <>
            {inner({ clipPath: "inset(18% 0 62% 0)", transform: `translateX(${glitch * 26}px)`, filter: "hue-rotate(140deg) saturate(3)", mixBlendMode: "screen", opacity: 0.9 })}
            {inner({ clipPath: "inset(55% 0 20% 0)", transform: `translateX(${-glitch * 34}px)`, filter: "hue-rotate(-90deg) saturate(3)", mixBlendMode: "screen", opacity: 0.9 })}
            {inner({ clipPath: "inset(80% 0 5% 0)", transform: `translateX(${glitch * 18}px) scaleY(1.2)`, opacity: 0.9 })}
            <div style={{ position: "absolute", inset: 0, backgroundImage: "repeating-linear-gradient(0deg, rgba(255,255,255,.12) 0 2px, transparent 2px 7px)", opacity: glitch }} />
          </>}
          <div style={{ position: "absolute", left: "50%", top: 12, width: 112, height: 32, borderRadius: 16, background: "#000", transform: "translateX(-50%)" }} />
          <div style={{ position: "absolute", inset: 0, background: "linear-gradient(115deg, rgba(255,255,255,.12), transparent 35%)", pointerEvents: "none", opacity: 0.6 + 0.2 * Math.sin(t) }} />
          {children}
        </div>
      </div>
    </div>
  );
};

const HUD: React.FC<{ step: string; next: string; n: number; of: number; danger?: boolean; progressAt?: number }> = ({ step, next, n, of, danger, progressAt = -1 }) => {
  const t = useT();
  return (
    <>
      <div style={{ position: "absolute", left: 16, top: 58, display: "flex", alignItems: "center", gap: 8, fontFamily: FONT, fontSize: 15, fontWeight: 800, color: "#fff", background: "rgba(5,6,8,.72)", padding: "6px 11px", borderRadius: 999 }}>
        <span style={{ width: 9, height: 9, borderRadius: 5, background: CORAL, opacity: 0.4 + 0.6 * Math.abs(Math.sin(t * 4)), boxShadow: `0 0 10px ${CORAL}` }} />LIVE
      </div>
      <div style={{ position: "absolute", left: 16, right: 16, top: 104, display: "flex", gap: 4 }}>
        {Array.from({ length: of }, (_, i) => <div key={i} style={{ flex: 1, height: 4, borderRadius: 2, background: i < n - 1 ? (danger ? CORAL : GREEN) : i === n - 1 ? CYAN : "rgba(255,255,255,.25)", opacity: i === n - 1 ? 0.6 + 0.4 * Math.sin(t * 5) : 1, transform: `scaleX(${i < n ? ramp(t, progressAt + i * 0.15, progressAt + 0.3 + i * 0.15) : 1})`, transformOrigin: "left" }} />)}
      </div>
      <div style={{ position: "absolute", left: 16, right: 16, bottom: 22, display: "grid", gap: 8 }}>
        <div style={{ fontFamily: FONT, fontSize: 14, fontWeight: 800, color: danger ? CORAL : CYAN, letterSpacing: "0.04em" }}>STEP {n} OF {of}</div>
        <div style={{ fontFamily: FONT, fontSize: 23, fontWeight: 800, color: "#fff", lineHeight: 1.15, textShadow: "0 2px 12px rgba(0,0,0,.8)" }}>{step}</div>
        <div style={{ fontFamily: FONT, fontSize: 15, fontWeight: 700, color: "#fff", background: danger ? CORAL : COBALT, padding: "8px 12px", borderRadius: 12, justifySelf: "start", boxShadow: `0 10px 30px -10px ${danger ? CORAL : COBALT}` }}>{danger ? "Do first: " : "Next: "}{next}</div>
      </div>
    </>
  );
};

const Live: React.FC = () => {
  const t = useT(); const f = useCurrentFrame();
  const s = sp(f, 0.2, { damping: 15 });
  const camAt = S("live", 1), knowAt = S("live", 2);
  return (
    <AbsoluteFill>
      <Bg hero="hero/phone.jpg" glow={0.8} />
      <Cam push={0.03}>
        {[0, 0.8, 1.6].map((d, i) => { if (t < camAt + d) return null; const p = ((t - camAt - d) / 2.4) % 1; return <div key={i} style={{ position: "absolute", left: 560, top: 540, width: 120 + p * 1500, height: 120 + p * 1500, borderRadius: "50%", transform: "translate(-50%,-50%)", border: `1.5px solid ${CYAN}`, opacity: (1 - p) * 0.4 }} />; })}
        <div style={{ position: "absolute", left: 345, top: 110, transform: `translateY(${(1 - s) * 600}px)`, opacity: s }}>
          <Phone from={6} rate={1.5}><HUD step="Open the cabinet door" next="Remove the old component" n={2} of={7} progressAt={knowAt} />{t > camAt && <Brackets size={28} inset={14} />}</Phone>
        </div>
        <div style={{ position: "absolute", left: 930, top: 250, width: 900 }}>
          <Kinetic text="Then it watches you." at={0.5} size={96} align="flex-start" hot={["you."]} />
          <Kinetic text="Through any camera." at={camAt} size={62} weight={700} color={DIM} align="flex-start" style={{ marginTop: 16 }} />
          <div style={{ marginTop: 44, display: "grid", gap: 12, justifyItems: "start" }}>
            {t > knowAt && <Stamp at={knowAt} ghost size={30} rot={0}>Knows the step you're on</Stamp>}
            {t > knowAt + 0.9 && <Stamp at={knowAt + 0.9} ghost size={30} rot={0}>Tells you what comes next</Stamp>}
          </div>
        </div>
      </Cam>
    </AbsoluteFill>
  );
};

const Alert: React.FC = () => {
  const t = useT();
  const hit = S("alert", 1) - 0.15, then = S("alert", 2), after = S("alert", 3);
  const g = t > hit && t < hit + 0.42 ? (1 - lin(t, hit, hit + 0.42)) * (0.5 + 0.5 * Math.abs(Math.sin(t * 90))) : 0;
  const red = t > hit ? (0.5 + 0.5 * Math.abs(Math.sin((t - hit) * 5))) * (1 - 0.5 * lin(t, hit + 2, hit + 4)) : 0;
  const tension = lin(t, 0.4, hit);
  return (
    <AbsoluteFill>
      <Bg glow={0.6 - 0.4 * tension} />
      <AbsoluteFill style={{ background: `radial-gradient(70% 70% at 50% 50%, transparent 35%, ${CORAL})`, opacity: red * 0.55 }} />
      <Cam push={0.02} shakeAt={hit} amp={22}>
        <div style={{ position: "absolute", left: 345, top: 110, filter: `saturate(${1 - 0.5 * tension})` }}>
          <Phone from={19} rate={1.2} glitch={g}>
            <HUD step={t > hit ? "Removing the old component" : "Removing the old component"} next={t > hit ? "Turn the power OFF" : "Turn the power OFF"} n={3} of={7} danger={t > hit} />
            <div style={{ position: "absolute", inset: 0, background: CORAL, opacity: red * 0.35, mixBlendMode: "multiply" }} />
            {t > hit && <div style={{ position: "absolute", inset: 8 }}><Ants color={CORAL} width={6} radius={34} glow /></div>}
          </Phone>
        </div>
        <div style={{ position: "absolute", left: 930, top: 250, width: 920, display: "grid", gap: 22, justifyItems: "start" }}>
          <div style={{ opacity: 1 - ramp(t, hit - 0.1, hit) }}><Kinetic text="And if you miss something?" at={0.5} size={70} weight={700} color={DIM} align="flex-start" /></div>
          {t > hit && <Stamp at={hit} size={124} rot={-6}>STOP.</Stamp>}
          {t > hit + 0.35 && <Stamp at={hit + 0.35} size={40} rot={0} ghost style={{ border: `2px solid ${CORAL}`, boxShadow: `0 0 50px ${CORAL}55` }}>The power is still on.</Stamp>}
          <div style={{ display: "flex", gap: 20, marginTop: 30 }}>
            {t > then && <Stamp at={then} size={58} rot={-2} color={WHITE} style={{ color: INK, boxShadow: "none" }}>Right then.</Stamp>}
            {t > after && <Stamp at={after} size={58} rot={2} ghost>Not after.</Stamp>}
          </div>
        </div>
      </Cam>
      <Flash at={hit} dur={0.12} color={CORAL} />
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ 6. robot */

const Robot: React.FC = () => {
  const t = useT(); const f = useCurrentFrame();
  const VW = 1480, VH = 832;
  const open = ramp(t, 0, 1.1);
  const cutB = 8.5, cutC = 12.5, knock = S("robot", 2) + 0.3, noticed = knock + 1.1, fixed = S("robot", 3) + 0.6;
  const s = sp(f, 0.05, { damping: 16 });
  return (
    <AbsoluteFill>
      <Bg hero="hero/robot.jpg" glow={0.9} />
      <div style={{ position: "absolute", left: 90, top: 112 }}><Kinetic text="Not just for people." at={0.5} size={66} align="flex-start" hot={["people."]} /></div>
      <Cam push={0.025} shakeAt={knock} amp={16}>
        <div style={{ position: "absolute", left: (W - VW) / 2, top: 212, transform: `scale(${0.92 + 0.08 * s})`, clipPath: `circle(${open * 80}% at 50% 50%)` }}>
          <Frame w={VW} h={VH}>
            {t < cutB && <Clip src="robot_demo" w={VW} h={VH} rate={2.5} from={2} />}
            {t >= cutB && t < cutC && <Sequence from={Math.round(cutB * FPS)} layout="none"><Clip src="robot_eidos" w={VW} h={VH} rate={1} from={19.5} /></Sequence>}
            {t >= cutC && <Sequence from={Math.round(cutC * FPS)} layout="none"><Clip src="robot_eidos" w={VW} h={VH} rate={7} from={23.5} /></Sequence>}
            <Brackets color={t > fixed ? GREEN : CYAN} />
            <div style={{ position: "absolute", right: 24, top: 18, fontFamily: MONO, fontSize: 16, color: WHITE, background: "rgba(5,6,8,.65)", padding: "6px 12px", borderRadius: 8 }}>{t < cutB ? "THE DEMONSTRATION" : "CHECKS ON"}</div>
            <Flash at={cutB} dur={0.12} /><Flash at={cutC} dur={0.1} />
          </Frame>
        </div>
        <div style={{ position: "absolute", left: 230, top: 170 }}>{t > 1.2 && t < cutB && <Stamp at={1.2} ghost size={34} rot={0}>Shown once</Stamp>}</div>
        <div style={{ position: "absolute", left: 300, top: 640 }}>{t > knock && t < fixed && <Stamp at={knock} size={66} rot={-7}>Knocked over</Stamp>}</div>
        <div style={{ position: "absolute", right: 300, top: 640 }}>{t > noticed && t < fixed && <Stamp at={noticed} size={54} rot={3} ghost style={{ border: `2px solid ${CYAN}` }}>Noticed.</Stamp>}</div>
        <div style={{ position: "absolute", left: 0, right: 0, top: 560, display: "flex", justifyContent: "center" }}>{t > fixed && <Stamp at={fixed} size={128} rot={-3} color={GREEN}>Fixed. ✓</Stamp>}</div>
        {t > fixed && Array.from({ length: 50 }, (_, i) => { const p = lin(t, fixed, fixed + 1.5); const a = rnd(i, 9) * Math.PI * 2; return <div key={i} style={{ position: "absolute", left: W / 2 + Math.cos(a) * p * (200 + rnd(i) * 600), top: 620 + Math.sin(a) * p * (160 + rnd(i) * 400) + p * p * 350, width: 7 + rnd(i, 2) * 10, height: 7 + rnd(i, 2) * 10, borderRadius: 2, background: [GREEN, CYAN, WHITE][i % 3], opacity: 1 - p, transform: `rotate(${t * 500 * rnd(i, 3)}deg)` }} />; })}
      </Cam>
      <Flare at={fixed} y={620} />
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ 7. meta */

const MODELS: [string, string, string][] = [["Muse Spark", "watches", CYAN], ["Muse Wonder", "compiles", "#c77dff"], ["SAM 3.1", "outlines", GREEN], ["Muse Image", "draws", "#ffb84d"], ["Muse Spark Open", "open weights", CYAN]];
const Meta: React.FC = () => {
  const t = useT(); const f = useCurrentFrame();
  const cx = W / 2, cy = 600, R = 360;
  const settle = ramp(t, 4.0, 5.2);
  return (
    <AbsoluteFill>
      <Bg glow={1.1} />
      <div style={{ position: "absolute", left: 0, right: 0, top: 120, display: "flex", justifyContent: "center" }}><Kinetic text="Built on Meta's AI models." at={0.5} size={78} hot={["Meta's"]} /></div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 222, display: "flex", justifyContent: "center" }}><Kinetic text="Meta Global AI Hackathon 2026" at={1.3} size={28} weight={700} color={DIM} wide /></div>
      <Cam push={0.02}>
        <svg width={W} height={H} style={{ position: "absolute", inset: 0 }}>
          {MODELS.map((_, i) => { const a = ((t * 18 + i * 72) * Math.PI) / 180; const ox = cx + Math.cos(a) * R, oy = cy + Math.sin(a) * R * 0.5; const lx = 300 + i * 330, ly = 780; const x = ox + (lx - ox) * settle, y = oy + (ly - oy) * settle; const p = ramp(t, 0.8 + i * 0.15, 1.5 + i * 0.15); return <line key={i} x1={cx} y1={cy} x2={cx + (x - cx) * p} y2={cy + (y - cy) * p} stroke={CYAN} strokeWidth={1.5} strokeDasharray="3 9" strokeDashoffset={-t * 40} opacity={0.55} />; })}
        </svg>
        <div style={{ position: "absolute", left: cx - 90, top: cy - 90, width: 180, height: 180, borderRadius: 90, background: `radial-gradient(circle at 40% 35%, #5d86ff, ${COBALT} 55%, #0a1550)`, boxShadow: `0 0 90px ${COBALT}, 0 0 180px ${COBALT}66`, display: "grid", placeItems: "center", fontFamily: FONT, fontWeight: 900, fontSize: 38, letterSpacing: "0.08em", fontVariationSettings: '"wdth" 125', color: "#fff", transform: `scale(${sp(f, 0.3, { damping: 10 })})` }}>EIDOS</div>
        {MODELS.map(([name, job, c], i) => {
          const a = ((t * 18 + i * 72) * Math.PI) / 180; const s = sp(f, 0.8 + i * 0.15, { damping: 11 });
          const ox = cx + Math.cos(a) * R, oy = cy + Math.sin(a) * R * 0.5; const lx = 300 + i * 330, ly = 780;
          const x = ox + (lx - ox) * settle, y = oy + (ly - oy) * settle; const front = Math.sin(a) > -0.3 || settle > 0.5;
          return <div key={name} style={{ position: "absolute", left: x - 130, top: y - 56, width: 260, display: "grid", justifyItems: "center", gap: 6, transform: `scale(${s * (front ? 1 : 0.85)})`, opacity: s * (front ? 1 : 0.65), zIndex: front ? 2 : 0 }}>
            <div style={{ width: 62, height: 62, borderRadius: 31, background: `radial-gradient(circle at 40% 35%, #fff, ${c} 50%, transparent 72%)`, boxShadow: `0 0 44px ${c}` }} />
            <div style={{ fontFamily: FONT, fontSize: 28, fontWeight: 900, color: WHITE, textAlign: "center", lineHeight: 1 }}>{name}</div>
            <div style={{ fontFamily: FONT, fontSize: 19, fontWeight: 650, color: DIM }}>{job}</div>
          </div>;
        })}
      </Cam>
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ 8. close */

const Close: React.FC = () => {
  const t = useT();
  const end = timing.durations[7], logoAt = S("close", 1) - 0.1, onceAt = S("close", 2), dotAt = end - 2.2;
  return (
    <AbsoluteFill>
      <Bg hero="hero/workshop.jpg" glow={0.8} />
      <Cam push={0.02}>
        <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
          <div style={{ opacity: 1 - ramp(t, logoAt - 0.3, logoAt), transform: `translateY(${-ramp(t, logoAt - 0.3, logoAt) * 40}px)`, position: "absolute", textAlign: "center" }}>
            <Kinetic text="Made by Maruthi Kunchala" at={0.6} size={64} weight={800} />
            <Kinetic text="with Team PULSE - Parallax" at={1.6} size={40} weight={700} color={DIM} style={{ marginTop: 14 }} />
          </div>
          {t > logoAt && <div style={{ opacity: 1 - ramp(t, dotAt, dotAt + 0.5), transform: `scale(${1 - 0.4 * ramp(t, dotAt, dotAt + 0.5)})`, display: "grid", justifyItems: "center" }}>
            <Logo at={logoAt} size={210} flare={logoAt + 1.0} />
            <div style={{ marginTop: 40 }}><Kinetic text="Show it once." at={onceAt} size={104} step={0.16} hot={["once."]} /></div>
          </div>}
          {t > dotAt + 0.3 && <div style={{ position: "absolute", width: 14, height: 14, borderRadius: 7, background: CYAN, boxShadow: `0 0 30px ${CYAN}, 0 0 80px ${CYAN}66`, opacity: (1 - ramp(t, end - 0.9, end - 0.3)) * (0.6 + 0.4 * Math.sin(t * 6)) }} />}
        </AbsoluteFill>
      </Cam>
      <AbsoluteFill style={{ background: INK, opacity: ramp(t, end - 0.8, end - 0.1) }} />
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ assembly */

const SCENES: React.FC[] = [Hook, Name, Learn, Live, Alert, Robot, Meta, Close];
const frames = timing.durations.map((d) => Math.round(d * FPS));
const TR = Math.round(timing.tr * FPS);
export const v7Frames = frames.reduce((a, b) => a + b, 0) - TR * (frames.length - 1);
const starts = frames.map((_, i) => frames.slice(0, i).reduce((a, b) => a + b, 0) - TR * i);

export const V7: React.FC = () => (
  <AbsoluteFill style={{ background: INK }}>
    <TransitionSeries>
      {SCENES.flatMap((C, i) => {
        const id = timing.ids[i];
        const items = [<TransitionSeries.Sequence key={id} durationInFrames={frames[i]}><C /><Caption id={id} /></TransitionSeries.Sequence>];
        if (i < SCENES.length - 1) items.push(<TransitionSeries.Transition key={id + "-t"} presentation={fade()} timing={linearTiming({ durationInFrames: TR })} />);
        return items;
      })}
    </TransitionSeries>
    <Film />
    {timing.ids.map((id, i) => (
      <Sequence key={id} from={starts[i] + Math.round(LEAD * FPS)} durationInFrames={Math.round(VO(id).seconds * FPS) + 10}>
        <Audio src={staticFile(`${(timing as any).vo || "vo7"}/${id}.wav`)} volume={1} />
      </Sequence>
    ))}
    <Audio src={staticFile("music/bed_v7.mp3")} volume={(f: number) => 0.5 * interpolate(f, [v7Frames - 60, v7Frames - 4], [1, 0], clamp)} />
  </AbsoluteFill>
);
