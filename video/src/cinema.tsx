import React from "react";
import { AbsoluteFill, Sequence, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { Video } from "@remotion/media";
import { FONT, ease } from "./ui";

// Generated b-roll (Higgsfield, Kling 3.0). Mood only: every shot of EIDOS
// itself in this film is real footage.

export const DARK = { bg: "#0b1220", ink: "#eef3fb", muted: "#a9b6c8", contract: "#8ea2ff", fail: "#ff7d90", pass: "#4fe0aa" };

/** Full-bleed b-roll that loops quietly behind dark "chapter" scenes. */
export const BrollBackdrop: React.FC<{ src: string; dim?: number; from?: number; fadeIn?: number }> = ({ src, dim = 0.55, from = 0, fadeIn = 0.6 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const o = interpolate(frame, [from * fps, (from + fadeIn) * fps], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ opacity: o }}>
      <Sequence from={Math.round(from * fps)} layout="none">
        <Video src={staticFile(src)} muted loop style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover" }} />
      </Sequence>
      <AbsoluteFill style={{ background: `linear-gradient(180deg, rgba(11,18,32,${dim * 0.7}) 0%, rgba(11,18,32,${dim}) 55%, rgba(11,18,32,${Math.min(0.92, dim + 0.3)}) 100%)` }} />
    </AbsoluteFill>
  );
};

/** A scene that opens on a generated shot with a big title, then hands over to real footage. */
export const WithIntro: React.FC<{ src: string; title: string; seconds?: number; label?: string; children: React.ReactNode }> = ({
  src, title, seconds = 2.5, label, children,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const n = Math.round(seconds * fps);
  const out = interpolate(frame, [n - 0.5 * fps, n], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: ease });
  const tin = interpolate(frame, [0.15 * fps, 0.8 * fps], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: ease });
  return (
    <AbsoluteFill>
      <Sequence from={n - Math.round(0.5 * fps)}>{children}</Sequence>
      {frame < n ? (
        <AbsoluteFill style={{ opacity: out, background: DARK.bg }}>
          <Video src={staticFile(src)} muted style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover" }} />
          <AbsoluteFill style={{ background: "linear-gradient(0deg, rgba(11,18,32,.82) 0%, rgba(11,18,32,.15) 60%)" }} />
          <div style={{ position: "absolute", left: 130, bottom: 150, right: 130, fontFamily: FONT, color: DARK.ink, opacity: tin, translate: `0px ${(1 - tin) * 24}px` }}>
            <div style={{ fontSize: 96, fontWeight: 800, lineHeight: 1.02, letterSpacing: "-0.015em", fontVariationSettings: '"wdth" 118' }}>{title}</div>
          </div>
          {label ? (
            <div style={{ position: "absolute", top: 40, right: 50, fontFamily: FONT, fontSize: 24, color: DARK.ink, background: "rgba(11,18,32,.6)", padding: "6px 14px", borderRadius: 8 }}>{label}</div>
          ) : null}
        </AbsoluteFill>
      ) : null}
    </AbsoluteFill>
  );
};
