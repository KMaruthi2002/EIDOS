import React from "react";
import { AbsoluteFill, Img, Sequence, getStaticFiles, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { Video } from "@remotion/media";
import { C, Contract, MONO, Page, Rise, Stamp, useIn } from "./ui";
import { BrollBackdrop, DARK } from "./cinema";
import trace from "./trace.json";
import results from "./results.json";
import physical from "./physical.json";

const H1: React.CSSProperties = { fontSize: 112, fontWeight: 800, lineHeight: 1.0, letterSpacing: "-0.02em", fontVariationSettings: '"wdth" 118', margin: 0 };
const H2: React.CSSProperties = { fontSize: 76, fontWeight: 780, lineHeight: 1.05, fontVariationSettings: '"wdth" 115', margin: 0 };
const BODY: React.CSSProperties = { fontSize: 44, lineHeight: 1.35, color: C.muted, maxWidth: 1300 };

/* 1. Hook ---------------------------------------------------------------- */
export const Hook: React.FC = () => (
  <AbsoluteFill style={{ background: DARK.bg }}>
    <BrollBackdrop src="broll/shot00.mp4" dim={0.35} fadeIn={0.8} />
    <Page bg="transparent">
      <div style={{ marginTop: "auto", marginBottom: 90, color: DARK.ink }}>
        <Rise at={0.6}><div style={{ ...H1, color: DARK.ink }}>Billions of hours of screen recordings.</div></Rise>
        <Rise at={5.6} style={{ marginTop: 26 }}><div style={{ ...H2, color: DARK.fail }}>AI agents can't learn from any of it.</div></Rise>
      </div>
    </Page>
  </AbsoluteFill>
);

/* 2. Problem ------------------------------------------------------------- */
export const Problem: React.FC = () => {
  const lines: [number, string, string][] = [
    [0.4, "Agents learn tasks from text.", "Prompts, documents, hand-written skills."],
    [5.6, "Video is only a hint.", "Research agents that read tutorials gain about +2 to +7 points on OSWorld."],
    [11.2, "When they go wrong, they don't know.", "No check against what the person actually did."],
  ];
  return (
    <AbsoluteFill style={{ background: DARK.bg }}>
      <BrollBackdrop src="broll/shot01.mp4" dim={0.62} />
      <BrollBackdrop src="broll/shot02.mp4" dim={0.62} from={10.8} fadeIn={0.8} />
      <Page bg="transparent">
        <div style={{ display: "grid", gap: 64, marginTop: 40 }}>
          {lines.map(([at, big, small], i) => (
            <Rise key={i} at={at}>
              <div style={{ display: "grid", gridTemplateColumns: "90px 1fr", gap: 30, alignItems: "baseline" }}>
                <div style={{ fontSize: 64, fontWeight: 800, color: i === 2 ? DARK.fail : DARK.muted, fontVariationSettings: '"wdth" 125' }}>{i + 1}</div>
                <div>
                  <div style={{ ...H2, fontSize: 70, color: i === 2 ? DARK.fail : DARK.ink }}>{big}</div>
                  <div style={{ ...BODY, color: DARK.muted, marginTop: 10 }}>{small}</div>
                </div>
              </div>
            </Rise>
          ))}
        </div>
      </Page>
    </AbsoluteFill>
  );
};

/* 3. Name ---------------------------------------------------------------- */
export const Name: React.FC = () => {
  const p = useIn(0.2, 0.9);
  const q = useIn(4.6);
  const r = useIn(8.2);
  return (
    <AbsoluteFill style={{ background: DARK.bg }}>
      <BrollBackdrop src="broll/shot03.mp4" dim={0.5} />
      <Page bg="transparent">
        <div style={{ margin: "auto 0", display: "grid", gap: 40, color: DARK.ink }}>
          <div style={{ position: "relative", display: "inline-block", width: "fit-content", padding: "14px 40px", opacity: p }}>
            <Contract x={0} y={0} w={0} h={0} fill />
            <div style={{ ...H1, fontSize: 170, letterSpacing: "0.12em", fontVariationSettings: '"wdth" 125', position: "relative", color: DARK.ink }}>EIDOS</div>
          </div>
          <div style={{ ...H2, opacity: q, color: DARK.ink }}>Learns the form of a task, not the pixels.</div>
          <div style={{ ...BODY, opacity: r, color: DARK.ink }}>
            Every step carries a <span style={{ color: DARK.contract, fontWeight: 700 }}>visual contract</span> from the video, so the agent can check it did what the person did.
          </div>
        </div>
      </Page>
    </AbsoluteFill>
  );
};

/* tutorial video with contract overlays */
const VW = 1100, VH = 620;
type TStep = (typeof trace.steps)[number];
const boxOf = (s: TStep): number[] | null => {
  const c = s.contract as Record<string, unknown>;
  if (c.selection_box) return c.selection_box as number[];
  if (c.cell_box) return c.cell_box as number[];
  if (s.action === "press_control") return [s.point[0] - 18, s.point[1] - 18, 36, 36];
  return (c.changed_box as number[]) ?? null;
};
const LABELS = ["Write the label", "Sum the column", "Select the row", "Make it bold"];

const TutorialWithContracts: React.FC<{ width: number }> = ({ width }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const scale = width / VW;
  return (
    <div style={{ position: "relative", width, height: VH * scale, borderRadius: 14, overflow: "hidden", boxShadow: "0 30px 80px -40px rgba(20,33,48,.45)", border: `1px solid ${C.line}` }}>
      <Video src={staticFile("clips/tutorial_totals.mp4")} muted style={{ width, height: VH * scale }} />
      {trace.steps.map((s, i) => {
        const b = boxOf(s);
        const next = trace.steps[i + 1];
        const until = next ? Math.min(s.t_end + 0.6, next.t_start - 0.1) : s.t_end + 2.0;
        if (!b || t < s.t_start - 0.15 || t > until) return null;
        return <Contract key={i} x={b[0]} y={b[1]} w={b[2]} h={b[3]} scale={scale} ok={t > s.t_end - 0.25} label={`${i + 1}. ${LABELS[i]}`} />;
      })}
    </div>
  );
};

/* 4. Watch --------------------------------------------------------------- */
export const Watch: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  return (
    <AbsoluteFill style={{ background: C.paper, fontFamily: "Archivo", color: C.ink, padding: "80px 100px", flexDirection: "row", gap: 60, alignItems: "center" }}>
      <div style={{ width: 400, display: "grid", gap: 28 }}>
        <Rise at={0.2}><div style={{ ...H2, fontSize: 50 }}>One tutorial, 14 seconds.</div></Rise>
        <div style={{ display: "grid", gap: 14 }}>
          {trace.steps.map((s, i) => {
            const on = t > s.t_start + 0.2;
            return (
              <div key={i} style={{ display: "flex", gap: 16, alignItems: "center", fontSize: 32, opacity: on ? 1 : 0.25 }}>
                <span style={{ width: 44, height: 44, borderRadius: 8, border: `3px dashed ${on ? C.pass : C.line}`, display: "grid", placeItems: "center", fontWeight: 800, fontSize: 24, color: on ? C.pass : C.muted }}>{i + 1}</span>
                {["Click", "Click", "Drag", "Click"][i]}{s.text ? <span style={{ fontFamily: MONO, fontSize: 26, color: C.contract }}>{s.text}</span> : null}
              </div>
            );
          })}
        </div>
        <Rise at={9.5}><div style={{ fontSize: 30, color: C.muted, lineHeight: 1.35 }}>Recovered from the video frames: the highlighted pointer, click rings, and what changed.</div></Rise>
      </div>
      <TutorialWithContracts width={1300} />
    </AbsoluteFill>
  );
};

