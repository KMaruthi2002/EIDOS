import React from "react";
import { AbsoluteFill, Img, Sequence, Series, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { Audio, Video } from "@remotion/media";
import { C, Caption, Contract, MONO, Page, Rise, Stamp, useIn } from "./ui";
import { BrollBackdrop, DARK, WithIntro } from "./cinema";
import { Robot } from "./scenes";
import timeline from "./timeline3.json";
import mail from "./mail_trace.json";
import story from "./story.json";

const H1: React.CSSProperties = { fontSize: 104, fontWeight: 800, lineHeight: 1.02, letterSpacing: "-0.02em", fontVariationSettings: '"wdth" 118', margin: 0 };
const H2: React.CSSProperties = { fontSize: 70, fontWeight: 780, lineHeight: 1.06, fontVariationSettings: '"wdth" 115', margin: 0 };
const BODY: React.CSSProperties = { fontSize: 40, lineHeight: 1.35, color: C.muted, maxWidth: 1400 };
const T = (id: string) => timeline.find((s) => s.id === id)!.seconds;

/* The words in the narration, as on-screen beats: [seconds, text]. */
const Beats: React.FC<{ beats: [number, string, string?][]; dark?: boolean; size?: number }> = ({ beats, dark, size = 66 }) => (
  <div style={{ display: "grid", gap: 34 }}>
    {beats.map(([at, big, col], i) => (
      <Rise key={i} at={at}><div style={{ ...H2, fontSize: size, color: col ?? (dark ? DARK.ink : C.ink) }}>{big}</div></Rise>
    ))}
  </div>
);

/* 1 */
const Hook: React.FC = () => (
  <AbsoluteFill style={{ background: DARK.bg }}>
    <BrollBackdrop src="broll/shot00.mp4" dim={0.4} fadeIn={0.8} />
    <Page bg="transparent">
      <div style={{ marginTop: "auto", marginBottom: 80 }}>
        <Beats dark size={60} beats={[[5.0, "Send this email."], [6.3, "File this expense."], [7.6, "Turn on this setting."]]} />
        <Rise at={9.4} style={{ marginTop: 40 }}><div style={{ ...H1, color: DARK.ink }}>Billions of hours of how-to videos.</div></Rise>
        <Rise at={T("hook") - 3.2} style={{ marginTop: 22 }}><div style={{ ...H2, color: DARK.fail }}>AI agents can't learn from a single one.</div></Rise>
      </div>
    </Page>
  </AbsoluteFill>
);

/* 2 */
const Problem: React.FC = () => (
  <AbsoluteFill style={{ background: DARK.bg }}>
    <BrollBackdrop src="broll/shot01.mp4" dim={0.65} />
    <Page bg="transparent">
      <div style={{ margin: "auto 0" }}>
        <Beats dark beats={[[0.4, "Agents copy clicks."], [3.4, "Change the app, and they click on nothing."], [T("problem") - 4.2, "And they report success anyway.", DARK.fail]]} />
      </div>
    </Page>
  </AbsoluteFill>
);

/* 3 */
const Name: React.FC = () => {
  const p = useIn(0.3, 0.9);
  return (
    <AbsoluteFill style={{ background: DARK.bg }}>
      <BrollBackdrop src="broll/shot03.mp4" dim={0.5} />
      <Page bg="transparent">
        <div style={{ margin: "auto 0", display: "grid", gap: 40 }}>
          <div style={{ position: "relative", width: "fit-content", padding: "14px 40px", opacity: p }}>
            <Contract x={0} y={0} w={0} h={0} fill ok={p > 0.98} />
            <div style={{ ...H1, fontSize: 170, letterSpacing: "0.12em", fontVariationSettings: '"wdth" 125', position: "relative", color: DARK.ink }}>EIDOS</div>
          </div>
          <Rise at={2.2}><div style={{ ...H2, color: DARK.ink }}>Show it once. It learns the skill.</div></Rise>
          <Rise at={5.2}><div style={{ ...BODY, color: DARK.muted }}>A program an agent can run anywhere, that <span style={{ color: DARK.pass, fontWeight: 700 }}>checks its own work</span> at every step.</div></Rise>
        </div>
      </Page>
    </AbsoluteFill>
  );
};

/* A screen recording in a frame (everyday apps are 1200 x 760). */
const Screen: React.FC<{ src: string; width: number; still?: string; from?: number; rate?: number; children?: React.ReactNode; len?: number }> = ({ src, width, still, from = 0, rate = 1, children, len }) => {
  const { fps } = useVideoConfig();
  const h = (760 / 1200) * width;
  return (
    <div style={{ position: "relative", width, height: h, borderRadius: 14, overflow: "hidden", border: `1px solid ${C.line}`, background: "#fff", boxShadow: "0 30px 80px -40px rgba(20,33,48,.45)" }}>
      {still ? <Img src={staticFile(still)} style={{ position: "absolute", inset: 0, width, height: h }} /> : null}
      <Sequence from={Math.round(from * fps)} durationInFrames={len ? Math.round((len / rate) * fps) - 2 : undefined} layout="none">
        <Video src={staticFile(src)} muted playbackRate={rate} style={{ position: "absolute", inset: 0, width, height: h }} />
      </Sequence>
      {children}
    </div>
  );
};

/* 4: the tutorial with what EIDOS found, step by step */
const Watch: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const lead = 0.6;
  const t = frame / fps - lead;
  const W = 1180, scale = W / 1200;
  const steps = mail.steps as any[];
  const NAMES = ["Press Compose", "Type into “To”", "Type into “Subject”", "Type into “Message”", "Press Send"];
  return (
    <Page>
      <div style={{ display: "flex", gap: 50, alignItems: "flex-start", marginTop: -20 }}>
        <div style={{ display: "grid", gap: 18 }}>
          <Rise at={0}><div style={{ fontSize: 34, color: C.muted, fontWeight: 650 }}>The tutorial: 19 seconds, highlighted pointer</div></Rise>
          <Screen src="clips/tutorial_mail.mp4" width={W} from={lead}>
            {steps.map((s, i) => {
              const nxt = steps[i + 1];
              const until = nxt ? nxt.t - 0.1 : s.t + 2.5;
              if (!s.box || t < s.t - 0.1 || t > until) return null;
              const b = s.box;
              return <Contract key={i} x={b[0]} y={b[1]} w={b[2]} h={b[3]} scale={scale} ok={t > s.t + 0.8} label={`${i + 1}. ${NAMES[i]}`} />;
            })}
          </Screen>
        </div>
        <div style={{ display: "grid", gap: 16, marginTop: 64, width: 420 }}>
          <div style={{ fontSize: 30, fontWeight: 750, color: C.muted, letterSpacing: ".08em", textTransform: "uppercase" }}>What EIDOS found</div>
          {steps.map((s, i) => {
            const on = t >= s.t;
            return (
              <div key={i} style={{ display: "grid", gridTemplateColumns: "44px 1fr", gap: 14, alignItems: "center", opacity: on ? 1 : 0.22, transition: "none" }}>
                <div style={{ width: 44, height: 44, borderRadius: "50%", background: on ? C.contract : C.line, color: "#fff", display: "grid", placeItems: "center", fontWeight: 800, fontSize: 24 }}>{i + 1}</div>
                <div>
                  <div style={{ fontSize: 30, fontWeight: 700 }}>{NAMES[i]}</div>
                  {s.value ? <div style={{ fontFamily: MONO, fontSize: 20, color: C.muted }}>{`“${s.value}”`}</div> : null}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </Page>
  );
};

/* 5: the program */
const Understand: React.FC = () => {
  const prog = story.program as any[];
  return (
    <Page>
      <Rise at={0.1}><div style={H2}>The skill it compiled</div></Rise>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 60, marginTop: 50 }}>
        <div style={{ display: "grid", gap: 18 }}>
          {prog.map((s, i) => (
            <Rise key={i} at={1.0 + i * 0.5} dist={14}>
              <div style={{ background: C.surface, border: `1px solid ${C.line}`, borderRadius: 14, padding: "16px 22px" }}>
                <div style={{ fontSize: 30, fontWeight: 700 }}>
                  <span style={{ fontFamily: MONO, color: C.muted, fontSize: 22, marginRight: 12 }}>{s.do}</span>
                  {s.what}
                </div>
                <div style={{ fontSize: 22, color: C.contract, marginTop: 6 }}><b style={{ fontFamily: MONO, fontSize: 16, letterSpacing: ".1em" }}>CONTRACT </b>{s.contract}</div>
              </div>
            </Rise>
          ))}
        </div>
        <div style={{ display: "grid", gap: 40, alignContent: "start", marginTop: 10 }}>
          <Rise at={2.4}><Point n="1" title="Targets by label" text="“the field labelled To”, never “the box at x = 467”" /></Rise>
          <Rise at={7.4}><Point n="2" title="Typed values become inputs" text="{to} · {subject} · {message}: send any email, to anyone" /></Rise>
          <Rise at={T("understand") - 6.6}><Point n="3" title="A contract per step" text="what must be true on screen once the step is done" /></Rise>
        </div>
      </div>
    </Page>
  );
};
const Point: React.FC<{ n: string; title: string; text: string }> = ({ n, title, text }) => (
  <div style={{ display: "grid", gridTemplateColumns: "64px 1fr", gap: 20 }}>
    <div style={{ width: 64, height: 64, borderRadius: 16, background: C.contractSoft, color: C.contract, fontSize: 34, fontWeight: 800, display: "grid", placeItems: "center" }}>{n}</div>
    <div>
      <div style={{ fontSize: 40, fontWeight: 760 }}>{title}</div>
      <div style={{ fontSize: 28, color: C.muted, marginTop: 6, lineHeight: 1.3 }}>{text}</div>
    </div>
  </div>
);

/* 6 and 7: split screen */
const Split: React.FC<{ heading: string; sub: string; left: [string, string, number, string]; right: [string, string, number, string]; leftOk?: boolean }> = ({ heading, sub, left, right, leftOk = false }) => {
  const W = 790;
  const lane = ([title, clip, len, verdict]: [string, string, number, string], ok: boolean) => (
    <div style={{ display: "grid", gap: 18, width: W }}>
      <div style={{ fontSize: 38, fontWeight: 750, fontVariationSettings: '"wdth" 112' }}>{title}</div>
      <Screen src={`clips/${clip}.mp4`} still={`stills/${clip}_end.png`} width={W} from={1.0} len={len} />
      <Stamp ok={ok} text={verdict} at={1.0 + len - 0.3} />
    </div>
  );
  return (
    <Page>
      <Rise at={0.1}><div style={{ ...H2, fontSize: 58 }}>{heading}</div></Rise>
      <Rise at={0.5}><div style={{ ...BODY, fontSize: 32, marginTop: 8 }}>{sub}</div></Rise>
      <div style={{ display: "flex", gap: 60, marginTop: 40 }}>{lane(left, leftOk)}{lane(right, true)}</div>
    </Page>
  );
};
const clipLen = (k: string) => (story.clips as Record<string, number>)[k];

/* 8: the four everyday tasks */
const Tasks: React.FC = () => {
  const items: [string, string][] = [["Send an email", "mail"], ["Add a calendar event", "calendar"], ["Submit an expense", "expense"], ["Turn on two-factor sign-in", "settings"]];
  const kinds = ["press", "type", "choose", "switch"];
  return (
    <Page>
      <Rise at={0.1}><div style={H2}>Four everyday tasks. One engine.</div></Rise>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px 36px", marginTop: 28, width: 1040 }}>
        {items.map(([t, k], i) => (
          <Rise key={k} at={2.2 + i * 1.1} dist={14}>
            <div style={{ display: "grid", gap: 10 }}>
              <div style={{ fontSize: 28, fontWeight: 720 }}>{t}</div>
              <Screen src={`clips/tutorial_${k}.mp4`} width={500} rate={1.6} />
            </div>
          </Rise>
        ))}
      </div>
      <div style={{ position: "absolute", right: 130, top: 300, display: "grid", gap: 22 }}>
        <Rise at={T("tasks") - 6.2}><div style={{ fontSize: 30, color: C.muted, fontWeight: 650 }}>Every step is one of</div></Rise>
        {kinds.map((k, i) => (
          <Rise key={k} at={T("tasks") - 5.4 + i * 0.7} dist={12}>
            <div style={{ fontFamily: MONO, fontSize: 46, color: C.contract, background: C.contractSoft, padding: "10px 26px", borderRadius: 12 }}>{k}</div>
          </Rise>
        ))}
      </div>
    </Page>
  );
};

/* 9: results */
const Bar: React.FC<{ name: string; s: number; n: number; col: string; at: number }> = ({ name, s, n, col, at }) => {
  const p = useIn(at, 1.0);
  return (
    <div style={{ display: "grid", gridTemplateColumns: "400px 1fr 150px", alignItems: "center", gap: 26, opacity: Math.min(1, p * 3) }}>
      <div style={{ fontSize: 34, fontWeight: 650 }}>{name}</div>
      <div style={{ height: 38, background: "rgba(20,33,48,.07)", borderRadius: 8, overflow: "hidden" }}>
        <div style={{ width: `${(n ? s / n : 0) * 100 * p}%`, height: "100%", background: col, borderRadius: 8 }} />
      </div>
      <div style={{ fontSize: 40, fontWeight: 800, textAlign: "right", fontVariantNumeric: "tabular-nums" }}>{`${Math.round(s * p)}/${n}`}</div>
    </div>
  );
};
const Results: React.FC = () => {
  const r = story.results as any;
  const block = (title: string, d: any, at: number) => (
    <div style={{ display: "grid", gap: 18 }}>
      <Rise at={at}><div style={{ fontSize: 36, fontWeight: 760 }}>{title}</div></Rise>
      <Bar name="Copying the clicks" s={d.replay[0]} n={d.replay[1]} col={C.muted} at={at + 0.6} />
      <Bar name="EIDOS, checks off" s={d.nochk[0]} n={d.nochk[1]} col="#8a96a6" at={at + 1.1} />
      <Bar name="EIDOS" s={d.eidos[0]} n={d.eidos[1]} col={C.contract} at={at + 1.6} />
    </div>
  );
  return (
    <Page>
      <Rise at={0.1}><div style={H2}>Measured on held-out tests</div></Rise>
      <Rise at={0.5}><div style={{ ...BODY, fontSize: 30, marginTop: 8 }}>New values, random redesigns, a different app, and mid-task interruptions, drawn from seeds kept aside and run once. Judged from each app's internal state, which the agent never sees.</div></Rise>
      <div style={{ display: "grid", gap: 44, marginTop: 40 }}>
        {block(r.everyday.title, r.everyday, r.at1)}
        {block(r.sheet.title, r.sheet, r.at2)}
      </div>
      <Rise at={r.at3} style={{ marginTop: 40 }}>
        <div style={{ display: "flex", gap: 60, fontSize: 34, flexWrap: "wrap" }}>
          <div><b style={{ color: C.pass }}>{r.agree}</b> times its own verdict matched the truth</div>
          <div>Interrupted: <b style={{ color: C.contract }}>{r.int_eidos}</b> with checks, <b style={{ color: C.fail }}>{r.int_nochk}</b> without</div>
        </div>
      </Rise>
    </Page>
  );
};

/* 11: why it's different */
const Unique: React.FC = () => {
  const rows: [string, string, string][] = [
    ["Video as a hint", "Video compiled into a program", "2.0"],
    ["Breaks when the app changes", "Finds targets by label, carries across apps", "8.0"],
    ["Says “done” either way", "Checks every step, and knows when it failed", "11.4"],
  ];
  return (
    <AbsoluteFill style={{ background: DARK.bg }}>
      <BrollBackdrop src="broll/shot07.mp4" dim={0.7} />
      <Page bg="transparent">
        <Rise at={0.1}><div style={{ ...H2, color: DARK.ink }}>What makes it different</div></Rise>
        <div style={{ display: "grid", gap: 30, marginTop: 60 }}>
          {rows.map(([a, b, at]) => (
            <Rise key={a} at={+at}>
              <div style={{ display: "grid", gridTemplateColumns: "640px 80px 1fr", alignItems: "center", fontSize: 44 }}>
                <div style={{ color: DARK.muted, textDecoration: "line-through", textDecorationColor: DARK.fail }}>{a}</div>
                <div style={{ color: DARK.muted }}>→</div>
                <div style={{ color: DARK.ink, fontWeight: 760 }}>{b}</div>
              </div>
            </Rise>
          ))}
        </div>
        <Rise at={T("unique") - 4.0} style={{ marginTop: 70 }}><div style={{ ...H2, fontSize: 58, color: DARK.pass }}>An agent you can depend on.</div></Rise>
      </Page>
    </AbsoluteFill>
  );
};

/* 12 */
const Models: React.FC = () => {
  const rows: [string, string][] = [
    ["SAM 3.1", "finds what's on the screen: pointer, fields, buttons, what changed"],
    ["Muse Spark", "understands what each step was for"],
    ["Muse Wonder", "compiles the steps into a program with contracts"],
  ];
  return (
    <Page>
      <Rise at={0.1}><div style={H2}>Designed around Meta's models</div></Rise>
      <div style={{ display: "grid", marginTop: 50, background: C.surface, borderRadius: 16, border: `1px solid ${C.line}`, overflow: "hidden" }}>
        {rows.map(([m, job], i) => (
          <Rise key={m} at={2.0 + i * 1.6} dist={12}>
            <div style={{ display: "grid", gridTemplateColumns: "360px 1fr", gap: 30, padding: "30px 40px", borderTop: i ? `1px solid ${C.line}` : "none" }}>
              <div style={{ fontSize: 44, fontWeight: 800 }}>{m}</div>
              <div style={{ fontSize: 36, color: C.muted, lineHeight: 1.3 }}>{job}</div>
            </div>
          </Rise>
        ))}
      </div>
      <Rise at={T("meta") - 7.5} style={{ marginTop: 36 }}>
        <div style={{ fontSize: 30, color: C.muted, maxWidth: 1500 }}>Everything in this video ran offline, with classic computer vision standing in for each model, so every result can be reproduced.</div>
      </Rise>
    </Page>
  );
};

/* 13 */
const Close: React.FC = () => {
  const p = useIn(2.8, 0.9);
  return (
    <AbsoluteFill style={{ background: DARK.bg }}>
      <BrollBackdrop src="broll/shot09.mp4" dim={0.55} />
      <Page bg="transparent">
        <div style={{ margin: "auto 0", display: "grid", gap: 28 }}>
          <Rise at={0.1}><div style={{ ...H2, color: DARK.muted }}>Prompting is how we talk to AI.</div></Rise>
          <Rise at={1.5}><div style={{ ...H2, color: DARK.ink }}>Showing is how we'll teach it.</div></Rise>
          <div style={{ position: "relative", width: "fit-content", padding: "12px 34px", marginTop: 44, opacity: p }}>
            <Contract x={0} y={0} w={0} h={0} fill ok={p > 0.95} />
            <div style={{ ...H1, fontSize: 130, letterSpacing: "0.12em", fontVariationSettings: '"wdth" 125', position: "relative", color: DARK.ink }}>EIDOS</div>
          </div>
          <div style={{ fontSize: 30, color: DARK.muted, opacity: p }}>Maruthi Kunchala, Team Parallax. Meta Global AI Hackathon 2026.</div>
          <div style={{ fontSize: 20, color: DARK.muted, opacity: p * 0.8 }}>Cinematic shots generated with Higgsfield. All EIDOS footage is real and unedited.</div>
        </div>
      </Page>
    </AbsoluteFill>
  );
};

const PAD: Record<string, number> = { hook: 0.9, problem: 0.7, name: 0.8, watch: 2.5, understand: 1.2, otherapp: 3.0, interrupt: 3.0, tasks: 1.2, results: 2.0, robot: 4.0, unique: 1.2, meta: 0.8, close: 2.5 };
const MIN: Record<string, number> = {
  otherapp: 2.0 + 1.0 + Math.max(clipLen("other_replay"), clipLen("other_eidos")) + 2.2,
  interrupt: 2.0 + 1.0 + Math.max(clipLen("int_nochk"), clipLen("int_eidos")) + 2.2,
  watch: 2.0 + 0.6 + 19.4,
};
export const storySeconds = (id: string) => Math.max(T(id) + (PAD[id] ?? 0.8), MIN[id] ?? 0);
export const storyTotal = () => timeline.reduce((a, s) => a + storySeconds(s.id), 0);

const SCENES: Record<string, React.FC> = {
  hook: Hook, problem: Problem, name: Name,
  watch: () => <WithIntro src="broll/shot04.mp4" title="Learning from one video."><Watch /></WithIntro>,
  understand: Understand,
  otherapp: () => <WithIntro src="broll/shot05.mp4" title="Somewhere the video never went."><Split heading="A different mail app, in dark mode, fields reordered." sub="Same skill, same video. New values for this run."
    left={["Copying the clicks", "other_replay", clipLen("other_replay"), "Nothing was sent"]} right={["EIDOS", "other_eidos", clipLen("other_eidos"), "Sent, every step checked"]} /></WithIntro>,
  interrupt: () => <WithIntro src="broll/shot06.mp4" title="When something gets in the way."><Split heading="A dialog pops up and swallows the keystrokes." sub="Both agents run the same skill. Only one checks its work."
    left={["EIDOS, checks off", "int_nochk", clipLen("int_nochk"), "Said done. Nothing was sent."]} right={["EIDOS", "int_eidos", clipLen("int_eidos"), "Noticed, cleared it, redid the step"]} /></WithIntro>,
  tasks: Tasks,
  results: Results,
  robot: () => <WithIntro src="broll/shot08.mp4" title="The same idea, off the screen." seconds={3} label="Generated illustration"><Robot /></WithIntro>,
  unique: Unique, meta: Models, close: Close,
};

export const Story: React.FC = () => {
  const { fps } = useVideoConfig();
  return (
    <AbsoluteFill style={{ background: C.paper }}>
      <Series>
        {timeline.map((s) => {
          const Scene = SCENES[s.id];
          return (
            <Series.Sequence key={s.id} durationInFrames={Math.round(storySeconds(s.id) * fps)} name={s.id}>
              <Scene />
              <Audio src={staticFile(`vo3/${s.id}.wav`)} />
              <Caption text={s.text} seconds={s.seconds} />
            </Series.Sequence>
          );
        })}
      </Series>
    </AbsoluteFill>
  );
};
