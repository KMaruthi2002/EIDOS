// Two style previews for the new explainer: the same three beats in two looks.
import React from "react";
import { AbsoluteFill, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig, Sequence } from "remotion";
import { Video } from "@remotion/media";
import { FONT, MONO, ease } from "./ui";

const BOX = [409, 133, 444, 33]; // the "To" field in the mail tutorial (1200 x 760)
const sec = (f: number, fps: number) => f / fps;
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

const useT = () => { const f = useCurrentFrame(); const { fps } = useVideoConfig(); return sec(f, fps); };
const ramp = (t: number, a: number, b: number, from = 0, to = 1) => interpolate(t, [a, b], [from, to], { ...clamp, easing: ease });

/* ------------------------------------------------------------------ shared pieces */

const Ants: React.FC<{ w?: number; h?: number; color: string; t: number; draw?: number; width?: number; radius?: number }> = ({ color, t, draw = 1, width = 3, radius = 6 }) => (
  <svg width="100%" height="100%" style={{ position: "absolute", inset: 0, overflow: "visible" }}>
    <rect x={0} y={0} width="100%" height="100%" rx={radius} fill="none" stroke={color} strokeWidth={width} pathLength={100}
      strokeDasharray={draw < 1 ? `${100 * draw} 100` : "1.2 0.8"} strokeDashoffset={draw < 1 ? 0 : -t * 4}
      style={{ filter: `drop-shadow(0 0 8px ${color})` }} />
  </svg>
);

const Words: React.FC<{ text: string; t: number; start: number; step?: number; style?: React.CSSProperties; blur?: boolean }> = ({ text, t, start, step = 0.09, style, blur }) => (
  <span style={{ display: "inline-flex", flexWrap: "wrap", gap: "0 0.28em", ...style }}>
    {text.split(" ").map((w, i) => {
      const p = ramp(t, start + i * step, start + i * step + 0.55);
      return (
        <span key={i} style={{ display: "inline-block", overflow: blur ? "visible" : "hidden", paddingBottom: "0.08em" }}>
          <span style={{ display: "inline-block", transform: `translateY(${(1 - p) * (blur ? 30 : 105)}%)`, opacity: blur ? p : 1,
            filter: blur ? `blur(${(1 - p) * 14}px)` : undefined }}>{w}</span>
        </span>
      );
    })}
  </span>
);

const Counter: React.FC<{ to: number; t: number; start: number; dur?: number }> = ({ to, t, start, dur = 1.4 }) => (
  <>{Math.round(to * ramp(t, start, start + dur))}</>
);

/* ------------------------------------------------------------------ style 1: cinematic dark */

const DarkBg: React.FC<{ t: number }> = ({ t }) => (
  <AbsoluteFill style={{ background: "#03050b", overflow: "hidden" }}>
    <AbsoluteFill style={{ background: `radial-gradient(60% 55% at ${50 + Math.sin(t * 0.6) * 6}% ${46 + Math.cos(t * 0.5) * 4}%, rgba(56,92,255,.30), transparent 70%)` }} />
    <div style={{ position: "absolute", left: "-25%", right: "-25%", bottom: "-38%", height: "80%", transform: "perspective(900px) rotateX(64deg)",
      backgroundImage: "linear-gradient(rgba(110,140,255,.22) 1px, transparent 1px), linear-gradient(90deg, rgba(110,140,255,.22) 1px, transparent 1px)",
      backgroundSize: "80px 80px", backgroundPosition: `0 ${t * 40}px`, maskImage: "linear-gradient(transparent, #000 60%)", WebkitMaskImage: "linear-gradient(transparent, #000 60%)" }} />
    <AbsoluteFill style={{ background: "radial-gradient(120% 90% at 50% 45%, transparent 55%, rgba(0,0,0,.85))" }} />
    <svg width="100%" height="100%" style={{ position: "absolute", inset: 0, opacity: 0.09, mixBlendMode: "screen" }}>
      <filter id="grain"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed={Math.floor(t * 24)} /></filter>
      <rect width="100%" height="100%" filter="url(#grain)" />
    </svg>
  </AbsoluteFill>
);

const BLUE = "#5b7cff", GREEN = "#3ee0a8";