/* 5. Understand ---------------------------------------------------------- */
export const Understand: React.FC = () => {
  const a = useIn(4.2, 0.8);
  const b = useIn(9.2, 0.8);
  const card: React.CSSProperties = { background: C.surface, border: `1px solid ${C.line}`, borderRadius: 16, padding: "30px 36px", display: "grid", gap: 14 };
  const k: React.CSSProperties = { fontSize: 26, color: C.muted, fontWeight: 650 };
  return (
    <Page>
      <Rise at={0.2}><div style={H2}>It learns what each step was for.</div></Rise>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 40, marginTop: 60 }}>
        <Rise at={1.0}>
          <div style={card}>
            <div style={k}>Seen in the video</div>
            <div style={{ fontFamily: MONO, fontSize: 64, color: C.ink }}>=SUM(E2:E11)</div>
            <div style={{ height: 2, background: C.line, margin: "8px 0" }} />
            <div style={{ ...k, opacity: a }}>Learned</div>
            <div style={{ fontSize: 46, fontWeight: 700, lineHeight: 1.2, opacity: a }}>
              Sum the <span style={{ color: C.contract }}>Revenue</span> column over <span style={{ color: C.contract }}>all data rows</span>
            </div>
          </div>
        </Rise>
        <Rise at={6.6}>
          <div style={card}>
            <div style={k}>Seen in the video</div>
            <div style={{ display: "grid", gap: 10 }}>
              {[["row_before", "Before"], ["row_after", "After"]].map(([f, lab]) => (
                <div key={f} style={{ display: "grid", gridTemplateColumns: "90px 1fr", alignItems: "center", gap: 12 }}>
                  <span style={{ fontSize: 22, color: C.muted }}>{lab}</span>
                  <Img src={staticFile(`stills/${f}.png`)} style={{ width: "100%", borderRadius: 6, border: `1px solid ${C.line}` }} />
                </div>
              ))}
            </div>
            <div style={{ height: 2, background: C.line, margin: "8px 0" }} />
            <div style={{ ...k, opacity: b }}>Learned</div>
            <div style={{ fontSize: 46, fontWeight: 700, lineHeight: 1.2, opacity: b }}>
              Make the row <span style={{ color: C.contract }}>bold</span>, because the text got heavier
            </div>
          </div>
        </Rise>
      </div>
    </Page>
  );
};

