// EIDOS explainer, "product launch" look: bright moving gradients, heavy kinetic type,
// the app in clean browser windows, springy motion graphics.
import React from "react";
import { AbsoluteFill, Img, interpolate, Sequence, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { Audio, Video } from "@remotion/media";
import { TransitionSeries, linearTiming } from "@remotion/transitions";
import { slide } from "@remotion/transitions/slide";
import { fade } from "@remotion/transitions/fade";
import { wipe } from "@remotion/transitions/wipe";
import { FONT, MONO, ease } from "./ui";
import timeline from "./timeline4.json";
import mail from "./mail_trace.json";

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
  const parts = vo.text.replace(/Eye-doss/g, "EIDOS").match(/[^.!?]+[.!?]+/g) || [vo.text];
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

/* ------------------------------------------------------------------ scenes */

const Hook: React.FC = () => {
  const t = useT();
  const fr = useCurrentFrame();
  const cards = Array.from({ length: 12 }, (_, i) => i);
    const gather = ramp(t, 7.4, 9.0);
  return (
    <AbsoluteFill>
      <Mesh p="a" />
      <AbsoluteFill style={{ perspective: 1600 }}>
        {cards.map((i) => {
          const col = i % 4, row = Math.floor(i / 4);
          const x0 = 140 + col * 430 + (row % 2) * 120, y0 = 120 + row * 300;
          const s = spring({ frame: fr - i * 3, fps: FPS, config: { damping: 15 } });
          const drift = Math.sin(t * 0.8 + i) * 14;
          const x = x0 + (960 - 190 - x0) * gather, y = y0 + drift + (540 - 110 - y0) * gather;
          return (
            <div key={i} style={{ position: "absolute", left: x, top: y, width: 380, height: 236, borderRadius: 18, overflow: "hidden", background: "#fff",
              transform: `translateZ(${(1 - s) * -600}px) rotateY(${(col - 1.5) * 8 * (1 - gather)}deg) rotate(${(i % 3 - 1) * 3 * (1 - gather) + gather * (i - 6) * 2}deg) scale(${(0.6 + 0.4 * s) * (1 - gather * 0.25)})`,
              opacity: s * (1 - ramp(t, 9.6, 10.4)), boxShadow: "0 30px 60px -24px rgba(30,20,90,.5)" }}>
              <Img src={staticFile(`thumbs/t${i}.jpg`)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
              <div style={{ position: "absolute", left: 12, bottom: 12, width: 44, height: 44, borderRadius: 22, background: "rgba(13,15,26,.75)", display: "grid", placeItems: "center" }}>
                <svg width="18" height="18" viewBox="0 0 18 18"><path d="M5 3l10 6-10 6z" fill="#fff" /></svg>
              </div>
              <div style={{ position: "absolute", right: 10, top: 10, fontFamily: MONO, fontSize: 14, padding: "3px 8px", borderRadius: 6, background: RED, color: "#fff" }}>REC</div>
            </div>
          );
        })}
      </AbsoluteFill>
      {t > 2.6 && t < 7.0 && (
        <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", fontFamily: FONT, color: INK, opacity: 1 - ramp(t, 6.4, 6.9),
          background: `rgba(247,245,255,${0.55 * ramp(t, 2.6, 3.0)})`, backdropFilter: `blur(${12 * ramp(t, 2.6, 3.0)}px)` }}>
          <Words text="Billions of hours." at={2.7} step={0.12} style={{ fontSize: 190, fontWeight: 900, letterSpacing: "-0.05em", lineHeight: 1.05 }} color={(w) => (w === "Billions" ? "grad" : undefined)} />
          <div style={{ fontSize: 46, fontWeight: 700, color: SUB, marginTop: 14, opacity: ramp(t, 3.4, 3.9) }}>of people showing each other how things get done</div>
        </AbsoluteFill>
      )}
      {t > 9.2 && <Headline text="An agent still can't learn from one." at={9.3} size={104} top={380} grad={["learn"]} max={1500} />}
    </AbsoluteFill>
  );
};

