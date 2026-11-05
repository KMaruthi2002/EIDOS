// EIDOS, version 8: restrained and premium. Short on-screen words that never repeat the narration,
// one accent colour, footage framed or used as texture, sharp hero stills for the big moments,
// no decorative glow, no rotated stamps, no captions.
import React from "react";
import { AbsoluteFill, Img, interpolate, Sequence, spring, staticFile, useCurrentFrame } from "remotion";
import { Audio, Video } from "@remotion/media";
import { TransitionSeries, linearTiming } from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";
import { FONT, ease } from "./ui";
import timeline from "./timeline8.json";
import timing from "./v8_timing.json";
import sent from "./v8_sent.json";
import world from "./world_data.json";

const FPS = 30, W = 1920, H = 1080, BAR = 84;
const INK = "#060709", WHITE = "#f3f4f8", DIM = "rgba(243,244,248,.55)", LINE = "rgba(243,244,248,.14)";
const CYAN = "#1ee3ff", COBALT = "#2a5bff", RED = "#ff2d46", GREEN = "#2bf0a6";
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const useT = () => useCurrentFrame() / FPS;
const ramp = (t: number, a: number, b: number) => interpolate(t, [a, b], [0, 1], { ...clamp, easing: ease });
const lin = (t: number, a: number, b: number) => interpolate(t, [a, b], [0, 1], clamp);
const sp = (f: number, at: number, cfg: { damping?: number; mass?: number; stiffness?: number } = {}) =>
  spring({ frame: f - at * FPS, fps: FPS, config: { damping: 100, stiffness: 200, mass: 0.5, ...cfg } });
const rnd = (i: number, k = 0) => { const x = Math.sin(i * 127.1 + k * 311.7) * 43758.5453; return x - Math.floor(x); };
const LEAD = timing.lead;
const VO = (id: string) => timeline.find((s) => s.id === id)!;
const S = (id: string, k: number) => LEAD + (sent as any)[id][k];
const shake = (t: number, at: number, amp = 10, dur = 0.4) => (t > at && t < at + dur ? Math.sin((t - at) * 95) * amp * (1 - lin(t, at, at + dur)) : 0);
const fill = (s: string) => s.replace(/\{(\w+)\}/g, (_: string, n: string) => String((world as any).inputs?.[n] ?? n));

/* ------------------------------------------------------------------ film layer */

const Film: React.FC = () => {
  const t = useT();
  return (
    <>
      <AbsoluteFill style={{ backgroundImage: `url(${staticFile("noise.png")})`, backgroundSize: 460, backgroundPosition: `${(t * 113) % 460}px ${(t * 71) % 460}px`, opacity: 0.06, mixBlendMode: "overlay", pointerEvents: "none" }} />
      <AbsoluteFill style={{ background: "radial-gradient(85% 75% at 50% 50%, transparent 60%, rgba(0,0,0,.55))", pointerEvents: "none" }} />
      <div style={{ position: "absolute", left: 0, right: 0, top: 0, height: BAR, background: INK }} />
      <div style={{ position: "absolute", left: 0, right: 0, bottom: 0, height: BAR, background: INK }} />
    </>
  );
};

const Flash: React.FC<{ at: number; dur?: number; color?: string; max?: number }> = ({ at, dur = 0.2, color = "#fff", max = 0.9 }) => {
  const t = useT();
  const o = t >= at && t < at + dur ? 1 - lin(t, at, at + dur) : 0;
  return o > 0 ? <AbsoluteFill style={{ background: color, opacity: o * max }} /> : null;
};

/* a hero still with a slow drift, dimmed */
const Still: React.FC<{ src: string; dim?: number; drift?: number; zoom?: number; from?: number }> = ({ src, dim = 0.45, drift = 1, zoom = 0.05, from = 0 }) => {
  const t = useT() - from;
  return (
    <AbsoluteFill style={{ overflow: "hidden", background: INK }}>
      <Img src={staticFile(src)} style={{ position: "absolute", width: "108%", height: "108%", left: "-4%", top: "-4%", objectFit: "cover", transform: `scale(${1 + zoom * lin(t, 0, 14)}) translate(${-t * 2 * drift}px, ${t * 0.8 * drift}px)`, filter: "saturate(.85)" }} />
      <AbsoluteFill style={{ background: `rgba(6,7,9,${dim})` }} />
    </AbsoluteFill>
  );
};

