// EIDOS, the cut for family and friends: cinematic dark look, kinetic type, 3D footage carousel,
// scan reveals, stamps and particle bursts. Plain words, no benchmark numbers.
import React from "react";
import { AbsoluteFill, Img, interpolate, Sequence, spring, staticFile, useCurrentFrame } from "remotion";
import { Audio, Video } from "@remotion/media";
import { TransitionSeries, linearTiming } from "@remotion/transitions";
import { slide } from "@remotion/transitions/slide";
import { fade } from "@remotion/transitions/fade";
import { wipe } from "@remotion/transitions/wipe";
import { clockWipe } from "@remotion/transitions/clock-wipe";
import { iris } from "@remotion/transitions/iris";
import { FONT, MONO, ease } from "./ui";
import timeline from "./timeline_family.json";
import timing from "./family_timing.json";
import world from "./world_data.json";

const FPS = 30;
const W = 1920, H = 1080;
const BG = "#05060d", WHITE = "#f4f6ff", DIM = "rgba(244,246,255,.62)";
const COBALT = "#2b5cff", CYAN = "#19d3ff", MAGENTA = "#ff3df2", CORAL = "#ff4d5e", GREEN = "#19e0a0";
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const useT = () => useCurrentFrame() / FPS;
const ramp = (t: number, a: number, b: number) => interpolate(t, [a, b], [0, 1], { ...clamp, easing: ease });
const lin = (t: number, a: number, b: number) => interpolate(t, [a, b], [0, 1], clamp);
const sp = (f: number, at: number, cfg: { damping?: number; mass?: number; stiffness?: number } = {}) =>
  spring({ frame: f - at * FPS, fps: FPS, config: { damping: 12, ...cfg } });
const VO = (id: string) => timeline.find((s) => s.id === id)!;
const rnd = (i: number, k = 0) => { const x = Math.sin(i * 127.1 + k * 311.7) * 43758.5453; return x - Math.floor(x); };

/* ------------------------------------------------------------------ atmosphere */