/* 6 and 7. Split-screen runs -------------------------------------------- */
const Lane: React.FC<{ clip: string; still: string; seconds: number; title: string; ok: boolean; verdict: string; delay: number; width: number }> = ({
  clip, still, seconds, title, ok, verdict, delay, width,
}) => {
  const { fps } = useVideoConfig();
  const h = (VH / VW) * width;
  return (
    <div style={{ display: "grid", gap: 20, width }}>
      <div style={{ fontSize: 40, fontWeight: 750, fontVariationSettings: '"wdth" 112' }}>{title}</div>
      <div style={{ position: "relative", width, height: h, borderRadius: 14, overflow: "hidden", border: `1px solid ${C.line}`, background: "#fff" }}>
        <Img src={staticFile(still)} style={{ position: "absolute", inset: 0, width, height: h }} />
        <Sequence from={Math.round(delay * fps)} durationInFrames={Math.round(seconds * fps) - 3} layout="none">
          <Video src={staticFile(clip)} muted style={{ position: "absolute", inset: 0, width, height: h }} />
        </Sequence>
      </div>
      <Stamp ok={ok} text={verdict} at={delay + seconds - 0.4} />
    </div>
  );
};

export const Runs: React.FC<{ which: string; heading: string; sub: string; leftTitle: string; leftVerdict: string; rightVerdict: string }> = ({
  which, heading, sub, leftTitle, leftVerdict, rightVerdict,
}) => {
  const dur = results.clips as Record<string, number>;
  const W = 790;
  return (
    <Page>
      <Rise at={0.1}><div style={{ ...H2, fontSize: 62 }}>{heading}</div></Rise>
      <Rise at={0.5}><div style={{ ...BODY, fontSize: 34, marginTop: 10 }}>{sub}</div></Rise>
      <div style={{ display: "flex", gap: 60, marginTop: 46 }}>
        <Lane clip={`clips/${which}_replay.mp4`} still={`stills/${which}_replay_end.png`} seconds={dur[`${which}_replay`]} title={leftTitle} ok={false} verdict={leftVerdict} delay={1.2} width={W} />
        <Lane clip={`clips/${which}_eidos.mp4`} still={`stills/${which}_eidos_end.png`} seconds={dur[`${which}_eidos`]} title="EIDOS" ok verdict={rightVerdict} delay={1.2} width={W} />
      </div>
    </Page>
  );
};