/* text that is revealed by a mask from below, then sits still */
const Reveal: React.FC<{ at: number; children: React.ReactNode; delay?: number; style?: React.CSSProperties; out?: number }> = ({ at, children, style, out }) => {
  const f = useCurrentFrame(); const t = useT();
  const p = sp(f, at);
  const o = out != null ? 1 - ramp(t, out, out + 0.35) : 1;
  return (
    <div style={{ overflow: "hidden", ...style }}>
      <div style={{ transform: `translateY(${(1 - p) * 105}%)`, opacity: o }}>{children}</div>
    </div>
  );
};

const Head: React.FC<{ text: string; at: number; size?: number; weight?: number; color?: string; out?: number; align?: "left" | "center"; style?: React.CSSProperties }> = ({ text, at, size = 88, weight = 760, color = WHITE, out, align = "center", style }) => (
  <div style={{ display: "flex", flexDirection: "column", alignItems: align === "center" ? "center" : "flex-start", ...style }}>
    {text.split("\n").map((line, i) => (
      <Reveal key={i} at={at + i * 0.08} out={out}>
        <div style={{ fontFamily: FONT, fontSize: size, fontWeight: weight, letterSpacing: "-0.035em", lineHeight: 1.08, color, textAlign: align, padding: "0 0.05em" }}>{line}</div>
      </Reveal>
    ))}
  </div>
);

const Label: React.FC<{ at: number; children: React.ReactNode; color?: string; out?: number; style?: React.CSSProperties }> = ({ at, children, color = WHITE, out, style }) => {
  const f = useCurrentFrame(); const t = useT();
  const p = sp(f, at); const o = out != null ? 1 - ramp(t, out, out + 0.3) : 1;
  return (
    <div style={{ display: "inline-flex", alignItems: "center", gap: 10, fontFamily: FONT, fontSize: 20, fontWeight: 650, letterSpacing: "0.01em", color, padding: "9px 14px", borderRadius: 8, border: `1px solid ${color === WHITE ? LINE : color + "88"}`, background: "rgba(6,7,9,.55)", backdropFilter: "blur(8px)", opacity: Math.min(1, p * 1.4) * o, transform: `translateY(${(1 - p) * 14}px)`, whiteSpace: "nowrap", ...style }}>{children}</div>
  );
};

const Rule: React.FC<{ at: number; width?: number; style?: React.CSSProperties }> = ({ at, width = 120, style }) => {
  const t = useT();
  return <div style={{ height: 2, width, background: CYAN, transform: `scaleX(${ramp(t, at, at + 0.6)})`, transformOrigin: "left", ...style }} />;
};

const Ants: React.FC<{ color: string; draw?: number; width?: number; radius?: number }> = ({ color, draw = 1, width = 3, radius = 14 }) => {
  const t = useT();
  return (
    <svg width="100%" height="100%" style={{ position: "absolute", inset: 0, overflow: "visible" }}>
      <rect x={0} y={0} width="100%" height="100%" rx={radius} fill="none" stroke={color} strokeWidth={width} pathLength={100} strokeDasharray={draw < 1 ? `${100 * draw} 100` : "1.6 1.0"} strokeDashoffset={draw < 1 ? 0 : -t * 2.5} />
    </svg>
  );
};

const Frame: React.FC<{ w: number; h: number; children: React.ReactNode; style?: React.CSSProperties; radius?: number }> = ({ w, h, children, style, radius = 18 }) => (
  <div style={{ position: "relative", width: w, height: h, borderRadius: radius, overflow: "hidden", background: "#000", boxShadow: `0 0 0 1px rgba(255,255,255,.14), 0 60px 110px -50px rgba(0,0,0,.95)`, ...style }}>{children}</div>
);

const Clip: React.FC<{ src: string; w: number; h: number; rate?: number; from?: number }> = ({ src, w, h, rate = 1, from = 0 }) => (
  <Video src={staticFile(`clips/${src}.mp4`)} muted playbackRate={rate} trimBefore={Math.round(from * FPS)} style={{ width: w, height: h, display: "block", objectFit: "cover", filter: "contrast(1.06) saturate(.92)" }} />
);

const Scan: React.FC<{ period?: number }> = ({ period = 3.2 }) => {
  const t = useT(); const y = (t / period) % 1;
  return <div style={{ position: "absolute", left: 0, right: 0, top: `${y * 100}%`, height: 1.5, background: CYAN, opacity: 0.8, boxShadow: `0 0 12px ${CYAN}` }} />;
};

