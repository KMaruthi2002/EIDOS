// EIDOS launch video, version 2: one compiler, three worlds (real world live, screens, robots).
// the app in clean browser windows, springy motion graphics.
import React from "react";
import { AbsoluteFill, Img, interpolate, Sequence, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { Audio, Video } from "@remotion/media";
import { TransitionSeries, linearTiming } from "@remotion/transitions";
import { slide } from "@remotion/transitions/slide";
import { fade } from "@remotion/transitions/fade";
import { wipe } from "@remotion/transitions/wipe";
import { FONT, MONO, ease } from "./ui";
import timeline from "./timeline5.json";
import world from "./world_data.json";


const FPS = 30;
const INK = "#0d0f1a", SUB = "#3a3f5c", MUTE = "#6b6f86";
const BLUE = "#3b5bff", VIOLET = "#8b5cf6", CORAL = "#ff7a59", CYAN = "#20c4ff", GREEN = "#12b886", RED = "#f03e5e";
const GRAD = `linear-gradient(120deg, ${BLUE}, ${VIOLET} 55%, ${CORAL})`;
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

const useT = () => useCurrentFrame() / FPS;
const ramp = (t: number, a: number, b: number) => interpolate(t, [a, b], [0, 1], { ...clamp, easing: ease });
const useSpring = (at: number, cfg: { damping?: number; mass?: number; stiffness?: number } = {}) => {
  const f = useCurrentFrame();
  return spring({ frame: f - at * FPS, fps: FPS, config: { damping: 14, ...cfg } });
};
const VO = (id: string) => timeline.find((s) => s.id === id)!;

/* ------------------------------------------------------------------ backdrop */

const PALETTES: Record<string, string[]> = {
  a: [BLUE, VIOLET, CORAL, CYAN],
  b: [VIOLET, "#ff5fa2", CYAN, BLUE],
  c: [CYAN, BLUE, "#7cf2c7", VIOLET],
  d: [CORAL, "#ffc24b", VIOLET, BLUE],
};
const Mesh: React.FC<{ p?: keyof typeof PALETTES }> = ({ p = "a" }) => {
  const f = useCurrentFrame();
  const t = f / FPS;
  const spots: [number, number, number, number][] = [[18, 28, 900, 0], [78, 22, 820, 1.7], [66, 82, 780, 3.1], [14, 84, 720, 4.4]];
  return (
    <AbsoluteFill style={{ background: "#f7f5ff", overflow: "hidden" }}>
      {spots.map(([x, y, r, ph], i) => (
        <div key={i} style={{ position: "absolute", width: r, height: r, borderRadius: "50%", background: PALETTES[p][i], filter: "blur(150px)", opacity: 0.5,
          left: `calc(${x + Math.sin(t * 0.45 + ph) * 9}% - ${r / 2}px)`, top: `calc(${y + Math.cos(t * 0.38 + ph) * 9}% - ${r / 2}px)` }} />
      ))}
      <AbsoluteFill style={{ backgroundImage: "radial-gradient(rgba(20,20,60,.10) 1.4px, transparent 1.6px)", backgroundSize: "34px 34px",
        maskImage: "radial-gradient(70% 60% at 50% 50%, transparent 40%, #000)", WebkitMaskImage: "radial-gradient(70% 60% at 50% 50%, transparent 40%, #000)" }} />
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ type */

const Words: React.FC<{ text: string; at: number; step?: number; style?: React.CSSProperties; color?: (w: string, i: number) => string | undefined }> = ({ text, at, step = 0.08, style, color }) => {
  const t = useT();
  return (
    <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", columnGap: "0.26em", ...style }}>
      {text.split(" ").map((w, i) => {
        const p = ramp(t, at + i * step, at + i * step + 0.6);
        const c = color?.(w, i);
        return (
          <span key={i} style={{ display: "inline-block", overflow: "hidden", padding: "0.04em 0.02em 0.14em" }}>
            <span style={{ display: "inline-block", transform: `translateY(${(1 - p) * 110}%) rotate(${(1 - p) * 6}deg)`,
              ...(c === "grad" ? { background: GRAD, WebkitBackgroundClip: "text", color: "transparent" } : c ? { color: c } : {}) }}>{w}</span>
          </span>
        );
      })}
    </div>
  );
};

const Headline: React.FC<{ text: string; at?: number; size?: number; top?: number; grad?: string[]; max?: number }> = ({ text, at = 0.1, size = 92, top = 64, grad = [], max = 1700 }) => (
  <div style={{ position: "absolute", left: 0, right: 0, top, display: "flex", justifyContent: "center", fontFamily: FONT, fontWeight: 860, fontSize: size,
    letterSpacing: "-0.035em", lineHeight: 1.02, color: INK, textAlign: "center" }}>
    <div style={{ maxWidth: max }}>
      <Words text={text} at={at} color={(w) => (grad.includes(w.replace(/[.,]/g, "")) ? "grad" : undefined)} />
    </div>
  </div>
);

const Pill: React.FC<{ at: number; children: React.ReactNode; tone?: "ok" | "bad" | "plain" | "brand"; size?: number; style?: React.CSSProperties }> = ({ at, children, tone = "plain", size = 28, style }) => {
  const s = useSpring(at, { damping: 11 });
  const bg = tone === "ok" ? `linear-gradient(135deg, ${GREEN}, #0ca678)` : tone === "bad" ? `linear-gradient(135deg, ${RED}, #d6336c)` : tone === "brand" ? `linear-gradient(135deg, ${BLUE}, ${VIOLET})` : "rgba(255,255,255,.85)";
  return (
    <div style={{ display: "inline-flex", alignItems: "center", gap: 12, fontFamily: FONT, fontSize: size, fontWeight: 760, padding: `${size * 0.45}px ${size * 0.8}px`, borderRadius: 999,
      background: bg, color: tone === "plain" ? INK : "#fff", whiteSpace: "nowrap", transform: `scale(${s})`, opacity: Math.min(1, s * 2),
      boxShadow: "0 18px 40px -16px rgba(40,30,120,.45)", ...style }}>{children}</div>
  );
};

/* ------------------------------------------------------------------ browser window */

const Browser: React.FC<{ w: number; h: number; url: string; children: React.ReactNode; style?: React.CSSProperties; dark?: boolean }> = ({ w, h, url, children, style, dark }) => (
  <div style={{ width: w, borderRadius: 22, overflow: "hidden", background: dark ? "#1c1c24" : "#fff",
    boxShadow: "0 60px 120px -40px rgba(40,20,120,.55), 0 0 0 1px rgba(20,20,60,.08)", ...style }}>
    <div style={{ height: 44, display: "flex", alignItems: "center", gap: 9, padding: "0 18px", background: dark ? "#2a2a34" : "#f3f2f8", borderBottom: `1px solid ${dark ? "#3a3a48" : "#e4e2ee"}` }}>
      {["#ff5f57", "#febc2e", "#28c840"].map((c) => <span key={c} style={{ width: 12, height: 12, borderRadius: 6, background: c }} />)}
      <div style={{ marginLeft: 16, flex: 1, maxWidth: 420, height: 26, borderRadius: 13, background: dark ? "#1c1c24" : "#fff", fontFamily: FONT, fontSize: 14,
        color: MUTE, display: "flex", alignItems: "center", padding: "0 12px", overflow: "hidden", whiteSpace: "nowrap" }}>{url}</div>
    </div>
    <div style={{ position: "relative", width: w, height: h, overflow: "hidden" }}>{children}</div>
  </div>
);

const Clip: React.FC<{ src: string; w: number; h: number; rate?: number; from?: number }> = ({ src, w, h, rate = 1, from = 0 }) => (
  <Video src={staticFile(`clips/${src}.mp4`)} muted playbackRate={rate} trimBefore={Math.round(from * FPS)} style={{ width: w, height: h, display: "block" }} />
);

/* ------------------------------------------------------------------ caption */

const Caption: React.FC<{ id: string; at: number }> = ({ id, at }) => {
  const t = useT() - at;
  const vo = VO(id);
  const parts = (vo.text.replace(/Eye-doss/g, "EIDOS").replace(/(\d)\.(\d)/g, "$1\u00a7$2").match(/[^.!?]+[.!?]+/g) || [vo.text]).map((x) => x.replace(/\u00a7/g, "."));
  const total = parts.reduce((a, p) => a + p.length, 0);
  let acc = 0, cur = "";
  for (const p of parts) { const s = (acc / total) * vo.seconds, e = ((acc + p.length) / total) * vo.seconds; if (t >= s - 0.05 && t < e + 0.25) cur = p.trim(); acc += p.length; }
  if (t > vo.seconds + 0.4 || t < 0) cur = "";
  return (
    <div style={{ position: "absolute", left: 0, right: 0, bottom: 34, display: "flex", justifyContent: "center", pointerEvents: "none" }}>
      {cur && <div style={{ maxWidth: 1400, fontFamily: FONT, fontSize: 28, fontWeight: 560, lineHeight: 1.3, color: INK, textAlign: "center",
        padding: "10px 22px", borderRadius: 16, background: "rgba(255,255,255,.78)", backdropFilter: "blur(10px)", boxShadow: "0 10px 30px -18px rgba(30,20,90,.45)" }}>{cur}</div>}
    </div>
  );
};

const Ants: React.FC<{ color: string; draw?: number; width?: number; radius?: number }> = ({ color, draw = 1, width = 4, radius = 18 }) => {
  const t = useT();
  return (
    <svg width="100%" height="100%" style={{ position: "absolute", inset: 0, overflow: "visible" }}>
      <rect x={0} y={0} width="100%" height="100%" rx={radius} fill="none" stroke={color} strokeWidth={width} pathLength={100}
        strokeDasharray={draw < 1 ? `${100 * draw} 100` : "1.4 0.9"} strokeDashoffset={draw < 1 ? 0 : -t * 3} />
    </svg>
  );
};

const Roll: React.FC<{ value: number; at: number; dur?: number }> = ({ value, at, dur = 1.3 }) => {
  const t = useT();
  return <>{Math.round(value * ramp(t, at, at + dur))}</>;
};

const Bind: React.FC<{ text: string }> = ({ text }) => (
  <>{text.split(/(\{\w+\})/).map((x, j) => /^\{/.test(x) ? <span key={j} style={{ color: BLUE }}>{x}</span> : x)}</>
);

/* ------------------------------------------------------------------ 1. hook */

const Hook: React.FC = () => {
  const t = useT();
  const fr = useCurrentFrame();
  const gather = ramp(t, 8.6, 10.2);
  return (
    <AbsoluteFill>
      <Mesh p="a" />
      <AbsoluteFill style={{ perspective: 1600 }}>
        {Array.from({ length: 12 }, (_, i) => {
          const col = i % 4, row = Math.floor(i / 4);
          const x0 = 140 + col * 430 + (row % 2) * 120, y0 = 120 + row * 300;
          const s = spring({ frame: fr - i * 3, fps: FPS, config: { damping: 15 } });
          const drift = Math.sin(t * 0.8 + i) * 14;
          const x = x0 + (960 - 190 - x0) * gather, y = y0 + drift + (540 - 110 - y0) * gather;
          return (
            <div key={i} style={{ position: "absolute", left: x, top: y, width: 380, height: 236, borderRadius: 18, overflow: "hidden", background: "#fff",
              transform: `translateZ(${(1 - s) * -600}px) rotateY(${(col - 1.5) * 8 * (1 - gather)}deg) rotate(${(i % 3 - 1) * 3 * (1 - gather) + gather * (i - 6) * 2}deg) scale(${(0.6 + 0.4 * s) * (1 - gather * 0.25)})`,
              opacity: s * (1 - ramp(t, 10.8, 11.6)), boxShadow: "0 30px 60px -24px rgba(30,20,90,.5)" }}>
              <Img src={staticFile(`thumbs/w${i}.jpg`)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
              <div style={{ position: "absolute", left: 12, bottom: 12, width: 44, height: 44, borderRadius: 22, background: "rgba(13,15,26,.75)", display: "grid", placeItems: "center" }}>
                <svg width="18" height="18" viewBox="0 0 18 18"><path d="M5 3l10 6-10 6z" fill="#fff" /></svg>
              </div>
            </div>
          );
        })}
      </AbsoluteFill>
      {t > 4.4 && t < 8.4 && (
        <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", fontFamily: FONT, color: INK, opacity: 1 - ramp(t, 7.8, 8.3),
          background: `rgba(247,245,255,${0.55 * ramp(t, 4.4, 4.8)})`, backdropFilter: `blur(${12 * ramp(t, 4.4, 4.8)}px)` }}>
          <Words text="Billions of hours." at={4.5} step={0.12} style={{ fontSize: 190, fontWeight: 900, letterSpacing: "-0.05em", lineHeight: 1.05 }} color={(w) => (w === "Billions" ? "grad" : undefined)} />
          <div style={{ fontSize: 46, fontWeight: 700, color: SUB, marginTop: 14, opacity: ramp(t, 5.1, 5.6) }}>of people showing how things get done</div>
        </AbsoluteFill>
      )}
      {t > 10.4 && <Headline text="AI still can't learn a skill from one." at={10.5} size={104} top={380} grad={["learn"]} max={1500} />}
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ 2. name */

const Name: React.FC = () => {
  const t = useT();
  const f = useCurrentFrame();
  return (
    <AbsoluteFill>
      <Mesh p="b" />
      {Array.from({ length: 14 }, (_, i) => {
        const a = (i / 14) * Math.PI * 2, r = 520 + (i % 3) * 90, p = ramp(t, 0.3 + i * 0.03, 1.4 + i * 0.03);
        const x = 960 + Math.cos(a + t * 0.25) * r * p, y = 470 + Math.sin(a + t * 0.25) * r * 0.55 * p, s = 26 + (i % 4) * 12;
        return <div key={i} style={{ position: "absolute", left: x - s / 2, top: y - s / 2, width: s, height: s, transform: `rotate(${t * 40 + i * 20}deg)`, opacity: p * 0.8 }}>
          <Ants color={[BLUE, VIOLET, CORAL, CYAN][i % 4]} width={3} radius={4} />
        </div>;
      })}
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        <div style={{ position: "relative", padding: "26px 64px", marginTop: -60 }}>
          <Ants color={BLUE} draw={ramp(t, 0.2, 1.3)} width={5} radius={26} />
          <div style={{ display: "flex", fontFamily: FONT, fontSize: 230, fontWeight: 900, letterSpacing: "0.06em", fontVariationSettings: '"wdth" 125', color: INK }}>
            {"EIDOS".split("").map((l, i) => {
              const s = spring({ frame: f - (0.4 + i * 0.09) * FPS, fps: FPS, config: { damping: 9, mass: 0.7 } });
              return <span key={i} style={{ display: "inline-block", transform: `translateY(${(1 - s) * 140}px) rotate(${(1 - s) * (i % 2 ? 18 : -18)}deg) scale(${0.4 + 0.6 * s})`, opacity: Math.min(1, s * 1.5) }}>{l}</span>;
            })}
          </div>
        </div>
        <div style={{ marginTop: 40, maxWidth: 1500 }}>
          <Words text="Show it once. It compiles the video into a program that checks the work." at={1.6} step={0.06} style={{ fontFamily: FONT, fontSize: 52, fontWeight: 700, color: SUB }}
            color={(w) => (w === "program" || w.startsWith("checks") ? "grad" : undefined)} />
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ 3. learn */

const BOXES4: number[][] = ((world as any).boxes4 || []);
const Learn: React.FC = () => {
  const t = useT();
  const fr = useCurrentFrame();
  const W = 860, H = Math.round(860 * 360 / 640);
  const notes = world.notes.filter((_, i) => i % 3 === 0).slice(0, 16);
  const compiled = ramp(t, 7.2, 8.0);
  const step4 = world.steps.find((s) => s.id === 4)!;
  return (
    <AbsoluteFill>
      <Mesh p="c" />
      <Headline text="It watches, then compiles a program." at={0.05} size={72} top={52} grad={["program."]} />
      <div style={{ position: "absolute", left: 90, top: 190 }}>
        <Browser w={W} h={H} url={t < 12.4 ? "kitchen.mp4 (a cooking video, 7 min)" : "evidence: the frame where step 4 was finished"}>
          <Clip src="tomato_demo" w={W} h={H} />
          {t > 12.4 && (
            <div style={{ position: "absolute", inset: 0, opacity: ramp(t, 12.4, 12.8) }}>
              <Img src={staticFile("world/tomato/evidence/step4_end.jpg")} style={{ width: "100%", height: "100%" }} />
              {BOXES4.map((b, i) => (
                <div key={i} style={{ position: "absolute", left: `${b[0] * 100}%`, top: `${b[1] * 100}%`, width: `${(b[2] - b[0]) * 100}%`, height: `${(b[3] - b[1]) * 100}%` }}>
                  <Ants color={CYAN} width={4} radius={5} draw={ramp(t, 12.9 + i * 0.25, 13.6 + i * 0.25)} />
                </div>
              ))}
            </div>
          )}
        </Browser>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 12, marginTop: 22, width: W }}>
          {t > 1.0 && <Pill at={1.0} tone="brand" size={24}>Muse Spark watches, 8 s at a time</Pill>}
          {t > 7.4 && <Pill at={7.4} tone="brand" size={24}>Muse Wonder compiles</Pill>}
          {t > 13.0 && <Pill at={13.0} tone="plain" size={24}>SAM 3.1 outlines it</Pill>}
        </div>
      </div>
      {/* notes stream, then the program */}
      <div style={{ position: "absolute", left: 1010, top: 196, width: 830, height: 820, overflow: "hidden" }}>
        <div style={{ opacity: 1 - compiled, display: "grid", gap: 8, transform: `translateY(${-Math.max(0, t - 2.2) * 34}px)` }}>
          {notes.map((n, i) => {
            const at = 0.8 + i * 0.4;
            const s = spring({ frame: fr - at * FPS, fps: FPS, config: { damping: 14 } });
            return (
              <div key={i} style={{ display: "flex", gap: 14, alignItems: "baseline", padding: "10px 16px", borderRadius: 12, background: "rgba(255,255,255,.85)",
                transform: `translateX(${(1 - s) * 80}px)`, opacity: Math.min(1, s * 1.5) }}>
                <span style={{ fontFamily: MONO, fontSize: 18, color: MUTE, width: 64 }}>{`${Math.floor(n.t / 60)}:${String(Math.round(n.t % 60)).padStart(2, "0")}`}</span>
                <span style={{ fontFamily: FONT, fontSize: 24, fontWeight: 600, color: INK }}>{n.a}</span>
              </div>
            );
          })}
        </div>
        <div style={{ position: "absolute", inset: 0, display: "grid", gap: 9, alignContent: "start", opacity: compiled }}>
          <div style={{ fontFamily: FONT, fontSize: 30, fontWeight: 850, color: INK, marginBottom: 4 }}>{world.title}</div>
          {world.steps.map((s, i) => {
            const at = 7.6 + i * 0.32;
            const sp = spring({ frame: fr - at * FPS, fps: FPS, config: { damping: 13 } });
            return (
              <div key={s.id} style={{ display: "flex", alignItems: "center", gap: 14, padding: "11px 16px", borderRadius: 14, background: "rgba(255,255,255,.92)",
                boxShadow: "0 12px 26px -18px rgba(30,20,90,.5)", transform: `translateX(${(1 - sp) * 120}px)`, opacity: Math.min(1, sp * 1.4) }}>
                <span style={{ width: 34, height: 34, borderRadius: 17, background: "#eceaff", color: VIOLET, display: "grid", placeItems: "center", fontFamily: FONT, fontWeight: 850, fontSize: 18 }}>{s.id}</span>
                <span style={{ fontFamily: FONT, fontSize: 22, fontWeight: 650, color: INK, flex: 1 }}><Bind text={s.do} /></span>
                {s.needs.length > 0 && <span style={{ fontFamily: MONO, fontSize: 15, color: MUTE, whiteSpace: "nowrap" }}>needs {s.needs.join(", ")}</span>}
              </div>
            );
          })}
        </div>
      </div>
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ 4. show it again */

const Again: React.FC = () => {
  const t = useT();
  const fr = useCurrentFrame();
  const changed = new Map(world.changes.map((c) => [c.step, c]));
  return (
    <AbsoluteFill>
      <Mesh p="d" />
      <Headline text="Show it again. It learns what's essential." at={0.05} size={72} top={52} grad={["essential."]} max={1800} />
      <div style={{ position: "absolute", top: 190, left: 0, right: 0, display: "flex", justifyContent: "center", gap: 40 }}>
        {[["w0", "First demonstration"], ["again2", "Second demonstration, another cook"]].map(([src, label], i) => {
          const s = useSpring(0.3 + i * 0.4, { damping: 14 });
          return (
            <div key={src} style={{ display: "grid", gap: 10, justifyItems: "center", transform: `translateY(${(1 - s) * 120}px)`, opacity: Math.min(1, s * 1.5) }}>
              <div style={{ width: 520, height: 292, borderRadius: 18, overflow: "hidden", boxShadow: "0 30px 60px -28px rgba(30,20,90,.6)" }}>
                <Img src={staticFile(`thumbs/${src}.jpg`)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
              </div>
              <div style={{ fontFamily: FONT, fontSize: 26, fontWeight: 760, color: INK }}>{label}</div>
            </div>
          );
        })}
      </div>
      <div style={{ position: "absolute", top: 560, left: 260, right: 260, display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px 24px" }}>
        {world.steps.map((s, i) => {
          const c = changed.get(s.id);
          const hit = c ? ramp(t, 4.0, 4.6) : 0;
          const wasOpt = s.opt;
          return (
            <div key={s.id} style={{ display: "flex", alignItems: "center", gap: 12, padding: "9px 14px", borderRadius: 12, background: "rgba(255,255,255,.9)",
              opacity: (c || wasOpt ? 1 : 0.88) * ramp(t, 1.2 + i * 0.08, 1.6 + i * 0.08), outline: c ? `3px solid rgba(240,62,94,${hit})` : "none" }}>
              <span style={{ fontFamily: FONT, fontWeight: 850, fontSize: 17, color: VIOLET, width: 22 }}>{s.id}</span>
              <span style={{ fontFamily: FONT, fontSize: 20, fontWeight: 620, color: INK, flex: 1, textDecoration: c && hit > 0.5 ? "line-through" : "none", textDecorationColor: RED, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}><Bind text={s.do} /></span>
              {(wasOpt || (c && hit > 0.4)) && <span style={{ fontFamily: FONT, fontSize: 16, fontWeight: 760, color: "#fff", background: c ? RED : MUTE, borderRadius: 999, padding: "3px 10px" }}>optional</span>}
            </div>
          );
        })}
      </div>
      {t > 4.8 && world.changes[0] && <div style={{ position: "absolute", left: 0, right: 0, top: 900, display: "flex", justifyContent: "center" }}>
        <Pill at={4.8} tone="brand" size={26}>Step {world.changes[0].step}: {world.changes[0].why}, so it is a habit, not a rule</Pill></div>}
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ 5-7. live */

const Studio: React.FC<{ src: string; from?: number; rate?: number; zoom?: [number, number, number, number, number]; head: string; grad: string[]; pal: keyof typeof PALETTES; pills?: [number, string, "ok" | "bad" | "plain" | "brand"][] }> = ({ src, from = 0, rate = 1, zoom, head, grad, pal, pills = [] }) => {
  const t = useT();
  const W = 1240, H = Math.round(1240 * 900 / 1440);
  const s = useSpring(0.1, { damping: 16 });
  // zoom: [start, end, scale, originX%, originY%]
  const z = zoom ? 1 + (zoom[2] - 1) * (ramp(t, zoom[0], zoom[0] + 0.8) - ramp(t, zoom[1], zoom[1] + 0.8)) : 1;
  return (
    <AbsoluteFill>
      <Mesh p={pal} />
      <Headline text={head} at={0.05} size={68} top={40} grad={grad} max={1800} />
      <div style={{ position: "absolute", left: (1920 - W) / 2, top: 140, transform: `translateY(${(1 - s) * 300}px)` }}>
        <Browser w={W} h={H} url="localhost:8000/world  EIDOS Studio, Real world">
          <div style={{ width: W, height: H, transform: `scale(${z})`, transformOrigin: zoom ? `${zoom[3]}% ${zoom[4]}%` : "center" }}>
            <Clip src={src} w={W} h={H} rate={rate} from={from} />
          </div>
        </Browser>
      </div>
      <div style={{ position: "absolute", right: 70, top: 160, display: "grid", gap: 12, justifyItems: "end" }}>
        {pills.map(([at, p, tone]) => t > at ? <Pill key={p} at={at} tone={tone} size={24}>{p}</Pill> : null)}
      </div>
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ 8. anything */

const SKILLS: [string, string, string, number][] = [["tomato", "Tomato salad", "CaptainCook4D", 4], ["gpu", "Install a graphics card", "HoloAssist", 4], ["ram", "Install RAM", "HoloAssist", 2], ["cabinet", "Replace a cabinet part", "HoloAssist", 3]];
const Anything: React.FC = () => {
  const fr = useCurrentFrame();
  return (
    <AbsoluteFill style={{ perspective: 2200 }}>
      <Mesh p="a" />
      <Headline text="One video in. A checkable skill out." at={0.05} size={76} top={52} grad={["checkable"]} />
      <div style={{ position: "absolute", top: 210, left: 0, right: 0, display: "flex", justifyContent: "center", gap: 30 }}>
        {SKILLS.map(([k, name, src, ev], i) => {
          const s = spring({ frame: fr - (0.4 + i * 0.45) * FPS, fps: FPS, config: { damping: 13 } });
          const prog = (SKILLDATA as any)[k];
          const step = prog.steps.find((x: any) => x.id === ev) || prog.steps[0];
          const boxes = step.evidence?.boxes || [];
          return (
            <div key={k} style={{ width: 410, borderRadius: 26, background: "rgba(255,255,255,.92)", padding: 18, boxShadow: "0 40px 80px -40px rgba(40,20,120,.6)",
              transform: `translateY(${(1 - s) * 220}px) rotate(${(1 - s) * (i - 1.5) * 8}deg)`, opacity: Math.min(1, s * 1.6), display: "grid", gap: 12, alignContent: "start" }}>
              <div style={{ position: "relative", width: 374, height: 210, borderRadius: 14, overflow: "hidden" }}>
                <Img src={staticFile(`world/${k}/evidence/${step.evidence.end}`)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                {boxes.map((b: number[], j: number) => <div key={j} style={{ position: "absolute", left: `${b[0] * 100}%`, top: `${b[1] * 100}%`, width: `${(b[2] - b[0]) * 100}%`, height: `${(b[3] - b[1]) * 100}%` }}><Ants color={CYAN} width={3} radius={4} /></div>)}
              </div>
              <div style={{ fontFamily: FONT, fontSize: 30, fontWeight: 850, color: INK }}>{name}</div>
              <div style={{ fontFamily: FONT, fontSize: 19, fontWeight: 600, color: MUTE }}>{prog.steps.length} steps, from one video ({src})</div>
              {prog.steps.slice(0, 5).map((x: any) => <div key={x.id} style={{ fontFamily: FONT, fontSize: 18, color: SUB, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{x.id}. {x.do.replace(/\{(\w+)\}/g, (_: string, n: string) => prog.inputs?.[n] ?? n)}</div>)}
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
import tomatoP from "../public/world/tomato/program.json";
import gpuP from "../public/world/gpu/program.json";
import ramP from "../public/world/ram/program.json";
import cabinetP from "../public/world/cabinet/program.json";
const SKILLDATA = { tomato: tomatoP, gpu: gpuP, ram: ramP, cabinet: cabinetP };

/* ------------------------------------------------------------------ 9. results */

const Results: React.FC = () => {
  const t = useT();
  const fr = useCurrentFrame();
  const R = (world as any).results;
  const beats: { at: number; big: React.ReactNode; line: string; pills: [string, "ok" | "bad" | "plain" | "brand"][] }[] = R.beats.map((b: any) => ({
    at: b.at, line: b.line, pills: b.pills,
    big: b.text != null ? <>{b.text}</> : b.pct != null ? <><Roll value={b.pct} at={b.at + 0.1} />%</> : <><Roll value={b.n} at={b.at + 0.1} />/{b.d}</>,
  }));
  return (
    <AbsoluteFill>
      <Mesh p="c" />
      <div style={{ position: "absolute", top: 70, left: 0, right: 0, textAlign: "center", fontFamily: FONT, fontSize: 40, fontWeight: 700, color: SUB, opacity: ramp(t, 0.1, 0.5) }}>
        {R.head}
      </div>
      {beats.map((b, i) => {
        const nx = beats[i + 1];
        if (!(t >= b.at && (!nx || t < nx.at))) return null;
        const pop = spring({ frame: fr - b.at * FPS, fps: FPS, config: { damping: 12 } });
        return (
          <AbsoluteFill key={i} style={{ alignItems: "center", justifyContent: "center", fontFamily: FONT, textAlign: "center" }}>
            <div style={{ fontSize: 230, fontWeight: 900, letterSpacing: "-0.06em", lineHeight: 1.05, fontVariantNumeric: "tabular-nums", padding: "0 30px",
              background: GRAD, WebkitBackgroundClip: "text", color: "transparent", transform: `scale(${0.7 + 0.3 * pop})` }}>{b.big}</div>
            <div style={{ fontSize: 48, fontWeight: 760, color: INK, marginTop: -6, maxWidth: 1500, opacity: ramp(t, b.at + 0.4, b.at + 0.9) }}>{b.line}</div>
            <div style={{ display: "flex", gap: 16, marginTop: 34, flexWrap: "wrap", justifyContent: "center", maxWidth: 1600 }}>
              {b.pills.map(([p, tone], j) => <Pill key={p} at={b.at + 1.2 + j * 0.3} tone={tone}>{p}</Pill>)}
            </div>
          </AbsoluteFill>
        );
      })}
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ 10. screens and robots */

const Screens: React.FC = () => {
  const t = useT();
  const fr = useCurrentFrame();
  const W = 560, H = Math.round(560 * 760 / 1200);
  const items: [string, string, number, string, string][] = [
    ["other_eidos", "A redesigned app", 1.6, "60/60 everyday tasks", "Screens"],
    ["renamed_live", "Every control renamed", 5.6, "32/32 with Muse Spark", "Screens"],
    ["robot_eidos", "A knocked-over stack", 1.6, "Noticed and rebuilt", "Robots"],
  ];
  return (
    <AbsoluteFill style={{ perspective: 2000 }}>
      <Mesh p="b" />
      <Headline text="The same compiler, on screens and robots." at={0.05} size={72} top={56} grad={["screens", "robots."]} max={1800} />
      <div style={{ position: "absolute", top: 230, left: 0, right: 0, display: "flex", justifyContent: "center", gap: 36 }}>
        {items.map(([src, label, rate, res, world_], i) => {
          const at = [0.6, 4.0, 8.4][i];
          const s = spring({ frame: fr - at * FPS, fps: FPS, config: { damping: 13 } });
          const h = src === "robot_eidos" ? Math.round(W * 9 / 16) : H;
          return (
            <div key={src} style={{ display: "grid", gap: 12, justifyItems: "center", transform: `translateY(${(1 - s) * 200}px) rotateX(${(1 - s) * 25}deg)`, opacity: Math.min(1, s * 1.5) }}>
              <div style={{ fontFamily: MONO, fontSize: 20, color: VIOLET }}>{world_}</div>
              <Browser w={W} h={h} url={label}><Clip src={src} w={W} h={h} rate={rate} /></Browser>
              <div style={{ height: 70 }}>{t > at + 1.6 && <Pill at={at + 1.6} tone="ok" size={26}>{res}</Pill>}</div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ 11-12. meta, close */

const MODELS: [string, string, string[]][] = [
  ["Muse Spark", "Watches the video and the live camera, and checks each step", [BLUE, VIOLET]],
  ["Muse Wonder", "Compiles what it saw into a program", [VIOLET, "#ff5fa2"]],
  ["SAM 3.1", "Outlines what each contract is about", [CYAN, BLUE]],
  ["Muse Image", "Draws a card for every skill", [CORAL, "#ffc24b"]],
  ["Muse Spark Open", "Can watch live on open weights", ["#20c997", CYAN]],
];
const Meta: React.FC = () => {
  const t = useT();
  return (
    <AbsoluteFill>
      <Mesh p="b" />
      <Headline text="Built on Meta's models." at={0.05} size={88} top={90} grad={["Meta's"]} />
      <div style={{ position: "absolute", top: 300, left: 0, right: 0, display: "flex", justifyContent: "center", gap: 24 }}>
        {MODELS.map(([name, job, g], i) => {
          const at = 1.4 + i * VO("meta").seconds / 6.4;
          const s = useSpring(at, { damping: 12 });
          return (
            <div key={name} style={{ width: 330, height: 430, borderRadius: 30, padding: 30, background: "rgba(255,255,255,.88)", boxShadow: "0 40px 80px -40px rgba(40,20,120,.6)",
              transform: `translateY(${(1 - s) * 260}px) rotate(${(1 - s) * (i - 2) * 10}deg)`, opacity: Math.min(1, s * 1.6), display: "grid", alignContent: "start", gap: 20 }}>
              <div style={{ width: 84, height: 84, borderRadius: 24, background: `linear-gradient(135deg, ${g[0]}, ${g[1]})`, display: "grid", placeItems: "center",
                transform: `rotate(${Math.sin(t * 1.5 + i) * 6}deg)` }}>
                <div style={{ width: 36, height: 36, borderRadius: i === 3 ? 18 : 8, border: "4px dashed #fff" }} />
              </div>
              <div style={{ fontFamily: FONT, fontSize: 36, fontWeight: 850, color: INK, letterSpacing: "-0.02em" }}>{name}</div>
              <div style={{ fontFamily: FONT, fontSize: 25, fontWeight: 520, color: SUB, lineHeight: 1.32 }}>{job}</div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

const Close: React.FC = () => {
  const t = useT();
  const f = useCurrentFrame();
  const s = spring({ frame: f - 3.2 * FPS, fps: FPS, config: { damping: 10 } });
  return (
    <AbsoluteFill>
      <Mesh p="a" />
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", fontFamily: FONT, textAlign: "center" }}>
        <div style={{ opacity: 1 - ramp(t, 3.0, 3.4), transform: `translateY(${-ramp(t, 3.0, 3.4) * 40}px)` }}>
          <Words text="Prompting is how we talk to AI." at={0.1} style={{ fontSize: 88, fontWeight: 800, color: MUTE, letterSpacing: "-0.03em" }} />
          <Words text="Showing is how we'll teach it." at={1.4} style={{ fontSize: 96, fontWeight: 880, color: INK, letterSpacing: "-0.035em" }} color={(w) => (w === "Showing" ? "grad" : undefined)} />
        </div>
      </AbsoluteFill>
      {t > 3.1 && (
        <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", fontFamily: FONT }}>
          <div style={{ position: "relative", padding: "20px 60px", transform: `scale(${s})` }}>
            <Ants color={BLUE} width={5} radius={26} />
            <div style={{ fontSize: 200, fontWeight: 900, letterSpacing: "0.06em", fontVariationSettings: '"wdth" 125', color: INK }}>EIDOS</div>
          </div>
          <div style={{ marginTop: 36, fontSize: 34, fontWeight: 650, color: SUB, opacity: ramp(t, 3.8, 4.4) }}>Maruthi Kunchala, Team Parallax</div>
          <div style={{ marginTop: 8, fontSize: 24, fontWeight: 560, color: MUTE, opacity: ramp(t, 4.0, 4.6), maxWidth: 1600, textAlign: "center" }}>
            Meta Global AI Hackathon 2026. All footage is real; some clips are sped up. Real-world recordings: CaptainCook4D (Apache 2.0) and HoloAssist (CDLA-Permissive-2.0).
          </div>
        </AbsoluteFill>
      )}
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ assembly */

const LiveCab: React.FC = () => (
  <Studio src="live_cabinet" rate={2.2} head="Then it watches live." grad={["live."]} pal="a"
    pills={[[1.2, "Camera or any video, one frame a second", "plain"], [4.0, "Which step, what's next, does it match", "brand"]]} />
);
const Cabinet: React.FC = () => {
  const L = (world as any).live || {};
  return <Studio src="live_cabinet" from={L.cabFrom ?? 60} rate={L.cabRate ?? 1.4} head="Power still on. Flagged while it happens." grad={["Flagged"]} pal="d"
    zoom={[L.cabZoom ?? 4, 99, 1.45, 0, 100]} pills={[[L.cabZoom ?? 4, "Out of order: part removed before the power was off", "bad"]]} />;
};
const Kitchen: React.FC = () => {
  const L = (world as any).live || {};
  return <Studio src="live_tomato" from={L.tomFrom ?? 0} rate={L.tomRate ?? 12} head="It looks back, then names the skipped step." grad={["skipped"]} pal="c"
    zoom={[L.tomZoom ?? 8, 99, 1.45, 0, 100]} pills={[[L.tomZoom ?? 8, "Skipped: pour the oil", "bad"]]} />;
};

const SCENES: { id: string; C: React.FC; min?: number; pad?: number }[] = [
  { id: "hook", C: Hook, min: 13.4 },
  { id: "name", C: Name, pad: 1.4 },
  { id: "learn", C: Learn, min: 16 },
  { id: "again", C: Again, pad: 1.4 },
  { id: "live", C: LiveCab, pad: 1.2 },
  { id: "cabinet", C: Cabinet, pad: 2.0 },
  { id: "kitchen", C: Kitchen, pad: 2.0 },
  { id: "anything", C: Anything, pad: 1.4 },
  { id: "results", C: Results, pad: 1.6 },
  { id: "screens", C: Screens, pad: 1.2 },
  { id: "meta", C: Meta, pad: 1.4 },
  { id: "close", C: Close, min: 9 },
];
const TR = 14;
const LEAD = 0.35;
export const sceneFrames2 = SCENES.map((s) => Math.round(Math.max(VO(s.id).seconds + LEAD + (s.pad ?? 1.0), s.min ?? 0) * FPS));
export const launch2Frames = sceneFrames2.reduce((a, b) => a + b, 0) - TR * (SCENES.length - 1);
const starts = sceneFrames2.map((_, i) => sceneFrames2.slice(0, i).reduce((a, b) => a + b, 0) - TR * i);
const TRANS = [slide({ direction: "from-right" }), wipe({ direction: "from-left" }), fade(), slide({ direction: "from-bottom" })];

export const Launch2: React.FC = () => (
  <AbsoluteFill style={{ background: "#f7f5ff" }}>
    <TransitionSeries>
      {SCENES.flatMap((s, i) => {
        const items = [
          <TransitionSeries.Sequence key={s.id} durationInFrames={sceneFrames2[i]}>
            <s.C />
            <Caption id={s.id} at={LEAD} />
          </TransitionSeries.Sequence>,
        ];
        if (i < SCENES.length - 1) items.push(<TransitionSeries.Transition key={s.id + "-t"} presentation={TRANS[i % TRANS.length] as any} timing={linearTiming({ durationInFrames: TR })} />);
        return items;
      })}
    </TransitionSeries>
    {SCENES.map((s, i) => (
      <Sequence key={s.id} from={starts[i] + Math.round(LEAD * FPS)} durationInFrames={Math.round(VO(s.id).seconds * FPS) + 10}>
        <Audio src={staticFile(`vo5/${s.id}.wav`)} />
      </Sequence>
    ))}
    <Audio src={staticFile("music/bed2.mp3")} volume={0.5} />
  </AbsoluteFill>
);