const DarkTitle: React.FC = () => {
  const t = useT();
  const draw = ramp(t, 0.9, 2.0);
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", fontFamily: FONT, color: "#eef2ff" }}>
      <div style={{ position: "relative", padding: "28px 56px" }}>
        <div style={{ position: "absolute", inset: 0 }}><Ants w={1180} h={250} color={BLUE} t={t} draw={draw} width={4} radius={18} /></div>
        <div style={{ fontSize: 200, fontWeight: 850, letterSpacing: "-0.035em", fontVariationSettings: '"wdth" 112', lineHeight: 1 }}>
          <Words text="Show it once." t={t} start={0.15} blur />
        </div>
      </div>
      <div style={{ fontFamily: MONO, fontSize: 30, color: "#8ea2ff", marginTop: 34, letterSpacing: ".04em", opacity: ramp(t, 1.6, 2.3) }}>
        one tutorial video  →  a skill that checks its own work
      </div>
    </AbsoluteFill>
  );
};

const DarkApp: React.FC = () => {
  const t = useT();
  const W = 1200, H = 760, s = 1.18;
  const tilt = ramp(t, 0, 2.6);
  const push = ramp(t, 1.2, 3.6);
  const ok = t > 2.6;
  const cx = BOX[0] + BOX[2] / 2, cy = BOX[1] + BOX[3] / 2;
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", perspective: 2000 }}>
      <div style={{ width: W, height: H, position: "relative", borderRadius: 18, overflow: "visible",
        transformOrigin: `${cx}px ${cy}px`,
        transform: `translateY(${(1 - tilt) * 80}px) rotateY(${-24 + tilt * 20}deg) rotateX(${12 - tilt * 9}deg) scale(${s * (0.86 + push * 0.5)}) translate(${push * (W / 2 - cx) * 0.55}px, ${push * (H / 2 - cy) * 0.55}px)`,
        boxShadow: `0 0 0 1px rgba(120,150,255,.35), 0 40px 120px -20px rgba(40,70,255,.55)` }}>
        <div style={{ position: "absolute", inset: 0, borderRadius: 18, overflow: "hidden" }}>
          <Video src={staticFile("clips/tutorial_mail.mp4")} trimBefore={Math.round(3.9 * 30)} muted style={{ width: W, height: H }} />
          <AbsoluteFill style={{ background: "rgba(3,6,14,.42)", opacity: ramp(t, 1.4, 2.0) }} />
        </div>
        {/* spotlight hole: re-draw the field area un-dimmed */}
        <div style={{ position: "absolute", left: BOX[0], top: BOX[1], width: BOX[2], height: BOX[3], borderRadius: 6, overflow: "hidden", opacity: ramp(t, 1.4, 2.0) }}>
          <div style={{ position: "absolute", left: -BOX[0], top: -BOX[1], width: W, height: H }}>
            <Video src={staticFile("clips/tutorial_mail.mp4")} trimBefore={Math.round(3.9 * 30)} muted style={{ width: W, height: H }} />
          </div>
        </div>
        <div style={{ position: "absolute", left: BOX[0], top: BOX[1], width: BOX[2], height: BOX[3], opacity: ramp(t, 1.3, 1.6) }}>
          <Ants w={BOX[2]} h={BOX[3]} color={ok ? GREEN : BLUE} t={t} width={3} />
          <div style={{ position: "absolute", left: 0, top: -44, fontFamily: MONO, fontSize: 17, whiteSpace: "nowrap", padding: "6px 12px", borderRadius: 8,
            background: ok ? GREEN : BLUE, color: "#04101c", fontWeight: 600, transform: `translateY(${(1 - ramp(t, 1.5, 1.9)) * 10}px)`, opacity: ramp(t, 1.5, 1.9) }}>
            {ok ? "✓ contract held: To shows maya@northwind.com" : "contract: the box labelled To shows {to}"}
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

const DarkResult: React.FC = () => {
  const t = useT();
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", fontFamily: FONT, color: "#eef2ff" }}>
      <div style={{ fontFamily: MONO, fontSize: 26, color: "#8ea2ff", letterSpacing: ".06em", opacity: ramp(t, 0.1, 0.5) }}>HELD-OUT RUNS, NEVER SEEN IN DEVELOPMENT</div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 70, marginTop: 20 }}>
        <div style={{ textAlign: "center" }}>
          <div style={{ fontSize: 260, fontWeight: 880, lineHeight: 1, fontVariantNumeric: "tabular-nums", letterSpacing: "-0.04em",
            textShadow: `0 0 60px rgba(91,124,255,.75)` }}><Counter to={60} t={t} start={0.3} />/60</div>
          <div style={{ fontSize: 34, fontWeight: 700, color: BLUE }}>EIDOS</div>
        </div>
        <div style={{ textAlign: "center", opacity: ramp(t, 1.2, 1.8) }}>
          <div style={{ fontSize: 120, fontWeight: 800, lineHeight: 1, color: "#ff6b81", opacity: 0.85 }}>4/60</div>
          <div style={{ fontSize: 28, fontWeight: 600, color: "#9aa6c4" }}>copying the clicks</div>
        </div>
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: "50%", height: 2, background: "linear-gradient(90deg, transparent, #7d95ff, transparent)",
        transform: `scaleX(${ramp(t, 0.2, 1.4)})`, opacity: 0.5 - ramp(t, 1.4, 2.2) * 0.5 }} />
    </AbsoluteFill>
  );
};