const Logo: React.FC<{ at: number; size?: number; still?: string }> = ({ at, size = 220, still }) => {
  const t = useT(); const f = useCurrentFrame();
  const solid = still ? ramp(t, at + 1.5, at + 2.1) : 1;
  const letters = (color: string, extra?: React.CSSProperties) => (
    <div style={{ display: "flex", fontFamily: FONT, fontSize: size, fontWeight: 800, letterSpacing: "0.1em", fontVariationSettings: '"wdth" 125', lineHeight: 1, color, ...extra }}>
      {"EIDOS".split("").map((l, i) => { const s = sp(f, at + i * 0.06, { damping: 18, stiffness: 120, mass: 0.8 }); return <span key={i} style={{ display: "inline-block", transform: `translateY(${(1 - s) * 60}px)`, opacity: s }}>{l}</span>; })}
    </div>
  );
  return (
    <div style={{ position: "relative", padding: `${size * 0.12}px ${size * 0.26}px` }}>
      <Ants color={CYAN} draw={ramp(t, at + 0.3, at + 1.4)} width={3} radius={size * 0.08} />
      <div style={{ position: "relative" }}>
        {still && solid < 1 && (
          <div style={{ position: "absolute", inset: -12, overflow: "hidden", opacity: 1 - solid }}>
            <Img src={staticFile(still)} style={{ width: "100%", height: "100%", objectFit: "cover", transform: `scale(${1.15 - 0.1 * lin(t, at, at + 2)})` }} />
            <AbsoluteFill style={{ background: "#000", mixBlendMode: "multiply", alignItems: "center", justifyContent: "center", padding: 12 }}>{letters("#fff")}</AbsoluteFill>
          </div>
        )}
        {letters(WHITE, { opacity: solid })}
      </div>
    </div>
  );
};

const Cam: React.FC<{ children: React.ReactNode; push?: number; shakeAt?: number; amp?: number }> = ({ children, push = 0.03, shakeAt, amp = 10 }) => {
  const t = useT(); const sx = shakeAt != null ? shake(t, shakeAt, amp) : 0;
  return <AbsoluteFill style={{ transform: `scale(${1 + push * lin(t, 0, 14)}) translate(${sx}px, ${sx * 0.5}px)` }}>{children}</AbsoluteFill>;
};

/* ------------------------------------------------------------------ 1. hook */