/* 8. Results ------------------------------------------------------------- */
export const Results: React.FC = () => {
  const r = results.test as any;
  const rows: [string, { success: number; n: number }, string][] = [
    ["Copying the clicks", r.all.replay, C.muted],
    ["EIDOS with checks off", r.all.eidos_nochk, "#8a96a6"],
    ["EIDOS", r.all.eidos, C.contract],
  ];
  const it = r.interruption;
  return (
    <Page>
      <Rise at={0.1}><div style={H2}>Pilot benchmark</div></Rise>
      <Rise at={0.5}><div style={{ ...BODY, fontSize: 34, marginTop: 12 }}>{`${r.all.eidos.n} runs: new data, a second app, ${r.redesign.eidos.n} random redesigns and ${it.eidos.n} mid-task interruptions from a held-out seed. Judged from each app's internal state.`}</div></Rise>
      <div style={{ display: "grid", gap: 30, marginTop: 56 }}>
        {rows.map(([name, v, col], i) => (
          <Bar key={name} name={name} v={v} col={col} at={1.6 + i * 1.2} />
        ))}
      </div>
      <Rise at={6.0} style={{ marginTop: 50 }}>
        <div style={{ display: "flex", gap: 70, fontSize: 38, lineHeight: 1.3, flexWrap: "wrap" }}>
          <div><span style={{ fontWeight: 800, color: C.pass }}>{`${r.self.agrees_with_oracle}/${r.self.n}`}</span> own verdict matched the truth</div>
          <div>Interrupted: <span style={{ fontWeight: 800, color: C.contract }}>{`${it.eidos.success}/${it.eidos.n}`}</span> with checks, <span style={{ fontWeight: 800, color: C.fail }}>{`${it.eidos_nochk.success}/${it.eidos_nochk.n}`}</span> without</div>
        </div>
      </Rise>
    </Page>
  );
};

const Bar: React.FC<{ name: string; v: { success: number; n: number }; col: string; at: number }> = ({ name, v, col, at }) => {
  const p = useIn(at, 1.0);
  const pct = v.n ? v.success / v.n : 0;
  return (
    <div style={{ display: "grid", gridTemplateColumns: "460px 1fr 170px", alignItems: "center", gap: 30, opacity: Math.min(1, p * 3) }}>
      <div style={{ fontSize: 40, fontWeight: 650 }}>{name}</div>
      <div style={{ height: 46, background: "rgba(20,33,48,.07)", borderRadius: 8, overflow: "hidden" }}>
        <div style={{ width: `${pct * 100 * p}%`, height: "100%", background: col, borderRadius: 8 }} />
      </div>
      <div style={{ fontSize: 48, fontWeight: 800, textAlign: "right", fontVariantNumeric: "tabular-nums" }}>{`${Math.round(v.success * p)}/${v.n}`}</div>
    </div>
  );
};

/* 9. Meta models ---------------------------------------------------------- */
export const Models: React.FC = () => {
  const rows: [string, string][] = [
    ["SAM 3.1", "Tracks the pointer, segments what changed, finds controls by concept"],
    ["Muse Spark", "Reads each step: what was it for?"],
    ["Muse Wonder", "Compiles the steps into a general program with contracts"],
    ["Muse Image", "Draws a card for each learned skill"],
  ];
  return (
    <Page>
      <Rise at={0.1}><div style={H2}>Designed around Meta's models</div></Rise>
      <div style={{ display: "grid", gap: 0, marginTop: 54, background: C.surface, borderRadius: 16, border: `1px solid ${C.line}`, overflow: "hidden" }}>
        {rows.map(([m, job], i) => (
          <Rise key={m} at={1.6 + i * 2.2} dist={14}>
            <div style={{ display: "grid", gridTemplateColumns: "380px 1fr", gap: 30, padding: "30px 40px", borderTop: i ? `1px solid ${C.line}` : "none" }}>
              <div style={{ fontSize: 44, fontWeight: 800, fontVariationSettings: '"wdth" 112' }}>{m}</div>
              <div style={{ fontSize: 38, color: C.muted, lineHeight: 1.3 }}>{job}</div>
            </div>
          </Rise>
        ))}
      </div>
      <Rise at={12.2} style={{ marginTop: 40 }}>
        <div style={{ fontSize: 32, color: C.muted }}>Everything shown ran offline, with classic vision standing in for each model, so every result is reproducible.</div>
      </Rise>
    </Page>
  );
};

