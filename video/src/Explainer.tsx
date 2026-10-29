import React from "react";
import { AbsoluteFill, Series, staticFile, useVideoConfig } from "remotion";
import { Audio } from "@remotion/media";
import timeline from "./timeline.json";
import { Caption, C } from "./ui";
import { Close, Hook, Models, Name, Problem, Results, Runs, Understand, Watch } from "./scenes";

// Extra time after each voiceover so scenes can breathe (seconds).
const PAD: Record<string, number> = { hook: 0.8, problem: 0.7, name: 0.8, watch: 2.2, understand: 0.8, redesign: 1.6, otherapp: 9.5, interrupt: 1.5, results: 1.0, meta: 0.8, close: 2.0 };

export const sceneSeconds = (id: string) => {
  const t = timeline.find((s) => s.id === id)!;
  return t.seconds + (PAD[id] ?? 0.8);
};
export const totalSeconds = () => timeline.reduce((a, s) => a + sceneSeconds(s.id), 0);

const SCENES: Record<string, React.FC> = {
  hook: Hook,
  problem: Problem,
  name: Name,
  watch: Watch,
  understand: Understand,
  redesign: () => <Runs which="redesign" heading="The app was redesigned." sub="Dark theme, a sidebar, bigger cells, and the columns shuffled." leftTitle="Copying the clicks" leftVerdict="Wrong cells, no sum" rightVerdict="Done: =SUM(A2:A11), checked" />,
  otherapp: () => <Runs which="other_app" heading="A different app entirely." sub="Jspreadsheet: different toolbar, different layout, rows numbered differently." leftTitle="Copying the clicks" leftVerdict="Formula breaks: #ERROR" rightVerdict="Done: =SUM(E1:E10), checked" />,
  interrupt: () => <Runs which="interrupt" heading="Interrupted mid-task." sub="A dialog pops up and swallows input until it is dismissed." leftTitle="EIDOS with checks off" leftVerdict="Carried on blindly: task failed" rightVerdict="Noticed, dismissed, redid the step" />,
  results: Results,
  meta: Models,
  close: Close,
};

export const Explainer: React.FC = () => {
  const { fps } = useVideoConfig();
  return (
    <AbsoluteFill style={{ background: C.paper }}>
      <Series>
        {timeline.map((s) => {
          const Scene = SCENES[s.id];
          return (
            <Series.Sequence key={s.id} durationInFrames={Math.round(sceneSeconds(s.id) * fps)} name={s.id}>
              <Scene />
              <Audio src={staticFile(`vo/${s.id}.wav`)} />
              <Caption text={s.text} seconds={s.seconds} />
            </Series.Sequence>
          );
        })}
      </Series>
    </AbsoluteFill>
  );
};
