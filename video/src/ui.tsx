import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame, useVideoConfig, staticFile } from "remotion";
import { loadFont } from "@remotion/fonts";

export const C = {
  paper: "#eef1f5",
  surface: "#ffffff",
  ink: "#142130",
  muted: "#5a6878",
  line: "#d5dce5",
  contract: "#3352ff",
  contractSoft: "rgba(51,82,255,.10)",
  pass: "#0b8f63",
  passSoft: "rgba(11,143,99,.12)",
  fail: "#cf3049",
  failSoft: "rgba(207,48,73,.10)",
};

export const FONT = "Archivo";
export const MONO = "JetBrains Mono";

loadFont({ family: FONT, url: staticFile("fonts/archivo-latin-wdth-normal.woff2"), weight: "100 900" });
loadFont({ family: MONO, url: staticFile("fonts/jetbrains-mono-latin-600-normal.woff2"), weight: "600" });

export const ease = Easing.bezier(0.16, 1, 0.3, 1);

/** 0 to 1 over [start, start+dur] seconds, eased. */
export const useIn = (start: number, dur = 0.6) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return interpolate(frame, [start * fps, (start + dur) * fps], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: ease,
  });
};

export const Page: React.FC<{ children: React.ReactNode; bg?: string }> = ({ children, bg }) => (
  <AbsoluteFill
    style={{
      background: bg ?? C.paper,
      color: C.ink,
      fontFamily: FONT,
      padding: "110px 130px",
      fontVariationSettings: '"wdth" 100',
    }}
  >
    {children}
  </AbsoluteFill>
);

export const Rise: React.FC<{ at: number; children: React.ReactNode; style?: React.CSSProperties; dist?: number }> = ({
  at,
  children,
  style,
  dist = 26,
}) => {
  const p = useIn(at);
  return <div style={{ opacity: p, translate: `0px ${(1 - p) * dist}px`, ...style }}>{children}</div>;
};

/** Marching-ants outline: the visual contract. */
export const Contract: React.FC<{
  x: number;
  y: number;
  w: number;
  h: number;
  ok?: boolean;
  label?: string;
  scale?: number;
  fill?: boolean;
}> = ({ x, y, w, h, ok, label, scale = 1, fill }) => {
  const frame = useCurrentFrame();
  const col = ok ? C.pass : C.contract;
  const off = (frame * 0.6) % 12;
  const dash = (dir: string, pos: string, size: string, rep: string) =>
    `linear-gradient(${dir}, ${col} 50%, transparent 0) ${pos} / ${size} ${rep}`;
  return (
    <>
      <div
        style={{
          position: "absolute",
          ...(fill ? { inset: 0 } : { left: x * scale, top: y * scale, width: w * scale, height: h * scale }),
          borderRadius: 4,
          background: [
            dash("90deg", `${off}px 0`, "12px 3px", "repeat-x"),
            dash("90deg", `${-off}px 100%`, "12px 3px", "repeat-x"),
            dash("0deg", `0 ${-off}px`, "3px 12px", "repeat-y"),
            dash("0deg", `100% ${off}px`, "3px 12px", "repeat-y"),
            ok ? C.passSoft : C.contractSoft,
          ].join(","),
        }}
      />
      {label ? (
        <div
          style={{
            position: "absolute",
            left: Math.min(x, 600) * scale,
            top: y * scale - 46,
            background: col,
            color: "#fff",
            fontSize: 24,
            fontWeight: 650,
            padding: "6px 12px",
            borderRadius: 6,
            whiteSpace: "nowrap",
          }}
        >
          {label}
        </div>
      ) : null}
    </>
  );
};

export const Stamp: React.FC<{ ok: boolean; text: string; at: number }> = ({ ok, text, at }) => {
  const p = useIn(at, 0.45);
  return (
    <div
      style={{
        display: "inline-flex",
        justifySelf: "start",
        alignItems: "center",
        gap: 12,
        opacity: p,
        scale: String(0.9 + 0.1 * p),
        fontSize: 30,
        fontWeight: 750,
        color: ok ? C.pass : C.fail,
        background: ok ? C.passSoft : C.failSoft,
        padding: "8px 18px",
        borderRadius: 999,
      }}
    >
      <span
        style={{
          width: 34,
          height: 34,
          borderRadius: "50%",
          background: ok ? C.pass : C.fail,
          color: "#fff",
          display: "grid",
          placeItems: "center",
          fontSize: 22,
        }}
      >
        {ok ? "✓" : "✕"}
      </span>
      {text}
    </div>
  );
};

/** Burned-in captions: the narration, one sentence at a time. */
export const Caption: React.FC<{ text: string; seconds: number }> = ({ text, seconds }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const clean = text.replace(/Eye-doss/g, "EIDOS");
  const parts = clean.match(/[^.!?]+[.!?]+/g) ?? [clean];
  const total = parts.reduce((a, s) => a + s.length, 0);
  const t = frame / fps;
  let acc = 0;
  let current = parts[parts.length - 1];
  for (const s of parts) {
    const end = acc + (s.length / total) * seconds;
    if (t < end) {
      current = s;
      break;
    }
    acc = end;
  }
  return (
    <div
      style={{
        position: "absolute",
        left: 0,
        right: 0,
        bottom: 34,
        display: "flex",
        justifyContent: "center",
        pointerEvents: "none",
      }}
    >
      <div
        style={{
          maxWidth: 1500,
          fontFamily: FONT,
          fontSize: 32,
          lineHeight: 1.3,
          color: "#fff",
          background: "rgba(20,33,48,.82)",
          padding: "10px 22px",
          borderRadius: 10,
          textAlign: "center",
        }}
      >
        {current.trim()}
      </div>
    </div>
  );
};