/* 10. Close --------------------------------------------------------------- */
export const Close: React.FC = () => {
  const p = useIn(2.6, 0.9);
  return (
    <AbsoluteFill style={{ background: DARK.bg }}>
      <BrollBackdrop src="broll/shot09.mp4" dim={0.55} />
      <Page bg="transparent">
        <div style={{ margin: "auto 0", display: "grid", gap: 30 }}>
          <Rise at={0.1}><div style={{ ...H2, color: DARK.muted }}>Prompting is how we talk to AI.</div></Rise>
          <Rise at={1.4}><div style={{ ...H2, color: DARK.ink }}>Showing is how we'll teach it.</div></Rise>
          <div style={{ position: "relative", width: "fit-content", padding: "12px 34px", marginTop: 50, opacity: p }}>
            <Contract x={0} y={0} w={0} h={0} fill ok={p > 0.95} />
            <div style={{ ...H1, fontSize: 130, letterSpacing: "0.12em", fontVariationSettings: '"wdth" 125', position: "relative", color: DARK.ink }}>EIDOS</div>
          </div>
          <div style={{ fontSize: 30, color: DARK.muted, opacity: p }}>Maruthi Kunchala, Team Parallax. Meta Global AI Hackathon 2026.</div>
          <div style={{ fontSize: 20, color: DARK.muted, opacity: p * 0.8 }}>Cinematic shots generated with Higgsfield. All EIDOS footage is real.</div>
        </div>
      </Page>
    </AbsoluteFill>
  );
};

/* Robot add-on ------------------------------------------------------------ */

export const Robot: React.FC = () => {
  const p = physical as any;
  const W = 790;
  const H = (540 / 960) * W;
  const lane = (clip: string, title: string, ok: boolean, verdict: string, rate: number, len: number) => (
    <div style={{ display: "grid", gap: 18, width: W }}>
      <div style={{ fontSize: 38, fontWeight: 750, fontVariationSettings: '"wdth" 112' }}>{title}</div>
      <div style={{ position: "relative", width: W, height: H, borderRadius: 14, overflow: "hidden", border: `1px solid ${C.line}`, background: "#fff" }}>
        <Img src={staticFile(`physical/${clip}_end.png`)} style={{ position: "absolute", inset: 0, width: W, height: H }} />
        <Sequence from={30} durationInFrames={Math.round((len / rate) * 30) - 3} layout="none">
          <Video src={staticFile(`physical/${clip}.mp4`)} muted playbackRate={rate} style={{ position: "absolute", inset: 0, width: W, height: H }} />
        </Sequence>
        <div style={{ position: "absolute", top: 10, right: 12, fontSize: 20, color: C.muted, background: "rgba(255,255,255,.85)", padding: "2px 8px", borderRadius: 6 }}>{rate}x speed</div>
      </div>
      <Stamp ok={ok} text={verdict} at={1 + len / rate - 0.3} />
    </div>
  );
  return (
    <Page>
      <Rise at={0.1}><div style={{ ...H2, fontSize: 62 }}>Off the screen: a robot arm.</div></Rise>
      <Rise at={0.5}><div style={{ ...BODY, fontSize: 32, marginTop: 10 }}>
        {`Learned from a demonstration video: ${p.steps.join(", then ")}. Simulated Franka Panda in MuJoCo; the arm's motions are scripted, EIDOS decides what to do and checks it with the robot's cameras. Halfway through, the table gets bumped.`}
      </div></Rise>
      <div style={{ display: "flex", gap: 60, marginTop: 36 }}>
        {lane("nochk", "EIDOS with checks off", p.nochk.truth, p.nochk.truth ? "Stack correct" : "Says \"done\". Stack has fallen.", 3, p.nochk.seconds)}
        {lane("eidos", "EIDOS", p.eidos.truth, p.eidos.truth ? "Noticed, rebuilt, verified" : "Stack not correct", 3, p.eidos.seconds)}
      </div>
    </Page>
  );
};