export const StyleDark: React.FC = () => {
  const t = useT();
  return (
    <AbsoluteFill>
      <DarkBg t={t} />
      <Sequence durationInFrames={100}><DarkTitle /></Sequence>
      <Sequence from={100} durationInFrames={120}><DarkApp /></Sequence>
      <Sequence from={220}><DarkResult /></Sequence>
      <Flash at={[100 / 30, 220 / 30]} t={t} color="rgba(120,150,255,.5)" />
    </AbsoluteFill>
  );
};

const Flash: React.FC<{ at: number[]; t: number; color: string }> = ({ at, t, color }) => (
  <AbsoluteFill style={{ pointerEvents: "none", background: color, opacity: Math.max(0, ...at.map((a) => 1 - Math.abs(t - a) / 0.12)) * 0.6, mixBlendMode: "screen" }} />
);

/* ------------------------------------------------------------------ style 2: product launch */

const Mesh: React.FC<{ t: number }> = ({ t }) => {
  const blobs: [string, number, number, number, number][] = [
    ["#3b5bff", 20, 30, 900, 0], ["#9b5cff", 75, 25, 820, 1.7], ["#ff7a59", 65, 80, 760, 3.1], ["#20d3ff", 15, 85, 700, 4.4],
  ];
  return (
    <AbsoluteFill style={{ background: "#f6f4ff", overflow: "hidden" }}>
      {blobs.map(([c, x, y, r, ph], i) => (
        <div key={i} style={{ position: "absolute", width: r, height: r, borderRadius: "50%", background: c, filter: "blur(140px)", opacity: 0.55,
          left: `calc(${x + Math.sin(t * 0.5 + ph) * 8}% - ${r / 2}px)`, top: `calc(${y + Math.cos(t * 0.4 + ph) * 8}% - ${r / 2}px)` }} />
      ))}
      <AbsoluteFill style={{ background: "linear-gradient(180deg, rgba(255,255,255,.35), rgba(255,255,255,0) 40%)" }} />
    </AbsoluteFill>
  );
};

const INK = "#0d0f1a";
const LaunchTitle: React.FC = () => {
  const t = useT();
  const { fps } = useVideoConfig();
  const f = useCurrentFrame();
  const sc = spring({ frame: f, fps, config: { damping: 200 }, durationInFrames: 60 });
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", fontFamily: FONT, color: INK }}>
      <div style={{ fontFamily: FONT, fontSize: 30, fontWeight: 700, padding: "8px 18px", borderRadius: 999, background: "rgba(255,255,255,.7)",
        boxShadow: "0 10px 30px -12px rgba(40,30,120,.35)", opacity: ramp(t, 0.1, 0.6), transform: `translateY(${(1 - ramp(t, 0.1, 0.6)) * 20}px)` }}>Introducing EIDOS</div>
      <div style={{ fontSize: 230, fontWeight: 880, letterSpacing: "-0.05em", lineHeight: 1, marginTop: 30, transform: `scale(${1.08 - sc * 0.08})` }}>
        <Words text="Show it once." t={t} start={0.35} step={0.12} />
      </div>
      <div style={{ fontSize: 40, fontWeight: 500, color: "#3a3f5c", marginTop: 26, opacity: ramp(t, 1.5, 2.1) }}>
        It learns the skill. And checks its own work.
      </div>
    </AbsoluteFill>
  );
};