const Atmos: React.FC<{ hue?: [string, string]; drift?: number; burst?: number }> = ({ hue = [COBALT, CYAN], drift = 1, burst }) => {
  const t = useT();
  return (
    <AbsoluteFill style={{ background: BG, overflow: "hidden" }}>
      <div style={{ position: "absolute", width: 1300, height: 1300, borderRadius: "50%", background: hue[0], filter: "blur(220px)", opacity: 0.32,
        left: `calc(${22 + Math.sin(t * 0.35 * drift) * 8}% - 650px)`, top: `calc(${35 + Math.cos(t * 0.3 * drift) * 8}% - 650px)` }} />
      <div style={{ position: "absolute", width: 1000, height: 1000, borderRadius: "50%", background: hue[1], filter: "blur(200px)", opacity: 0.22,
        left: `calc(${76 + Math.cos(t * 0.28 * drift) * 7}% - 500px)`, top: `calc(${70 + Math.sin(t * 0.33 * drift) * 7}% - 500px)` }} />
      <div style={{ position: "absolute", width: 700, height: 700, borderRadius: "50%", background: MAGENTA, filter: "blur(220px)", opacity: 0.08,
        left: `calc(${60 + Math.sin(t * 0.2) * 10}% - 350px)`, top: `calc(${10}% - 350px)` }} />
      {/* particles in two parallax layers */}
      {Array.from({ length: 70 }, (_, i) => {
        const z = i % 2 ? 1 : 0.5, s = 2 + rnd(i) * 3 * z;
        let x = (rnd(i, 1) * 100 + t * (0.6 + rnd(i, 2)) * z) % 100, y = (rnd(i, 3) * 100 - t * (0.4 + rnd(i, 4) * 0.6) * z + 100) % 100;
        if (burst != null) { const r = ramp(t, burst, burst + 1.6); const a = rnd(i, 5) * Math.PI * 2; x = 50 + Math.cos(a) * r * (30 + rnd(i, 6) * 40); y = 50 + Math.sin(a) * r * (30 + rnd(i, 6) * 40); }
        return <div key={i} style={{ position: "absolute", left: `${x}%`, top: `${y}%`, width: s, height: s, borderRadius: "50%", background: i % 5 ? WHITE : CYAN,
          opacity: (0.25 + 0.55 * z) * (burst != null ? 1 - ramp(t, burst + 0.8, burst + 1.8) : 1), boxShadow: i % 5 ? "none" : `0 0 10px ${CYAN}` }} />;
      })}
      <AbsoluteFill style={{ backgroundImage: "repeating-linear-gradient(0deg, rgba(255,255,255,.035) 0 1px, transparent 1px 4px)", opacity: 0.7 }} />
      <AbsoluteFill style={{ backgroundImage: `url(${staticFile("noise.png")})`, backgroundSize: 512, backgroundPosition: `${(t * 97) % 512}px ${(t * 61) % 512}px`, opacity: 0.09, mixBlendMode: "overlay" }} />
      <AbsoluteFill style={{ background: "radial-gradient(75% 65% at 50% 50%, transparent 55%, rgba(0,0,0,.65))" }} />
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ type */

const Kinetic: React.FC<{ text: string; at: number; step?: number; size?: number; weight?: number; color?: string; glow?: string[]; style?: React.CSSProperties; align?: string }> =
  ({ text, at, step = 0.07, size = 96, weight = 850, color = WHITE, glow = [], style, align = "center" }) => {
    const t = useT();
    return (
      <div style={{ display: "flex", flexWrap: "wrap", justifyContent: align, columnGap: "0.28em", fontFamily: FONT, fontSize: size, fontWeight: weight, letterSpacing: "-0.035em", lineHeight: 1.05, color, ...style }}>
        {text.split(" ").map((w, i) => {
          const p = ramp(t, at + i * step, at + i * step + 0.7);
          const hot = glow.includes(w.replace(/[.,?!]/g, ""));
          return <span key={i} style={{ display: "inline-block", transform: `translateY(${(1 - p) * 70}px) scale(${0.85 + 0.15 * p})`, opacity: p, filter: `blur(${(1 - p) * 14}px)`,
            ...(hot ? { color: CYAN, textShadow: `0 0 30px ${CYAN}88, 0 0 70px ${COBALT}66` } : {}) }}>{w}</span>;
        })}
      </div>
    );
  };

const Stamp: React.FC<{ at: number; children: React.ReactNode; color?: string; size?: number; rot?: number; style?: React.CSSProperties }> = ({ at, children, color = CORAL, size = 54, rot = -5, style }) => {
  const f = useCurrentFrame();
  const s = sp(f, at, { damping: 9, stiffness: 220 });
  return (
    <div style={{ display: "inline-block", fontFamily: FONT, fontSize: size, fontWeight: 900, letterSpacing: "-0.02em", color: "#fff", padding: `${size * 0.3}px ${size * 0.6}px`, borderRadius: size * 0.3,
      background: color, boxShadow: `0 0 60px ${color}99, 0 30px 60px -20px rgba(0,0,0,.7)`, transform: `scale(${0.4 + 0.6 * s}) rotate(${rot * (1.6 - 0.6 * s)}deg)`, opacity: Math.min(1, s * 2), whiteSpace: "nowrap", ...style }}>{children}</div>
  );
};

const Ants: React.FC<{ color: string; draw?: number; width?: number; radius?: number; glow?: boolean }> = ({ color, draw = 1, width = 4, radius = 18, glow }) => {
  const t = useT();
  return (
    <svg width="100%" height="100%" style={{ position: "absolute", inset: 0, overflow: "visible", filter: glow ? `drop-shadow(0 0 10px ${color})` : undefined }}>
      <rect x={0} y={0} width="100%" height="100%" rx={radius} fill="none" stroke={color} strokeWidth={width} pathLength={100}
        strokeDasharray={draw < 1 ? `${100 * draw} 100` : "1.4 0.9"} strokeDashoffset={draw < 1 ? 0 : -t * 3} />
    </svg>
  );
};

const Brackets: React.FC<{ color?: string; size?: number; inset?: number }> = ({ color = CYAN, size = 44, inset = 18 }) => (
  <>{[[0, 0], [1, 0], [0, 1], [1, 1]].map(([x, y], i) => (
    <div key={i} style={{ position: "absolute", width: size, height: size, left: x ? undefined : inset, right: x ? inset : undefined, top: y ? undefined : inset, bottom: y ? inset : undefined,
      borderLeft: x ? undefined : `4px solid ${color}`, borderRight: x ? `4px solid ${color}` : undefined, borderTop: y ? undefined : `4px solid ${color}`, borderBottom: y ? `4px solid ${color}` : undefined,
      filter: `drop-shadow(0 0 8px ${color})` }} />
  ))}</>
);

const Frame: React.FC<{ w: number; h: number; children: React.ReactNode; style?: React.CSSProperties; radius?: number }> = ({ w, h, children, style, radius = 28 }) => (
  <div style={{ position: "relative", width: w, height: h, borderRadius: radius, overflow: "hidden", background: "#000",
    boxShadow: `0 0 0 1.5px rgba(255,255,255,.18), 0 0 0 8px rgba(255,255,255,.04), 0 80px 140px -50px rgba(0,0,0,.9), 0 0 120px -30px ${COBALT}88`, ...style }}>{children}</div>
);

const Clip: React.FC<{ src: string; w: number; h: number; rate?: number; from?: number }> = ({ src, w, h, rate = 1, from = 0 }) => (
  <Video src={staticFile(`clips/${src}.mp4`)} muted playbackRate={rate} trimBefore={Math.round(from * FPS)} style={{ width: w, height: h, display: "block", objectFit: "cover" }} />
);

const Scan: React.FC<{ period?: number; color?: string }> = ({ period = 2.6, color = CYAN }) => {
  const t = useT();
  const y = (t / period) % 1;
  return <div style={{ position: "absolute", left: 0, right: 0, top: `${y * 100}%`, height: 90, transform: "translateY(-90px)", background: `linear-gradient(180deg, transparent, ${color}33)`, borderBottom: `2px solid ${color}`, boxShadow: `0 0 24px ${color}` }} />;
};

const Caption: React.FC<{ id: string; at: number }> = ({ id, at }) => {
  const t = useT() - at;
  const vo = VO(id);
  const parts = (vo.text.replace(/Eye-doss/g, "EIDOS").replace(/A\.I\./g, "AI").replace(/Pulse Parallax/g, "PULSE - Parallax").match(/[^.!?]+[.!?]+/g) || [vo.text]);
  const total = parts.reduce((a, p) => a + p.length, 0);
  let acc = 0, cur = "";
  for (const p of parts) { const s = (acc / total) * vo.seconds, e = ((acc + p.length) / total) * vo.seconds; if (t >= s - 0.05 && t < e + 0.25) cur = p.trim(); acc += p.length; }
  if (t > vo.seconds + 0.4 || t < 0) cur = "";
  return (
    <div style={{ position: "absolute", left: 0, right: 0, bottom: 36, display: "flex", justifyContent: "center" }}>
      {cur && <div style={{ maxWidth: 1400, fontFamily: FONT, fontSize: 28, fontWeight: 600, color: WHITE, textAlign: "center", padding: "10px 24px", borderRadius: 14, background: "rgba(5,6,13,.62)", backdropFilter: "blur(12px)", border: "1px solid rgba(255,255,255,.12)" }}>{cur}</div>}
    </div>
  );
};

const Logo: React.FC<{ at: number; size?: number; sweep?: number }> = ({ at, size = 230, sweep }) => {
  const t = useT(); const f = useCurrentFrame();
  const draw = ramp(t, at, at + 1.1);
  const sw = sweep != null ? lin(t, sweep, sweep + 0.9) : -1;
  return (
    <div style={{ position: "relative", padding: `${size * 0.12}px ${size * 0.28}px` }}>
      <Ants color={CYAN} draw={draw} width={5} radius={size * 0.12} glow />
      <div style={{ position: "relative", display: "flex", fontFamily: FONT, fontSize: size, fontWeight: 900, letterSpacing: "0.08em", fontVariationSettings: '"wdth" 125', color: WHITE, overflow: "hidden" }}>
        {"EIDOS".split("").map((l, i) => {
          const s = sp(f, at + 0.1 + i * 0.08, { damping: 8, mass: 0.7 });
          return <span key={i} style={{ position: "relative", display: "inline-block", transform: `translateY(${(1 - s) * 180}px) scale(${0.3 + 0.7 * s})`, opacity: Math.min(1, s * 1.6) }}>
            <span style={{ position: "absolute", inset: 0, color: CYAN, transform: `translateX(${(1 - s) * -14}px)`, opacity: 0.8 * (1 - s) }}>{l}</span>
            <span style={{ position: "absolute", inset: 0, color: MAGENTA, transform: `translateX(${(1 - s) * 14}px)`, opacity: 0.8 * (1 - s) }}>{l}</span>
            <span style={{ position: "relative", textShadow: `0 0 40px ${COBALT}aa` }}>{l}</span>
          </span>;
        })}
        {sw >= 0 && sw < 1 && <div style={{ position: "absolute", top: -40, bottom: -40, width: 160, left: `${-20 + sw * 130}%`, background: "linear-gradient(100deg, transparent, rgba(255,255,255,.9), transparent)", transform: "skewX(-20deg)", mixBlendMode: "screen" }} />}
      </div>
    </div>
  );
};

/* ------------------------------------------------------------------ 1. open */

const Open: React.FC = () => {
  const t = useT();
  return (
    <AbsoluteFill>
      <Atmos />
      <div style={{ position: "absolute", left: "50%", top: 300, width: `${ramp(t, 0.1, 1.2) * 900}px`, height: 2, transform: "translateX(-50%)", background: `linear-gradient(90deg, transparent, ${CYAN}, transparent)`, boxShadow: `0 0 20px ${CYAN}` }} />
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", padding: "0 180px" }}>
        <Kinetic text="What if you could teach a computer" at={0.5} size={84} color={DIM} weight={700} />
        <Kinetic text="anything," at={2.0} size={170} glow={["anything"]} style={{ marginTop: 10 }} />
        <Kinetic text="just by showing it once?" at={2.8} size={84} style={{ marginTop: 10 }} />
      </AbsoluteFill>
      {t > 4.6 && <div style={{ position: "absolute", left: 1165, top: 630, width: 220, height: 112 }}><Ants color={CYAN} draw={ramp(t, 4.6, 5.4)} width={4} radius={16} glow /></div>}
      <AbsoluteFill style={{ background: "#fff", opacity: ramp(t, 7.0, 7.5) * 0.9 }} />
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ 2. montage */

const Montage: React.FC = () => {
  const t = useT(); const f = useCurrentFrame();
  const PICK = [0, 7, 10, 3, 9, 5, 11, 6]; const N = PICK.length;
  const speed = 14 + 60 * ramp(t, 6.2, 8.6);
  const theta = t * speed;
  const collapse = ramp(t, 8.2, 9.3);
  const words: [string, number][] = [["Cooking.", 1.5], ["Fixing.", 2.3], ["Building.", 3.1]];
  return (
    <AbsoluteFill>
      <Atmos hue={[COBALT, MAGENTA]} />
      <AbsoluteFill style={{ background: "#fff", opacity: 1 - ramp(t, 0, 0.5) }} />
      <div style={{ position: "absolute", left: W / 2, top: 640, filter: `blur(${ramp(t, 7.2, 8.6) * 8}px)` }}>
        {Array.from({ length: N }, (_, i) => {
          const a = ((theta + i * (360 / N)) * Math.PI) / 180;
          const s = sp(f, 0.2 + i * 0.06, { damping: 14 });
          const depth = (Math.cos(a) + 1) / 2;              // 1 = nearest
          const x = Math.sin(a) * 820 * s * (1 - collapse), y = (depth - 0.5) * 120 * (1 - collapse);
          const sc = (0.45 + 0.75 * depth) * (0.6 + 0.4 * s) * (1 - collapse);
          return <div key={i} style={{ position: "absolute", width: 400, height: 248, left: -200, top: -124, borderRadius: 20, overflow: "hidden", zIndex: Math.round(depth * 100),
            transform: `translate(${x}px, ${y}px) scale(${sc}) rotateY(${-Math.sin(a) * 28}deg)`, opacity: s * (0.35 + 0.65 * depth), filter: `brightness(${0.5 + 0.5 * depth})`,
            boxShadow: "0 40px 80px -30px rgba(0,0,0,.8), 0 0 0 1px rgba(255,255,255,.15)" }}>
            <Img src={staticFile(`thumbs/w${PICK[i]}.jpg`)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
            <div style={{ position: "absolute", inset: 0, background: `linear-gradient(180deg, transparent 60%, rgba(0,0,0,.6))` }} />
          </div>;
        })}
      </div>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "flex-start", paddingTop: 150, pointerEvents: "none" }}>
        <div style={{ display: "flex", gap: 28, opacity: 1 - ramp(t, 5.6, 6.1) }}>
          {words.map(([w, at]) => t > at && <Stamp key={w} at={at} color="rgba(255,255,255,.1)" size={64} rot={0} style={{ backdropFilter: "blur(10px)", border: "1.5px solid rgba(255,255,255,.25)", boxShadow: "none" }}>{w}</Stamp>)}
        </div>
        {t > 5.9 && <div style={{ position: "absolute", top: 120 }}><Kinetic text="Billions of hours." at={5.9} size={190} step={0.12} glow={["Billions"]} /></div>}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ 3. name */

const Name: React.FC = () => {
  const t = useT();
  return (
    <AbsoluteFill>
      <Atmos burst={0.05} />
      {[0, 0.25, 0.5].map((d, i) => {
        const p = lin(t, d, d + 1.6);
        return <div key={i} style={{ position: "absolute", left: W / 2, top: H / 2, width: 60 + p * 2400, height: 60 + p * 2400, borderRadius: "50%", transform: "translate(-50%,-50%)", border: `${3 - 2 * p}px solid ${CYAN}`, opacity: (1 - p) * 0.8, boxShadow: `0 0 40px ${CYAN}66` }} />;
      })}
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        <div style={{ transform: `scale(${1 + 0.06 * (1 - ramp(t, 0.1, 0.9))})` }}><Logo at={0.1} sweep={2.1} /></div>
        <div style={{ marginTop: 44 }}><Kinetic text="Show it once. It learns the skill." at={2.3} size={56} weight={700} color={DIM} glow={["once"]} /></div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ 4. learn */

const Learn: React.FC = () => {
  const t = useT(); const f = useCurrentFrame();
  const VW = 880, VH = 495;
  const s = sp(f, 0.1, { damping: 15 });
  return (
    <AbsoluteFill>
      <Atmos hue={[CYAN, COBALT]} />
      <div style={{ position: "absolute", left: 90, top: 80 }}><Kinetic text="It watches. It writes the recipe." at={0.2} size={72} align="flex-start" glow={["recipe."]} /></div>
      <div style={{ position: "absolute", left: 90, top: 260, transform: `translateX(${(1 - s) * -400}px) perspective(1800px) rotateY(${8 * (1 - s) + 4}deg)`, opacity: s }}>
        <Frame w={VW} h={VH}>
          <Clip src="tomato_demo" w={VW} h={VH} rate={1.4} />
          <Scan />
          <Brackets />
          <div style={{ position: "absolute", left: 22, bottom: 20 }} />
          <div style={{ position: "absolute", left: 22, bottom: 20, fontFamily: MONO, fontSize: 18, color: CYAN, background: "rgba(5,6,13,.6)", padding: "6px 12px", borderRadius: 8 }}>watching {Math.floor(t * 1.4)}s, one frame a second</div>
        </Frame>
      </div>
      <div style={{ position: "absolute", left: 1050, top: 250, width: 790, display: "grid", gap: 10 }}>
        {world.steps.slice(0, 10).map((st, i) => {
          const at = 2.4 + i * 0.3;
          const p = sp(f, at, { damping: 13 });
          const ok = sp(f, at + 0.5, { damping: 7, stiffness: 240 });
          return <div key={st.id} style={{ display: "flex", alignItems: "center", gap: 14, padding: "12px 16px", borderRadius: 14, background: "rgba(255,255,255,.07)", border: "1px solid rgba(255,255,255,.12)", backdropFilter: "blur(10px)",
            transform: `translateX(${(1 - p) * 320}px) perspective(900px) rotateX(${(1 - p) * -40}deg)`, opacity: Math.min(1, p * 1.5) }}>
            <span style={{ width: 34, height: 34, borderRadius: 17, display: "grid", placeItems: "center", background: t > at + 0.5 ? GREEN : "rgba(255,255,255,.12)", color: "#05060d", fontFamily: FONT, fontWeight: 900, fontSize: 18, transform: `scale(${t > at + 0.5 ? 0.7 + 0.3 * ok : 1})`, boxShadow: t > at + 0.5 ? `0 0 18px ${GREEN}` : "none" }}>{t > at + 0.5 ? "✓" : st.id}</span>
            <span style={{ fontFamily: FONT, fontSize: 22, fontWeight: 650, color: WHITE, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{st.do.replace(/\{(\w+)\}/g, (_: string, n: string) => String((world as any).inputs?.[n] ?? n))}</span>
          </div>;
        })}
      </div>
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ 5-6. live, alert */

const Phone: React.FC<{ from: number; rate: number; tilt?: number; shake?: number; children?: React.ReactNode }> = ({ from, rate, tilt = -14, shake = 0, children }) => {
  const PW = 440, PH = 900;
  return (
    <div style={{ transform: `perspective(2000px) rotateY(${tilt}deg) translate(${shake}px, ${shake * 0.6}px)` }}>
      <div style={{ position: "relative", width: PW, height: PH, borderRadius: 54, background: "#0b0d18", padding: 14, boxShadow: `0 0 0 2px rgba(255,255,255,.2), 0 90px 150px -40px rgba(0,0,0,.95), 0 0 160px -30px ${COBALT}aa` }}>
        <div style={{ position: "relative", width: PW - 28, height: PH - 28, borderRadius: 42, overflow: "hidden", background: "#000" }}>
          <Video src={staticFile("clips/cabinet_power_on.mp4")} muted playbackRate={rate} trimBefore={Math.round(from * FPS)} style={{ width: Math.round((PH - 28) * 16 / 9), height: PH - 28, display: "block", marginLeft: -Math.round(((PH - 28) * 16 / 9 - (PW - 28)) / 2) }} />
          <div style={{ position: "absolute", left: "50%", top: 14, width: 120, height: 34, borderRadius: 17, background: "#000", transform: "translateX(-50%)" }} />
          {children}
        </div>
      </div>
    </div>
  );
};

const HUD: React.FC<{ step: string; next: string; n: number; of: number; blink?: boolean }> = ({ step, next, n, of, blink = true }) => {
  const t = useT();
  return (
    <>
      <div style={{ position: "absolute", left: 18, top: 62, display: "flex", alignItems: "center", gap: 8, fontFamily: FONT, fontSize: 16, fontWeight: 800, color: "#fff", background: "rgba(5,6,13,.7)", padding: "6px 12px", borderRadius: 999 }}>
        <span style={{ width: 10, height: 10, borderRadius: 5, background: CORAL, opacity: blink ? 0.4 + 0.6 * Math.abs(Math.sin(t * 4)) : 1, boxShadow: `0 0 10px ${CORAL}` }} />LIVE
      </div>
      <div style={{ position: "absolute", left: 18, right: 18, bottom: 22, display: "grid", gap: 8 }}>
        <div style={{ fontFamily: FONT, fontSize: 15, fontWeight: 700, color: CYAN }}>STEP {n} OF {of}</div>
        <div style={{ fontFamily: FONT, fontSize: 24, fontWeight: 800, color: "#fff", lineHeight: 1.15, textShadow: "0 2px 12px rgba(0,0,0,.8)" }}>{step}</div>
        <div style={{ fontFamily: FONT, fontSize: 16, fontWeight: 650, color: "#fff", background: "rgba(43,92,255,.85)", padding: "8px 12px", borderRadius: 12, justifySelf: "start" }}>Next: {next}</div>
      </div>
    </>
  );
};

const Live: React.FC = () => {
  const t = useT(); const f = useCurrentFrame();
  const s = sp(f, 0.1, { damping: 14 });
  return (
    <AbsoluteFill>
      <Atmos hue={[COBALT, CYAN]} />
      {[0, 0.7, 1.4].map((d, i) => { const p = ((t - d) / 2.1) % 1; return t > d && <div key={i} style={{ position: "absolute", left: 560, top: 540, width: 200 + p * 1400, height: 200 + p * 1400, borderRadius: "50%", transform: "translate(-50%,-50%)", border: `2px solid ${CYAN}`, opacity: (1 - p) * 0.35 }} />; })}
      <div style={{ position: "absolute", left: 340, top: 90, transform: `translateY(${(1 - s) * 500}px)`, opacity: s }}>
        <Phone from={6} rate={1.6}><HUD step="Open the cabinet door" next="Remove the old component" n={2} of={7} /><Brackets size={30} inset={14} /></Phone>
      </div>
      <div style={{ position: "absolute", left: 920, top: 300, width: 900 }}>
        <Kinetic text="Then it watches you." at={0.3} size={92} align="flex-start" glow={["you."]} />
        <Kinetic text="Through any camera." at={1.6} size={64} weight={700} color={DIM} align="flex-start" style={{ marginTop: 18 }} />
        <Kinetic text="It knows the step you're on, and what comes next." at={3.0} size={46} weight={650} color={DIM} align="flex-start" style={{ marginTop: 40, maxWidth: 820 }} />
      </div>
    </AbsoluteFill>
  );
};

const Alert: React.FC = () => {
  const t = useT();
  const hit = 1.1;
  const shake = t > hit && t < hit + 0.7 ? Math.sin(t * 90) * 14 * (1 - lin(t, hit, hit + 0.7)) : 0;
  const red = t > hit ? 0.25 + 0.2 * Math.abs(Math.sin((t - hit) * 6)) : 0;
  return (
    <AbsoluteFill>
      <Atmos hue={[CORAL, MAGENTA]} drift={2} />
      <AbsoluteFill style={{ background: `radial-gradient(70% 70% at 50% 50%, transparent 40%, ${CORAL})`, opacity: red }} />
      <div style={{ position: "absolute", left: 340, top: 90 }}>
        <Phone from={19} rate={1.3} shake={shake}>
          <HUD step="Removing the old component" next="Turn the power OFF first" n={3} of={7} />
          <div style={{ position: "absolute", inset: 0, background: CORAL, opacity: red * 0.9, mixBlendMode: "multiply" }} />
          <div style={{ position: "absolute", inset: 10 }}>{t > hit && <Ants color={CORAL} width={6} radius={36} glow />}</div>
        </Phone>
      </div>
      <div style={{ position: "absolute", left: 900, top: 330, width: 920, display: "grid", gap: 26, justifyItems: "start" }}>
        {t > hit && <Stamp at={hit} size={110} rot={-6}>STOP.</Stamp>}
        {t > hit + 0.5 && <Stamp at={hit + 0.5} size={44} rot={0} color="rgba(5,6,13,.75)" style={{ border: `2px solid ${CORAL}`, boxShadow: `0 0 40px ${CORAL}66` }}>The power is still on.</Stamp>}
        <div style={{ marginTop: 40 }}><Kinetic text="Right then. Not after." at={3.3} size={64} align="flex-start" glow={["then."]} /></div>
      </div>
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ 7. robot */

const Robot: React.FC = () => {
  const t = useT(); const f = useCurrentFrame();
  const VW = 1400, VH = 788;
  const open = ramp(t, 0, 1.2);
  const knock = 2.0, fixed = 8.4;
  const shake = t > knock && t < knock + 0.6 ? Math.sin(t * 80) * 10 * (1 - lin(t, knock, knock + 0.6)) : 0;
  const s = sp(f, 0.05, { damping: 16 });
  return (
    <AbsoluteFill>
      <Atmos hue={[CYAN, GREEN]} />
      <div style={{ position: "absolute", left: 80, top: 56 }}><Kinetic text="Not just for people." at={0.3} size={70} align="flex-start" glow={["people."]} /></div>
      <div style={{ position: "absolute", left: (W - VW) / 2, top: 200, transform: `translate(${shake}px, ${shake * 0.5}px) scale(${0.9 + 0.1 * s})`, clipPath: `circle(${open * 85}% at 50% 50%)` }}>
        <Frame w={VW} h={VH}>
          <Clip src="robot_eidos" w={VW} h={VH} rate={5} from={16} />
          <Brackets color={t > fixed ? GREEN : CYAN} />
          <div style={{ position: "absolute", right: 80, top: 20, fontFamily: MONO, fontSize: 18, color: WHITE, background: "rgba(5,6,13,.6)", padding: "6px 12px", borderRadius: 8 }}>robot arm, shown once, checks on</div>
        </Frame>
      </div>
      <div style={{ position: "absolute", left: 300, top: 640 }}>{t > knock && t < fixed && <Stamp at={knock} size={64} rot={-8}>Knocked over</Stamp>}</div>
      <div style={{ position: "absolute", right: 300, top: 640 }}>{t > 5.4 && t < fixed && <Stamp at={5.4} size={54} rot={4} color="rgba(5,6,13,.78)" style={{ border: `2px solid ${CYAN}` }}>Noticed.</Stamp>}</div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 600, display: "flex", justifyContent: "center" }}>{t > fixed && <Stamp at={fixed} size={120} rot={-3} color={GREEN}>Fixed. ✓</Stamp>}</div>
      {t > fixed && Array.from({ length: 40 }, (_, i) => { const p = lin(t, fixed, fixed + 1.4); const a = rnd(i, 9) * Math.PI * 2; return <div key={i} style={{ position: "absolute", left: W / 2 + Math.cos(a) * p * (200 + rnd(i) * 500), top: 650 + Math.sin(a) * p * (200 + rnd(i) * 500) + p * p * 300, width: 8 + rnd(i, 2) * 10, height: 8 + rnd(i, 2) * 10, borderRadius: 3, background: [GREEN, CYAN, WHITE][i % 3], opacity: 1 - p, transform: `rotate(${t * 400 * rnd(i, 3)}deg)` }} />; })}
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ 8. meta */

const MODELS: [string, string][] = [["Muse Spark", "watches"], ["Muse Wonder", "compiles"], ["SAM 3.1", "outlines"], ["Muse Image", "draws"], ["Muse Spark Open", "open weights"]];
const Meta: React.FC = () => {
  const t = useT(); const f = useCurrentFrame();
  const cx = W / 2, cy = 600, R = 330;
  const rot = t * 10;
  return (
    <AbsoluteFill>
      <Atmos hue={[COBALT, MAGENTA]} />
      <div style={{ position: "absolute", left: 0, right: 0, top: 70, display: "flex", justifyContent: "center" }}><Kinetic text="Built on Meta's AI models." at={0.2} size={78} glow={["Meta's"]} /></div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 170, display: "flex", justifyContent: "center" }}><Kinetic text="Meta Global AI Hackathon 2026" at={1.2} size={30} weight={700} color={DIM} /></div>
      <svg width={W} height={H} style={{ position: "absolute", inset: 0 }}>
        {MODELS.map((_, i) => { const a = ((rot + i * 72) * Math.PI) / 180; const p = ramp(t, 0.8 + i * 0.2, 1.5 + i * 0.2); return <line key={i} x1={cx} y1={cy} x2={cx + Math.cos(a) * R * p} y2={cy + Math.sin(a) * R * 0.55 * p} stroke={CYAN} strokeWidth={2} strokeDasharray="4 10" strokeDashoffset={-t * 40} opacity={0.6} />; })}
        <circle cx={cx} cy={cy} r={70 + 8 * Math.sin(t * 3)} fill="none" stroke={CYAN} strokeWidth={2} opacity={0.5} />
      </svg>
      <div style={{ position: "absolute", left: cx - 90, top: cy - 90, width: 180, height: 180, borderRadius: 90, background: `radial-gradient(circle at 40% 35%, #4f7bff, ${COBALT} 60%, #0b1a6b)`, boxShadow: `0 0 80px ${COBALT}, 0 0 160px ${COBALT}66`, display: "grid", placeItems: "center", fontFamily: FONT, fontWeight: 900, fontSize: 40, letterSpacing: "0.06em", color: "#fff", transform: `scale(${sp(f, 0.3, { damping: 10 })})` }}>EIDOS</div>
      {MODELS.map(([name, job], i) => {
        const a = ((rot + i * 72) * Math.PI) / 180; const s = sp(f, 0.8 + i * 0.2, { damping: 11 });
        const x = cx + Math.cos(a) * R, y = cy + Math.sin(a) * R * 0.55;
        const front = Math.sin(a) > -0.2;
        return <div key={name} style={{ position: "absolute", left: x - 130, top: y - 60, width: 260, display: "grid", justifyItems: "center", gap: 6, transform: `scale(${s * (front ? 1 : 0.85)})`, opacity: s * (front ? 1 : 0.7), zIndex: front ? 2 : 0 }}>
          <div style={{ width: 64, height: 64, borderRadius: 32, background: `radial-gradient(circle at 40% 35%, #fff, ${[CYAN, MAGENTA, GREEN, "#ffb84d", CYAN][i]} 50%, transparent 72%)`, boxShadow: `0 0 40px ${[CYAN, MAGENTA, GREEN, "#ffb84d", CYAN][i]}` }} />
          <div style={{ fontFamily: FONT, fontSize: 30, fontWeight: 900, color: WHITE, textAlign: "center", lineHeight: 1 }}>{name}</div>
          <div style={{ fontFamily: FONT, fontSize: 20, fontWeight: 650, color: DIM }}>{job}</div>
        </div>;
      })}
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ 9. close */

const Close: React.FC = () => {
  const t = useT();
  const end = timing.durations[8];
  return (
    <AbsoluteFill>
      <Atmos />
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        <Logo at={0.2} size={200} sweep={4.6} />
        <div style={{ marginTop: 36 }}><Kinetic text="Maruthi Kunchala" at={1.2} size={44} weight={800} /></div>
        <div style={{ marginTop: 6 }}><Kinetic text="Team PULSE - Parallax" at={1.8} size={30} weight={700} color={DIM} /></div>
        <div style={{ marginTop: 50 }}><Kinetic text="Show it once." at={4.2} size={110} step={0.14} glow={["once."]} /></div>
      </AbsoluteFill>
      <AbsoluteFill style={{ background: BG, opacity: ramp(t, end - 1.6, end - 0.2) }} />
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ assembly */

const SCENES: React.FC[] = [Open, Montage, Name, Learn, Live, Alert, Robot, Meta, Close];
const frames = timing.durations.map((d) => Math.round(d * FPS));
const TR = Math.round(timing.tr * FPS);
export const familyFrames = frames.reduce((a, b) => a + b, 0) - TR * (frames.length - 1);
const starts = frames.map((_, i) => frames.slice(0, i).reduce((a, b) => a + b, 0) - TR * i);
const TRANS = [fade(), fade(), slide({ direction: "from-bottom" }), wipe({ direction: "from-left" }), fade(), iris({ width: W, height: H }), clockWipe({ width: W, height: H }), fade()];
const LEAD = 0.5;

export const Family: React.FC = () => (
  <AbsoluteFill style={{ background: BG }}>
    <TransitionSeries>
      {SCENES.flatMap((C, i) => {
        const id = timing.ids[i];
        const items = [
          <TransitionSeries.Sequence key={id} durationInFrames={frames[i]}><C /><Caption id={id} at={LEAD} /></TransitionSeries.Sequence>,
        ];
        if (i < SCENES.length - 1) items.push(<TransitionSeries.Transition key={id + "-t"} presentation={TRANS[i] as any} timing={linearTiming({ durationInFrames: TR })} />);
        return items;
      })}
    </TransitionSeries>
    {timing.ids.map((id, i) => (
      <Sequence key={id} from={starts[i] + Math.round(LEAD * FPS)} durationInFrames={Math.round(VO(id).seconds * FPS) + 10}>
        <Audio src={staticFile(`vo_family/${id}.wav`)} />
      </Sequence>
    ))}
    <Audio src={staticFile("music/bed_family.mp3")} volume={(f: number) => 0.55 * interpolate(f, [familyFrames - 70, familyFrames - 5], [1, 0], clamp)} />
  </AbsoluteFill>
);