const CUTS: [string, string, string, number][] = [["Cooking", "hero/kitchen.jpg", "tomato_demo", 0], ["Fixing", "hero/cabinet.jpg", "cabinet_power_on", 0], ["Building", "hero/pc.jpg", "gpu_demo", 0]];
const Hook: React.FC = () => {
  const t = useT(); const f = useCurrentFrame();
  const s1 = S("hook", 1), cutsAt = [S("hook", 2), S("hook", 3), S("hook", 4)], s5 = S("hook", 5);
  const cardsAt = s5 + 0.2, flipAt = s5 + 4.2, endAt = timing.durations[0];
  return (
    <AbsoluteFill style={{ background: INK }}>
      {t < cutsAt[0] && <Still src="hero/workshop.jpg" dim={0.5} />}
      {/* dot and first line */}
      {t < s1 + 0.5 && (
        <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
          <div style={{ width: 10, height: 10, borderRadius: 5, background: CYAN, opacity: ramp(t, 0.2, 0.7) * (1 - ramp(t, s1, s1 + 0.4)), transform: `scale(${1 + 0.15 * Math.sin(t * 5)})` }} />
          <div style={{ marginTop: 26, opacity: 1 - ramp(t, s1, s1 + 0.3) }}><Head text="A thought." at={0.5} size={48} weight={600} color={DIM} /></div>
        </AbsoluteFill>
      )}
      {/* a wall of real clips, as texture, behind two short lines */}
      {t >= s1 - 0.2 && t < cutsAt[0] && (
        <AbsoluteFill style={{ perspective: 1600 }}>
          {Array.from({ length: 12 }, (_, i) => {
            const col = i % 4, row = Math.floor(i / 4); const s = sp(f, s1 + i * 0.05, { damping: 22, stiffness: 90 });
            return <div key={i} style={{ position: "absolute", left: 100 + col * 445 + (row % 2) * 60, top: 130 + row * 275, width: 380, height: 232, borderRadius: 10, overflow: "hidden", transform: `translateZ(${(1 - s) * -700}px)`, opacity: s * 0.55 }}>
              <Img src={staticFile(`thumbs/w${i}.jpg`)} style={{ width: "100%", height: "100%", objectFit: "cover", filter: "saturate(.6) brightness(.7)" }} />
            </div>;
          })}
          <AbsoluteFill style={{ background: "linear-gradient(180deg, rgba(6,7,9,.2), rgba(6,7,9,.75))" }} />
          <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
            <Head text="Millions of people" at={s1 + 0.2} size={64} weight={600} color={DIM} />
            <Head text="filming how things are done." at={s1 + 0.5} size={92} />
          </AbsoluteFill>
        </AbsoluteFill>
      )}
      {/* three cuts: sharp stills with a single word, then the real clip in a frame */}
      {CUTS.map(([word, still, clip], i) => {
        const at = cutsAt[i], end = i < 2 ? cutsAt[i + 1] : cardsAt; if (t < at || t >= end) return null;
        return <AbsoluteFill key={word}>
          <Still src={still} dim={0.3} zoom={0.08} from={at} />
          <div style={{ position: "absolute", left: 110, bottom: 150 }}>
            <Rule at={at + 0.05} />
            <Head text={word} at={at + 0.1} size={150} weight={800} align="left" style={{ marginTop: 18 }} />
          </div>
          <div style={{ position: "absolute", right: 110, top: 150, opacity: ramp(t, at + 0.6, at + 1.0) }}>
            <Frame w={420} h={236} radius={12}><Clip src={clip} w={420} h={236} rate={1.3} from={[4, 22, 34][i]} /><Scan /></Frame>
          </div>
          <Flash at={at} dur={0.14} max={0.7} />
        </AbsoluteFill>;
      })}
      {/* one card, flipped */}
      {t >= cardsAt && (
        <AbsoluteFill style={{ background: INK, alignItems: "center", justifyContent: "center", perspective: 1800 }}>
          <Still src="hero/workshop.jpg" dim={0.75} from={cardsAt} />
          {CUTS.map(([, , clip], i) => {
            const gather = ramp(t, cardsAt + 1.4, cardsAt + 2.2), s = sp(f, cardsAt + 0.1 + i * 0.08, { damping: 20, stiffness: 120 });
            const keep = i === 0; if (!keep && gather >= 1) return null;
            const x = (i - 1) * 520 * (1 - gather), flip = ramp(t, flipAt, flipAt + 0.8), shrink = ramp(t, endAt - 1.0, endAt - 0.4);
            return <div key={clip} style={{ position: "absolute", width: 480, height: 276, left: W / 2 - 240, top: H / 2 - 138 - 60, transform: `translateX(${x}px) scale(${(0.8 + 0.2 * s) * (1 - shrink)}) rotateY(${keep ? flip * 180 : 0}deg)`, opacity: Math.min(1, s * 1.5) * (keep ? 1 : 1 - gather), transformStyle: "preserve-3d" }}>
              <div style={{ position: "absolute", inset: 0, borderRadius: 14, overflow: "hidden", backfaceVisibility: "hidden", boxShadow: "0 0 0 1px rgba(255,255,255,.16), 0 40px 80px -30px rgba(0,0,0,.9)" }}><Clip src={clip} w={480} h={276} rate={1.2} from={[8, 28, 40][i]} /></div>
              <div style={{ position: "absolute", inset: 0, borderRadius: 14, backfaceVisibility: "hidden", transform: "rotateY(180deg)", background: "#0c0e14", padding: "20px 22px", display: "grid", gap: 9, alignContent: "start", boxShadow: `0 0 0 1px ${CYAN}66` }}>
                {world.steps.slice(0, 5).map((st, j) => <div key={st.id} style={{ display: "flex", gap: 12, alignItems: "center", fontFamily: FONT, fontSize: 17, fontWeight: 600, color: WHITE, opacity: ramp(t, flipAt + 0.55 + j * 0.1, flipAt + 0.8 + j * 0.1) }}>
                  <span style={{ fontFamily: FONT, fontSize: 13, fontWeight: 700, color: CYAN, width: 18 }}>{st.id}</span><span style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{fill(st.do)}</span>
                </div>)}
              </div>
            </div>;
          })}
          <div style={{ position: "absolute", top: 720, left: 0, right: 0, display: "grid", justifyItems: "center", gap: 10, opacity: 1 - ramp(t, endAt - 1.0, endAt - 0.5) }}>
            <Head text="Just one video." at={cardsAt + 1.5} size={56} weight={600} color={DIM} />
            <Head text="A skill it can check." at={flipAt + 0.3} size={72} />
          </div>
        </AbsoluteFill>
      )}
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ 2. name */

const Name: React.FC = () => {
  const t = useT();
  return (
    <AbsoluteFill style={{ background: INK }}>
      <Still src="hero/workshop.jpg" dim={0.7} />
      <Flash at={0} dur={0.25} max={0.8} />
      {[0, 0.2].map((d, i) => { const p = lin(t, d, d + 1.3); return <div key={i} style={{ position: "absolute", left: W / 2, top: H / 2 - 20, width: 40 + p * 2400, height: 40 + p * 2400, borderRadius: "50%", transform: "translate(-50%,-50%)", border: `${2 - 1.5 * p}px solid ${CYAN}`, opacity: (1 - p) * 0.6 }} />; })}
      <Cam push={0.02} shakeAt={0.02} amp={6}>
        <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
          <Logo at={0.05} still="hero/kitchen.jpg" />
          <div style={{ marginTop: 34 }}><Head text="Show it once." at={S("name", 1)} size={50} weight={600} color={DIM} /></div>
        </AbsoluteFill>
      </Cam>
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ 3. learn */

const Learn: React.FC = () => {
  const t = useT(); const f = useCurrentFrame();
  const VW = 880, VH = 495;
  const s = sp(f, 0.2, { damping: 24, stiffness: 110 });
  const listAt = S("learn", 1) + 0.3, recipeAt = S("learn", 2);
  return (
    <AbsoluteFill style={{ background: INK }}>
      <Still src="hero/kitchen.jpg" dim={0.8} />
      <Cam push={0.02}>
        <div style={{ position: "absolute", left: 110, top: 150 }}>
          <Rule at={0.3} />
          <Head text="It watches." at={0.4} size={60} align="left" style={{ marginTop: 16 }} />
        </div>
        <div style={{ position: "absolute", left: 110, top: 300, transform: `translateY(${(1 - s) * 60}px)`, opacity: s }}>
          <Frame w={VW} h={VH}>
            <Clip src="tomato_demo" w={VW} h={VH} rate={1.5} />
            <Scan />
            <div style={{ position: "absolute", left: 18, top: 16 }}><Label at={0.8}><span style={{ width: 8, height: 8, borderRadius: 4, background: CYAN }} />one frame a second</Label></div>
          </Frame>
        </div>
        <div style={{ position: "absolute", left: 1090, top: 150, width: 720 }}>
          <Rule at={listAt - 0.3} />
          <Head text="It writes the recipe." at={listAt - 0.2} size={60} align="left" style={{ marginTop: 16 }} />
          <div style={{ marginTop: 30, display: "grid" }}>
            {world.steps.slice(0, 9).map((st, i) => {
              const at = listAt + 0.5 + i * 0.26, p = sp(f, at, { damping: 20, stiffness: 150 }), done = t > at + 0.5;
              return <div key={st.id} style={{ display: "flex", alignItems: "center", gap: 16, padding: "11px 0", borderBottom: `1px solid ${LINE}`, transform: `translateX(${(1 - p) * 40}px)`, opacity: p }}>
                <span style={{ fontFamily: FONT, fontSize: 15, fontWeight: 700, color: CYAN, width: 22 }}>{String(st.id).padStart(2, "0")}</span>
                <span style={{ fontFamily: FONT, fontSize: 23, fontWeight: 600, color: WHITE, flex: 1, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{fill(st.do)}</span>
                <svg width="18" height="18" viewBox="0 0 18 18" style={{ opacity: done ? ramp(t, at + 0.5, at + 0.7) : 0 }}><path d="M3 9.5l4 4 8-8" fill="none" stroke={GREEN} strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" /></svg>
              </div>;
            })}
          </div>
          <div style={{ marginTop: 22 }}>{t > recipeAt && <Label at={recipeAt} color={DIM}>steps · order · what done looks like</Label>}</div>
        </div>
      </Cam>
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ 4-5. live, alert */

const PW = 420, PH = 840;
const Phone: React.FC<{ from: number; rate: number; tilt?: number; shake?: number; glitch?: number; children?: React.ReactNode }> = ({ from, rate, tilt = -10, shake: sh = 0, glitch = 0, children }) => {
  const iw = PW - 24, ih = PH - 24, vw = Math.round(ih * 16 / 9);
  const vid = (extra?: React.CSSProperties, k?: string) => (
    <div key={k} style={{ position: "absolute", inset: 0, ...extra }}>
      <Video src={staticFile("clips/cabinet_power_on.mp4")} muted playbackRate={rate} trimBefore={Math.round(from * FPS)} style={{ width: vw, height: ih, display: "block", marginLeft: -Math.round((vw - iw) / 2), filter: "contrast(1.06) saturate(.9)" }} />
    </div>
  );
  return (
    <div style={{ transform: `perspective(2200px) rotateY(${tilt}deg) rotateX(2deg) translate(${sh}px, ${sh * 0.5}px)` }}>
      <div style={{ position: "relative", width: PW, height: PH, borderRadius: 50, background: "linear-gradient(160deg, #1b1e28, #08090e)", padding: 12, boxShadow: `0 0 0 1.5px rgba(255,255,255,.22), 0 80px 140px -40px rgba(0,0,0,.95)` }}>
        <div style={{ position: "relative", width: iw, height: ih, borderRadius: 40, overflow: "hidden", background: "#000" }}>
          {vid()}
          {glitch > 0 && <>
            {vid({ clipPath: "inset(20% 0 60% 0)", transform: `translateX(${glitch * 22}px)`, filter: "hue-rotate(150deg)", mixBlendMode: "screen", opacity: 0.85 }, "g1")}
            {vid({ clipPath: "inset(58% 0 18% 0)", transform: `translateX(${-glitch * 28}px)`, filter: "hue-rotate(-80deg)", mixBlendMode: "screen", opacity: 0.85 }, "g2")}
          </>}
          <div style={{ position: "absolute", left: "50%", top: 12, width: 108, height: 30, borderRadius: 15, background: "#000", transform: "translateX(-50%)" }} />
          {children}
        </div>
      </div>
    </div>
  );
};

const HUD: React.FC<{ step: string; next: string; n: number; of: number; danger?: boolean }> = ({ step, next, n, of, danger }) => {
  const t = useT();
  return (
    <>
      <div style={{ position: "absolute", left: 16, top: 56, display: "flex", alignItems: "center", gap: 8, fontFamily: FONT, fontSize: 14, fontWeight: 700, color: "#fff", background: "rgba(6,7,9,.7)", padding: "6px 11px", borderRadius: 999 }}>
        <span style={{ width: 8, height: 8, borderRadius: 4, background: RED, opacity: 0.5 + 0.5 * Math.abs(Math.sin(t * 3.5)) }} />LIVE
      </div>
      <div style={{ position: "absolute", left: 16, right: 16, top: 98, display: "flex", gap: 4 }}>
        {Array.from({ length: of }, (_, i) => <div key={i} style={{ flex: 1, height: 3, borderRadius: 2, background: i < n - 1 ? (danger ? RED : GREEN) : i === n - 1 ? CYAN : "rgba(255,255,255,.22)", opacity: i === n - 1 ? 0.6 + 0.4 * Math.sin(t * 4) : 1 }} />)}
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, bottom: 0, padding: "40px 16px 20px", background: "linear-gradient(180deg, transparent, rgba(0,0,0,.85))", display: "grid", gap: 8 }}>
        <div style={{ fontFamily: FONT, fontSize: 13, fontWeight: 700, color: danger ? RED : CYAN, letterSpacing: "0.06em" }}>STEP {n} OF {of}</div>
        <div style={{ fontFamily: FONT, fontSize: 22, fontWeight: 700, color: "#fff", lineHeight: 1.15 }}>{step}</div>
        <div style={{ fontFamily: FONT, fontSize: 15, fontWeight: 650, color: "#fff", background: danger ? RED : COBALT, padding: "8px 12px", borderRadius: 10, justifySelf: "start" }}>{danger ? "First: " : "Next: "}{next}</div>
      </div>
    </>
  );
};

const Live: React.FC = () => {
  const t = useT(); const f = useCurrentFrame();
  const s = sp(f, 0.2, { damping: 22, stiffness: 100 });
  const camAt = S("live", 1), knowAt = S("live", 2);
  return (
    <AbsoluteFill style={{ background: INK }}>
      <Still src="hero/phone.jpg" dim={0.72} />
      <Cam push={0.02}>
        <div style={{ position: "absolute", left: 360, top: 120, transform: `translateY(${(1 - s) * 300}px)`, opacity: s }}>
          <Phone from={6} rate={1.5}><HUD step="Open the cabinet door" next="Remove the old component" n={2} of={7} /></Phone>
        </div>
        <div style={{ position: "absolute", left: 960, top: 300, width: 860 }}>
          <Rule at={0.3} />
          <Head text="It watches you." at={0.4} size={92} align="left" style={{ marginTop: 16 }} />
          <Head text="Any camera." at={camAt} size={60} weight={600} color={DIM} align="left" style={{ marginTop: 10 }} />
          <div style={{ marginTop: 40, display: "flex", gap: 12 }}>
            {t > knowAt && <Label at={knowAt}>which step you're on</Label>}
            {t > knowAt + 0.8 && <Label at={knowAt + 0.8}>what comes next</Label>}
          </div>
        </div>
      </Cam>
    </AbsoluteFill>
  );
};

const Alert: React.FC = () => {
  const t = useT();
  const hit = S("alert", 1) - 0.15, then = S("alert", 2), after = S("alert", 3);
  const g = t > hit && t < hit + 0.35 ? (1 - lin(t, hit, hit + 0.35)) * (0.5 + 0.5 * Math.abs(Math.sin(t * 90))) : 0;
  const red = t > hit ? (0.6 + 0.4 * Math.abs(Math.sin((t - hit) * 4))) * (1 - 0.6 * lin(t, hit + 1.5, hit + 4)) : 0;
  const tension = lin(t, 0.3, hit);
  return (
    <AbsoluteFill style={{ background: INK }}>
      <Still src="hero/phone.jpg" dim={0.72 + 0.2 * tension} />
      <AbsoluteFill style={{ background: `radial-gradient(70% 70% at 50% 50%, transparent 30%, ${RED})`, opacity: red * 0.35 }} />
      <Cam push={0.015} shakeAt={hit} amp={16}>
        <div style={{ position: "absolute", left: 360, top: 120, filter: `saturate(${1 - 0.6 * tension})` }}>
          <Phone from={19} rate={1.2} glitch={g}>
            <HUD step="Removing the old component" next="Turn the power OFF" n={3} of={7} danger={t > hit} />
            {t > hit && <div style={{ position: "absolute", inset: 0, boxShadow: `inset 0 0 0 4px ${RED}`, borderRadius: 40, opacity: 0.5 + 0.5 * Math.abs(Math.sin((t - hit) * 6)) }} />}
          </Phone>
        </div>
        <div style={{ position: "absolute", left: 960, top: 300, width: 860 }}>
          <div style={{ opacity: 1 - ramp(t, hit - 0.15, hit) }}><Head text="Miss a step?" at={0.4} size={76} weight={600} color={DIM} align="left" /></div>
          {t > hit && <div style={{ position: "absolute", left: 0, top: 0 }}>
            <Rule at={hit} width={160} style={{ background: RED }} />
            <Head text="It stops you." at={hit + 0.05} size={104} align="left" style={{ marginTop: 16 }} />
            <div style={{ marginTop: 28, display: "flex", gap: 12 }}>
              {t > then && <Label at={then} color={RED}>right then</Label>}
              {t > after && <Label at={after}>not after</Label>}
            </div>
          </div>}
        </div>
      </Cam>
      <Flash at={hit} dur={0.1} color={RED} max={0.5} />
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ 6. robot */

const Robot: React.FC = () => {
  const t = useT(); const f = useCurrentFrame();
  const VW = 1400, VH = 788;
  const cutB = 8.5, cutC = 11.0, knock = S("robot", 2) + 0.3, noticed = knock + 1.1, fixed = S("robot", 3) + 0.6;
  const s = sp(f, 0.1, { damping: 24, stiffness: 100 });
  return (
    <AbsoluteFill style={{ background: INK }}>
      <Still src="hero/robot.jpg" dim={0.7} />
      <div style={{ position: "absolute", left: 110, top: 128 }}><Rule at={0.3} /><Head text="Not just for people." at={0.4} size={56} align="left" style={{ marginTop: 14 }} /></div>
      <Cam push={0.02} shakeAt={knock} amp={12}>
        <div style={{ position: "absolute", left: (W - VW) / 2, top: 236, transform: `translateY(${(1 - s) * 60}px)`, opacity: s }}>
          <Frame w={VW} h={VH} style={{ boxShadow: `0 0 0 1px ${t > fixed ? GREEN : "rgba(255,255,255,.14)"}, 0 60px 110px -50px rgba(0,0,0,.95)` }}>
            <div style={{ transform: "scale(1.17)", transformOrigin: "50% 50%" }}>
            {t < cutB && <Clip src="robot_demo" w={VW} h={VH} rate={2.5} from={2} />}
            {t >= cutB && t < cutC && <Sequence from={Math.round(cutB * FPS)} layout="none"><Clip src="robot_eidos" w={VW} h={VH} rate={1} from={19.5} /></Sequence>}
            {t >= cutC && <Sequence from={Math.round(cutC * FPS)} layout="none"><Clip src="robot_eidos" w={VW} h={VH} rate={12} from={23.5} /></Sequence>}
            </div>
            <div style={{ position: "absolute", right: 20, top: 18 }}><Label at={0.6} out={cutB}>the demonstration</Label></div>
            {t >= cutB && <div style={{ position: "absolute", right: 20, top: 18 }}><Label at={cutB}><span style={{ width: 8, height: 8, borderRadius: 4, background: t > fixed ? GREEN : CYAN }} />checks on</Label></div>}
            <div style={{ position: "absolute", left: 20, top: 18, display: "flex", gap: 10 }}>
              {t > knock && t < fixed && <Label at={knock} color={RED}>knocked over</Label>}
              {t > noticed && t < fixed && <Label at={noticed}>noticed</Label>}
              {t > fixed && <Label at={fixed} color={GREEN}><svg width="16" height="16" viewBox="0 0 18 18"><path d="M3 9.5l4 4 8-8" fill="none" stroke={GREEN} strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" /></svg>fixed</Label>}
            </div>
            <Flash at={cutB} dur={0.1} max={0.5} />
          </Frame>
        </div>
      </Cam>
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ 7. meta */

const MODELS: [string, string][] = [["Muse Spark", "watches the video and the camera"], ["Muse Wonder", "compiles the steps"], ["SAM 3.1", "outlines what each check is about"], ["Muse Image", "draws each skill"], ["Muse Spark Open", "the open-weights option"]];
const Meta: React.FC = () => {
  const t = useT(); const f = useCurrentFrame();
  return (
    <AbsoluteFill style={{ background: INK }}>
      <Still src="hero/pc.jpg" dim={0.8} />
      <Cam push={0.02}>
        <div style={{ position: "absolute", left: 110, top: 150, width: 760 }}>
          <Rule at={0.3} />
          <Head text="Built on Meta's models." at={0.4} size={66} align="left" style={{ marginTop: 16 }} />
          <Head text="Meta Global AI Hackathon 2026" at={1.0} size={26} weight={600} color={DIM} align="left" style={{ marginTop: 12 }} />
        </div>
        <div style={{ position: "absolute", left: 1000, top: 170, width: 820, display: "grid" }}>
          {MODELS.map(([name, job], i) => {
            const at = 1.0 + i * 0.22, p = sp(f, at, { damping: 20, stiffness: 150 });
            return <div key={name} style={{ display: "grid", gridTemplateColumns: "28px 1fr", alignItems: "baseline", gap: 18, padding: "20px 0", borderBottom: `1px solid ${LINE}`, transform: `translateX(${(1 - p) * 40}px)`, opacity: p }}>
              <span style={{ width: 8, height: 8, borderRadius: 4, background: CYAN, alignSelf: "center", opacity: t > at + 0.3 ? 1 : 0 }} />
              <div><div style={{ fontFamily: FONT, fontSize: 34, fontWeight: 760, color: WHITE, letterSpacing: "-0.02em" }}>{name}</div><div style={{ fontFamily: FONT, fontSize: 20, fontWeight: 550, color: DIM, marginTop: 4 }}>{job}</div></div>
            </div>;
          })}
        </div>
      </Cam>
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ 8. close */

const Close: React.FC = () => {
  const t = useT();
  const end = timing.durations[7], logoAt = S("close", 1) - 0.1, onceAt = S("close", 2);
  return (
    <AbsoluteFill style={{ background: INK }}>
      <Still src="hero/workshop.jpg" dim={0.6} />
      <Cam push={0.02}>
        <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
          <div style={{ position: "absolute", opacity: 1 - ramp(t, logoAt - 0.35, logoAt), display: "grid", justifyItems: "center", gap: 14 }}>
            <Head text="Maruthi Kunchala" at={0.6} size={64} weight={760} />
            <Head text="Team PULSE - Parallax" at={1.4} size={32} weight={600} color={DIM} />
          </div>
          {t > logoAt && <div style={{ display: "grid", justifyItems: "center" }}>
            <Logo at={logoAt} size={200} />
            <div style={{ marginTop: 36 }}><Head text="Show it once." at={onceAt} size={72} weight={700} /></div>
          </div>}
        </AbsoluteFill>
      </Cam>
      <AbsoluteFill style={{ background: INK, opacity: ramp(t, end - 1.0, end - 0.15) }} />
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ assembly */

const SCENES: React.FC[] = [Hook, Name, Learn, Live, Alert, Robot, Meta, Close];
const frames = timing.durations.map((d) => Math.round(d * FPS));
const TR = Math.round(timing.tr * FPS);
export const v8Frames = frames.reduce((a, b) => a + b, 0) - TR * (frames.length - 1);
const starts = frames.map((_, i) => frames.slice(0, i).reduce((a, b) => a + b, 0) - TR * i);

export const V8: React.FC = () => (
  <AbsoluteFill style={{ background: INK }}>
    <TransitionSeries>
      {SCENES.flatMap((C, i) => {
        const id = timing.ids[i];
        const items = [<TransitionSeries.Sequence key={id} durationInFrames={frames[i]}><C /></TransitionSeries.Sequence>];
        if (i < SCENES.length - 1) items.push(<TransitionSeries.Transition key={id + "-t"} presentation={fade()} timing={linearTiming({ durationInFrames: TR })} />);
        return items;
      })}
    </TransitionSeries>
    <Film />
    {timing.ids.map((id, i) => (
      <Sequence key={id} from={starts[i] + Math.round(LEAD * FPS)} durationInFrames={Math.round(VO(id).seconds * FPS) + 10}>
        <Audio src={staticFile(`${(timing as any).vo}/${id}.wav`)} volume={0.001} />
      </Sequence>
    ))}
  </AbsoluteFill>
);