const Problem: React.FC = () => {
  const t = useT();
  // a tiny app: the button moves away (a redesign) and the copied click lands on nothing
  const moved = ramp(t, 2.2, 3.0);
  const bx = 980 + moved * 420, by = 540 - moved * 160;
  const cur = t < 1.0 ? [700, 760] : t < 1.8 ? [700 + (1004 - 700) * ramp(t, 1.0, 1.8), 760 + (566 - 760) * ramp(t, 1.0, 1.8)] : [1004, 566];
  const click1 = t > 1.8 && t < 2.2, click2 = t > 3.6;
  const ring = (at: number) => { const p = ramp(t, at, at + 0.5); return { transform: `scale(${0.4 + p * 1.6})`, opacity: 1 - p }; };
  const shake = t > 3.7 && t < 4.3 ? Math.sin(t * 90) * 8 * (1 - ramp(t, 3.7, 4.3)) : 0;
  return (
    <AbsoluteFill>
      <Mesh p="d" />
      <Headline text="Copy the clicks, and a redesign breaks it." at={0.1} size={74} top={80} grad={["breaks"]} max={1840} />
      <div style={{ position: "absolute", left: 360, top: 250, transform: `translateX(${shake}px)` }}>
        <Browser w={1200} h={560} url="mail.postwise.app">
          <div style={{ position: "absolute", inset: 0, background: "#f4f6f9" }} />
          <div style={{ position: "absolute", left: 40, top: 40, width: 1120, height: 70, borderRadius: 14, background: "#fff", border: "1px solid #dbe1ea" }} />
          {[0, 1, 2].map((i) => <div key={i} style={{ position: "absolute", left: 40, top: 140 + i * 90, width: 760, height: 60, borderRadius: 12, background: "#fff", border: "1px solid #dbe1ea" }} />)}
          <div style={{ position: "absolute", left: bx - 360 - 90, top: by - 250 - 44 - 30, width: 180, height: 60, borderRadius: 14, background: BLUE, color: "#fff",
            fontFamily: FONT, fontWeight: 800, fontSize: 26, display: "grid", placeItems: "center", boxShadow: "0 12px 26px -10px rgba(59,91,255,.7)" }}>Send</div>
        </Browser>
      </div>
      {/* click rings and pointer */}
      {click1 && <div style={{ position: "absolute", left: cur[0] - 30, top: cur[1] - 30, width: 60, height: 60, borderRadius: 30, border: `5px solid ${BLUE}`, ...ring(1.8) }} />}
      {click2 && <div style={{ position: "absolute", left: 1004 - 30, top: 566 - 30, width: 60, height: 60, borderRadius: 30, border: `5px solid ${RED}`, ...ring(3.6) }} />}
      <svg width="40" height="46" viewBox="0 0 26 30" style={{ position: "absolute", left: cur[0] - 4, top: cur[1] - 4, filter: "drop-shadow(0 4px 6px rgba(0,0,0,.35))" }}>
        <path d="M2 2 L2 24 L8 18.5 L12.5 28 L16.5 26.2 L12 17 L20 17 Z" fill={INK} stroke="#fff" strokeWidth="2" strokeLinejoin="round" />
      </svg>
      {t > 3.8 && <div style={{ position: "absolute", left: 1040, top: 600 }}><Pill at={3.8} tone="bad">Clicked on nothing</Pill></div>}
      {t > 5.6 && <div style={{ position: "absolute", left: 0, right: 0, top: 860, display: "flex", justifyContent: "center" }}><Pill at={5.6} size={34}>…and it never notices.</Pill></div>}
    </AbsoluteFill>
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

const Name: React.FC = () => {
  const t = useT();
  const f = useCurrentFrame();
  const letters = "EIDOS".split("");
  return (
    <AbsoluteFill>
      <Mesh p="b" />
      {/* floating dashed squares */}
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
            {letters.map((l, i) => {
              const s = spring({ frame: f - (0.4 + i * 0.09) * FPS, fps: FPS, config: { damping: 9, mass: 0.7 } });
              return <span key={i} style={{ display: "inline-block", transform: `translateY(${(1 - s) * 140}px) rotate(${(1 - s) * (i % 2 ? 18 : -18)}deg) scale(${0.4 + 0.6 * s})`, opacity: Math.min(1, s * 1.5) }}>{l}</span>;
            })}
          </div>
        </div>
        <div style={{ marginTop: 40, maxWidth: 1500 }}>
          <Words text="Show it once. It learns the skill, and checks its own work." at={1.6} step={0.06} style={{ fontFamily: FONT, fontSize: 52, fontWeight: 700, color: SUB }}
            color={(w) => (w.startsWith("checks") || w === "own" || w.startsWith("work") ? "grad" : undefined)} />
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

const STEP_LABELS = [["press", "Compose"], ["type", "{to} into “To”"], ["type", "{subject} into “Subject”"], ["type", "{message} into “Message”"], ["press", "Send"]];
const Watch: React.FC = () => {
  const t = useT();
  const fr = useCurrentFrame();
  const RATE = 1.25, W = 1080, H = Math.round(1080 * 760 / 1200), k = W / 1200;
  const vt = t * RATE + 0.6;
  return (
    <AbsoluteFill>
      <Mesh p="c" />
      <Headline text="It reads the video, and writes a skill." at={0.1} size={76} top={56} grad={["skill"]} />
      <div style={{ position: "absolute", left: 90, top: 210, transform: `scale(${0.96 + ramp(t, 0, 2) * 0.04})`, transformOrigin: "left top" }}>
        <Browser w={W} h={H} url="tutorial_mail.mp4 (19 s recording)">
          <Clip src="tutorial_mail" w={W} h={H} rate={RATE} from={0.6} />
          {mail.steps.map((s, i) => {
            const nx = mail.steps[i + 1];
            const on = vt > s.t - 0.1 && vt < (nx ? nx.t - 0.1 : 99);
            if (!on) return null;
            const ok = vt > s.t + 0.8;
            const b = s.box;
            return (
              <div key={i} style={{ position: "absolute", left: b[0] * k - 6, top: b[1] * k - 6, width: b[2] * k + 12, height: b[3] * k + 12 }}>
                <Ants color={ok ? GREEN : BLUE} width={4} radius={10} />
              </div>
            );
          })}
        </Browser>
      </div>
      <div style={{ position: "absolute", left: 1230, top: 216, width: 600, display: "grid", gap: 14 }}>
        <div style={{ fontFamily: FONT, fontSize: 30, fontWeight: 800, color: INK, opacity: ramp(t, 0.6, 1.0) }}>The skill</div>
        {STEP_LABELS.map(([d, l], i) => {
          const appear = (mail.steps[i].t - 0.6) / RATE + 0.2;
          const s = spring({ frame: fr - appear * FPS, fps: FPS, config: { damping: 13 } });
          const ok = vt > mail.steps[i].t + 0.8;
          return (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 14, padding: "16px 20px", borderRadius: 18, background: "rgba(255,255,255,.9)",
              boxShadow: "0 16px 34px -20px rgba(30,20,90,.5)", transform: `translateX(${(1 - s) * 120}px)`, opacity: Math.min(1, s * 1.4),
              border: `2px solid ${ok ? GREEN : "transparent"}` }}>
              <span style={{ fontFamily: MONO, fontSize: 18, padding: "4px 10px", borderRadius: 8, background: d === "press" ? "#ece9ff" : "#e6f6ff", color: d === "press" ? VIOLET : "#0b7fb3" }}>{d}</span>
              <span style={{ fontFamily: FONT, fontSize: 26, fontWeight: 700, color: INK, whiteSpace: "nowrap" }}>{l.split(/(\{\w+\})/).map((x, j) => /^\{/.test(x) ? <span key={j} style={{ color: BLUE }}>{x}</span> : x)}</span>
              <span style={{ marginLeft: "auto", width: 30, height: 30, borderRadius: 15, background: ok ? GREEN : "#e9e7f3", display: "grid", placeItems: "center", color: "#fff", fontSize: 18, fontWeight: 900 }}>{ok ? "✓" : ""}</span>
            </div>
          );
        })}
        <div style={{ display: "flex", flexWrap: "wrap", gap: 10, marginTop: 8 }}>
          {t > 8.6 && <Pill at={8.6} tone="brand" size={22}>Targets by label</Pill>}
          {t > 9.6 && <Pill at={9.6} tone="brand" size={22}>Values become inputs</Pill>}
          {t > 11.2 && <Pill at={11.2} tone="ok" size={22}>A contract per step</Pill>}
        </div>
      </div>
    </AbsoluteFill>
  );
};

const Duel: React.FC<{ head: string; grad: string[]; pal: keyof typeof PALETTES; left: [string, string, number, string, "ok" | "bad"]; right: [string, string, number, string, "ok" | "bad"]; dark?: boolean; at: number; extra?: React.ReactNode; sub?: string }> = ({ head, grad, pal, left, right, dark, at, extra, sub }) => {
  const t = useT();
  const W = 820, H = Math.round(820 * 760 / 1200);
  const lane = (side: 0 | 1, [title, src, rate, verdict, tone]: [string, string, number, string, "ok" | "bad"]) => {
    const s = useSpring(0.3 + side * 0.15, { damping: 16 });
    return (
      <div style={{ display: "grid", gap: 16, justifyItems: "center", transform: `translateY(${(1 - s) * 200}px) rotateY(${(side ? -1 : 1) * 6 * (1 - ramp(t, 0.4, 2))}deg)`, opacity: Math.min(1, s * 1.5) }}>
        <div style={{ fontFamily: FONT, fontSize: 34, fontWeight: 800, color: side ? BLUE : SUB }}>{title}</div>
        <Browser w={W} h={H} url="your-app.com" dark={dark}><Clip src={src} w={W} h={H} rate={rate} /></Browser>
        <div style={{ height: 70 }}>{t > at && <Pill at={at + side * 0.25} tone={tone}>{verdict}</Pill>}</div>
      </div>
    );
  };
  return (
    <AbsoluteFill style={{ perspective: 2000 }}>
      <Mesh p={pal} />
      <Headline text={head} at={0.05} size={72} top={52} grad={grad} max={1700} />
      {sub && <div style={{ position: "absolute", top: 140, left: 0, right: 0, textAlign: "center", fontFamily: FONT, fontSize: 30, fontWeight: 600, color: SUB, opacity: ramp(t, 0.6, 1.1) }}>{sub}</div>}
      <div style={{ position: "absolute", top: 200, left: 0, right: 0, display: "flex", justifyContent: "center", gap: 70 }}>
        {lane(0, left)}{lane(1, right)}
      </div>
      {extra}
    </AbsoluteFill>
  );
};

const OtherApp: React.FC = () => (
  <Duel head="Run it where the video never went." grad={["never", "went"]} pal="a" dark at={9.6}
    sub="A new design, dark mode, fields shuffled, new values"
    left={["Copying the clicks", "other_replay", 1, "Nothing was sent", "bad"]}
    right={["EIDOS", "other_eidos", 1.6, "Sent, every step checked", "ok"]} />
);

const Interrupt: React.FC = () => (
  <Duel head="Something gets in the way." grad={["way"]} pal="b" at={9.4}
    sub="A dialog pops up and swallows the keystrokes"
    left={["Checks off", "int_nochk", 1, "Said done. Nothing sent.", "bad"]}
    right={["EIDOS", "int_eidos", 1.7, "Check failed, so it redid the step", "ok"]} />
);

const ALIASES = [["To", "Recipient"], ["Send", "Deliver"], ["Compose", "New email"], ["Subject", "Topic"], ["Message", "Body"]];
const Renamed: React.FC = () => {
  const t = useT();
  return (
    <Duel head="Rename every control." grad={["every"]} pal="c" dark at={10.4}
      sub="Offline it stops and says so. With Muse Spark, it reads for meaning."
      left={["EIDOS, offline", "renamed_offline", 1, "Stopped: couldn't find “Compose”", "bad"]}
      right={["EIDOS + Muse Spark", "renamed_live", 5.6, "Delivered, every step checked", "ok"]}
      extra={<div style={{ position: "absolute", left: 0, right: 0, top: 900, display: "flex", justifyContent: "center", gap: 14 }}>
        {ALIASES.map(([a, b], i) => t > 3 + i * 0.6 && t < 10.2 ? <Pill key={a} at={3 + i * 0.6} size={24} tone="brand">{a} <span style={{ opacity: .7 }}>→</span> {b}</Pill> : null)}
      </div>} />
  );
};


const TASKS: [string, string, string][] = [["tutorial_mail", "Send an email", "mail.postwise.app"], ["tutorial_calendar", "Add a calendar event", "calendar.app"],
  ["tutorial_expense", "Submit an expense", "expenses.app"], ["tutorial_settings", "Turn on two-factor sign-in", "settings.app"], ["tutorial_totals", "Add a totals row", "sheets.app"]];
const Tasks: React.FC = () => {
  const t = useT();
  const fr = useCurrentFrame();
  const W = 440, H = Math.round(440 * 760 / 1200);
  const kinds: [string, string][] = [["press", VIOLET], ["type", "#0b7fb3"], ["choose", CORAL], ["switch", GREEN]];
  return (
    <AbsoluteFill style={{ perspective: 2200 }}>
      <Mesh p="d" />
      <Headline text="Not one demo. One engine." at={0.05} size={84} top={50} grad={["engine"]} />
      <div style={{ position: "absolute", top: 190, left: 0, right: 0, display: "flex", flexWrap: "wrap", justifyContent: "center", gap: "28px 34px", padding: "0 120px" }}>
        {TASKS.map(([src, title, url], i) => {
          const s = spring({ frame: fr - (0.5 + i * 0.55) * FPS, fps: FPS, config: { damping: 13 } });
          const h = src === "tutorial_totals" ? Math.round(W * 620 / 1100) : H;
          return (
            <div key={src} style={{ display: "grid", gap: 10, justifyItems: "center", transform: `translateY(${(1 - s) * 160}px) rotateX(${(1 - s) * 30}deg) rotate(${(i % 2 ? 1 : -1) * (1 - s) * 8}deg)`, opacity: Math.min(1, s * 1.5) }}>
              <Browser w={W} h={h} url={url}><Clip src={src} w={W} h={h} rate={1.6} from={2} /></Browser>
              <div style={{ fontFamily: FONT, fontSize: 26, fontWeight: 760, color: INK }}>{title}</div>
            </div>
          );
        })}
      </div>
      <div style={{ position: "absolute", right: 140, bottom: 150, display: "grid", gap: 14 }}>
        {kinds.map(([k, c], i) => {
          const at = 5.6 + i * 0.45;
          const s = spring({ frame: fr - at * FPS, fps: FPS, config: { damping: 8, mass: 0.8 } });
          return <div key={k} style={{ fontFamily: MONO, fontSize: 40, fontWeight: 600, padding: "10px 26px", borderRadius: 16, background: "#fff", color: c,
            boxShadow: "0 18px 36px -18px rgba(30,20,90,.55)", transform: `scale(${s}) rotate(${(1 - s) * 30}deg)`, opacity: Math.min(1, s * 2), textAlign: "center" }}>{k}</div>;
        })}
      </div>
    </AbsoluteFill>
  );
};

const Teach: React.FC = () => {
  const t = useT();
  const W = 1220, H = Math.round(1220 * 900 / 1440);
  const s = useSpring(0.1, { damping: 16 });
  return (
    <AbsoluteFill>
      <Mesh p="d" />
      <Headline text="Teach it yourself." at={0.05} size={84} top={44} grad={["yourself"]} />
      <div style={{ position: "absolute", left: (1920 - W) / 2, top: 168, transform: `translateY(${(1 - s) * 300}px) scale(${0.94 + 0.06 * s})`, transformOrigin: "center top" }}>
        <Browser w={W} h={H} url="localhost:8000  EIDOS Studio">
          <Sequence durationInFrames={7 * FPS}><Clip src="teach_live" w={W} h={H} /></Sequence>
          <Sequence from={7 * FPS}><Clip src="teach_learned" w={W} h={H} /></Sequence>
        </Browser>
      </div>
      <div style={{ position: "absolute", left: (1920 + W) / 2 - 150, top: 140 }}>
        {t < 7 ? <Pill at={0.6} tone="bad" size={24}><span style={{ width: 12, height: 12, borderRadius: 6, background: "#fff", opacity: 0.5 + 0.5 * Math.sin(t * 8) }} />REC</Pill>
          : <Pill at={7} tone="ok" size={24}>Learned</Pill>}
      </div>
    </AbsoluteFill>
  );
};

const Roll: React.FC<{ value: number; at: number; dur?: number }> = ({ value, at, dur = 1.3 }) => {
  const t = useT();
  return <>{Math.round(value * ramp(t, at, at + dur))}</>;
};
const Results: React.FC = () => {
  const t = useT();
  const fr = useCurrentFrame();
  const beats: { at: number; n: number; d: number; line: string; pills: [string, "ok" | "bad" | "plain" | "brand"][] }[] = [
    { at: 0.2, n: 60, d: 60, line: "everyday runs it had never seen", pills: [["EIDOS 60/60", "brand"], ["Copying the clicks 4/60", "plain"]] },
    { at: 6.0, n: 32, d: 32, line: "with every control renamed", pills: [["Muse Spark 32/32", "brand"], ["Muse Spark Open 32/32", "brand"], ["Offline 0/32, and said so", "plain"]] },
    { at: 10.6, n: 168, d: 168, line: "times its own verdict matched the truth", pills: [["No silent failures", "ok"]] },
  ];
  return (
    <AbsoluteFill>
      <Mesh p="a" />
      <div style={{ position: "absolute", top: 70, left: 0, right: 0, textAlign: "center", fontFamily: FONT, fontSize: 40, fontWeight: 700, color: SUB, opacity: ramp(t, 0.1, 0.5) }}>
        Held-out tests, kept aside and run once
      </div>
      {beats.map((b, i) => {
        const nx = beats[i + 1];
        const vis = t >= b.at && (!nx || t < nx.at);
        if (!vis) return null;
        const pop = spring({ frame: fr - b.at * FPS, fps: FPS, config: { damping: 12 } });
        return (
          <AbsoluteFill key={i} style={{ alignItems: "center", justifyContent: "center", fontFamily: FONT, textAlign: "center" }}>
            <div style={{ fontSize: 300, fontWeight: 900, letterSpacing: "-0.06em", lineHeight: 1.05, fontVariantNumeric: "tabular-nums", padding: "0 30px",
              background: GRAD, WebkitBackgroundClip: "text", color: "transparent", transform: `scale(${0.7 + 0.3 * pop})` }}>
              <Roll value={b.n} at={b.at + 0.1} />/{b.d}
            </div>
            <div style={{ fontSize: 50, fontWeight: 760, color: INK, marginTop: -6, opacity: ramp(t, b.at + 0.4, b.at + 0.9) }}>{b.line}</div>
            <div style={{ display: "flex", gap: 16, marginTop: 34, flexWrap: "wrap", justifyContent: "center", maxWidth: 1600 }}>
              {b.pills.map(([p, tone], j) => <Pill key={p} at={b.at + 1.2 + j * 0.3} tone={tone}>{p}</Pill>)}
            </div>
          </AbsoluteFill>
        );
      })}
    </AbsoluteFill>
  );
};

const MODELS: [string, string, string[]][] = [
  ["Muse Spark", "Reads the screen for meaning, and must pick text that is really there", [BLUE, VIOLET]],
  ["SAM 3.1", "A second opinion on where every field and button is", [CYAN, BLUE]],
  ["Muse Image", "Draws a card for every skill", [CORAL, "#ffc24b"]],
  ["Muse Spark Open", "The same reading job, with open weights on Baseten", [VIOLET, "#ff5fa2"]],
];
const Meta: React.FC = () => {
  const t = useT();
  return (
    <AbsoluteFill>
      <Mesh p="b" />
      <Headline text="Built on Meta's models." at={0.05} size={88} top={90} grad={["Meta's"]} />
      <div style={{ position: "absolute", top: 300, left: 0, right: 0, display: "flex", justifyContent: "center", gap: 30 }}>
        {MODELS.map(([name, job, g], i) => {
          const at = 1.4 + i * VO("meta").seconds / 5.2;
          const s = useSpring(at, { damping: 12 });
          return (
            <div key={name} style={{ width: 390, height: 440, borderRadius: 30, padding: 34, background: "rgba(255,255,255,.88)", boxShadow: "0 40px 80px -40px rgba(40,20,120,.6)",
              transform: `translateY(${(1 - s) * 260}px) rotate(${(1 - s) * (i - 1.5) * 10}deg)`, opacity: Math.min(1, s * 1.6), display: "grid", alignContent: "start", gap: 22 }}>
              <div style={{ width: 92, height: 92, borderRadius: 26, background: `linear-gradient(135deg, ${g[0]}, ${g[1]})`, display: "grid", placeItems: "center",
                transform: `rotate(${Math.sin(t * 1.5 + i) * 6}deg)` }}>
                <div style={{ width: 40, height: 40, borderRadius: i === 2 ? 20 : 8, border: "4px dashed #fff" }} />
              </div>
              <div style={{ fontFamily: FONT, fontSize: 40, fontWeight: 850, color: INK, letterSpacing: "-0.02em" }}>{name}</div>
              <div style={{ fontFamily: FONT, fontSize: 27, fontWeight: 520, color: SUB, lineHeight: 1.32 }}>{job}</div>
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
          <div style={{ marginTop: 8, fontSize: 26, fontWeight: 560, color: MUTE, opacity: ramp(t, 4.0, 4.6) }}>Meta Global AI Hackathon 2026. All app footage is real; some clips are sped up.</div>
        </AbsoluteFill>
      )}
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ assembly */

const SCENES: { id: string; C: React.FC; min?: number; pad?: number }[] = [
  { id: "hook", C: Hook, min: 11.6 },
  { id: "problem", C: Problem, pad: 1.4 },
  { id: "name", C: Name, pad: 1.6 },
  { id: "watch", C: Watch, min: 16.6 },
  { id: "otherapp", C: OtherApp, min: 12.6 },
  { id: "interrupt", C: Interrupt, min: 12.6 },
  { id: "renamed", C: Renamed, min: 13.8 },
  { id: "tasks", C: Tasks, pad: 1.4 },
  { id: "teach", C: Teach, min: 12.2 },
  { id: "results", C: Results, min: 17.4 },
  { id: "meta", C: Meta, pad: 1.4 },
  { id: "close", C: Close, min: 8.4 },
];
const TR = 14;                                  // transition overlap, frames
const LEAD = 0.35;                              // voice starts this long into a scene
export const sceneFrames = SCENES.map((s) => Math.round(Math.max(VO(s.id).seconds + LEAD + (s.pad ?? 1.0), s.min ?? 0) * FPS));
export const launchFrames = sceneFrames.reduce((a, b) => a + b, 0) - TR * (SCENES.length - 1);
export const sceneStarts = sceneFrames.map((_, i) => sceneFrames.slice(0, i).reduce((a, b) => a + b, 0) - TR * i);

const TRANS = [slide({ direction: "from-right" }), wipe({ direction: "from-left" }), fade(), slide({ direction: "from-bottom" })];

export const Launch: React.FC = () => (
  <AbsoluteFill style={{ background: "#f7f5ff" }}>
    <TransitionSeries>
      {SCENES.flatMap((s, i) => {
        const items = [
          <TransitionSeries.Sequence key={s.id} durationInFrames={sceneFrames[i]}>
            <s.C />
            <Caption id={s.id} at={LEAD} />
          </TransitionSeries.Sequence>,
        ];
        if (i < SCENES.length - 1) items.push(<TransitionSeries.Transition key={s.id + "-t"} presentation={TRANS[i % TRANS.length] as any} timing={linearTiming({ durationInFrames: TR })} />);
        return items;
      })}
    </TransitionSeries>
    {SCENES.map((s, i) => (
      <Sequence key={s.id} from={sceneStarts[i] + Math.round(LEAD * FPS)} durationInFrames={Math.round(VO(s.id).seconds * FPS) + 10}>
        <Audio src={staticFile(`vo4/${s.id}.wav`)} />
      </Sequence>
    ))}
    <Audio src={staticFile("music/bed.mp3")} volume={0.5} />
  </AbsoluteFill>
);