const LaunchApp: React.FC = () => {
  const t = useT();
  const { fps } = useVideoConfig();
  const f = useCurrentFrame();
  const W = 1200, H = 760;
  const up = spring({ frame: f, fps, config: { damping: 18, mass: 0.9 } });
  const dolly = ramp(t, 0.4, 3.8);
  const ok = t > 2.6;
  const pill = spring({ frame: f - 1.3 * fps, fps, config: { damping: 12 } });
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", perspective: 2400 }}>
      <div style={{ transform: `translateY(${(1 - up) * 300}px) rotateX(${(1 - dolly) * 14}deg) scale(${1.0 + dolly * 0.12})`, borderRadius: 26, overflow: "hidden",
        background: "#fff", boxShadow: "0 60px 140px -40px rgba(40,20,120,.55), 0 0 0 1px rgba(20,20,60,.08)" }}>
        <div style={{ height: 52, display: "flex", alignItems: "center", gap: 10, padding: "0 20px", background: "#f3f2f8", borderBottom: "1px solid #e4e2ee" }}>
          {["#ff5f57", "#febc2e", "#28c840"].map((c) => <span key={c} style={{ width: 14, height: 14, borderRadius: 7, background: c }} />)}
          <div style={{ marginLeft: 20, flex: 1, maxWidth: 520, height: 30, borderRadius: 15, background: "#fff", fontFamily: FONT, fontSize: 16, color: "#6b6f86", display: "flex", alignItems: "center", padding: "0 14px" }}>mail.postwise.app</div>
        </div>
        <div style={{ position: "relative", width: W, height: H }}>
          <Video src={staticFile("clips/tutorial_mail.mp4")} trimBefore={Math.round(3.9 * 30)} muted style={{ width: W, height: H }} />
          <div style={{ position: "absolute", left: BOX[0] - 6, top: BOX[1] - 6, width: BOX[2] + 12, height: BOX[3] + 12, borderRadius: 12,
            border: `3px solid ${ok ? "#12b886" : "#5b5bff"}`, boxShadow: `0 0 0 ${8 * pill}px ${ok ? "rgba(18,184,134,.18)" : "rgba(91,91,255,.18)"}`, opacity: ramp(t, 1.1, 1.4) }} />
          <div style={{ position: "absolute", left: BOX[0] + BOX[2] + 24, top: BOX[1] - 8, transform: `scale(${pill})`, transformOrigin: "left center",
            fontFamily: FONT, fontSize: 22, fontWeight: 700, padding: "12px 18px", borderRadius: 16, color: "#fff", whiteSpace: "nowrap",
            background: ok ? "linear-gradient(135deg, #12b886, #0ca678)" : "linear-gradient(135deg, #5b5bff, #8b5cf6)", boxShadow: "0 14px 30px -10px rgba(60,40,200,.5)" }}>
            {ok ? "✓ Checked: To shows the address" : "Type {to} into “To”"}
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

const LaunchResult: React.FC = () => {
  const t = useT();
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", fontFamily: FONT, color: INK, textAlign: "center" }}>
      <div style={{ fontSize: 44, fontWeight: 600, color: "#3a3f5c", opacity: ramp(t, 0.1, 0.5) }}>Held-out runs it had never seen</div>
      <div style={{ fontSize: 330, fontWeight: 900, letterSpacing: "-0.06em", lineHeight: 1, fontVariantNumeric: "tabular-nums",
        background: "linear-gradient(120deg, #3b5bff, #9b5cff 55%, #ff7a59)", WebkitBackgroundClip: "text", color: "transparent",
        transform: `scale(${0.9 + ramp(t, 0.2, 1.2) * 0.1})` }}>
        <Counter to={60} t={t} start={0.2} />/60
      </div>
      <div style={{ display: "flex", gap: 18, justifyContent: "center", marginTop: 10, opacity: ramp(t, 1.3, 1.9), transform: `translateY(${(1 - ramp(t, 1.3, 1.9)) * 20}px)` }}>
        <span style={{ fontSize: 30, fontWeight: 700, padding: "12px 24px", borderRadius: 999, background: "#fff", boxShadow: "0 12px 30px -14px rgba(40,30,120,.4)" }}>EIDOS 60/60</span>
        <span style={{ fontSize: 30, fontWeight: 600, padding: "12px 24px", borderRadius: 999, background: "rgba(255,255,255,.55)", color: "#6b6f86" }}>Copying the clicks 4/60</span>
      </div>
    </AbsoluteFill>
  );
};

export const StyleLaunch: React.FC = () => {
  const t = useT();
  return (
    <AbsoluteFill>
      <Mesh t={t} />
      <Sequence durationInFrames={100}><LaunchTitle /></Sequence>
      <Sequence from={100} durationInFrames={120}><LaunchApp /></Sequence>
      <Sequence from={220}><LaunchResult /></Sequence>
    </AbsoluteFill>
  );
};
