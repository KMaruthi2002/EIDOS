import React from "react";
import { AbsoluteFill, Series, staticFile, useVideoConfig } from "remotion";
import { Audio } from "@remotion/media";
import timeline from "./timeline.json";
import { Caption, C } from "./ui";
import { Close, Hook, Models, Name, Problem, Results, Robot, Runs, Understand, Watch } from "./scenes";
import { WithIntro } from "./cinema";

// Extra time after each voiceover so scenes can breathe (seconds).
// Scenes that open on a generated shot get 2 s more (the shot overlaps the content by 0.5 s).
const PAD: Record<string, number> = { hook: 0.8, problem: 0.7, name: 0.8, watch: 4.2, understand: 0.8, redesign: 3.6, otherapp: 9.5, interrupt: 3.5, results: 3.0, robot: 4.5, meta: 0.8, close: 2.2 };

export const sceneSeconds = (id: string) => {
  const t = timeline.find((s) => s.id === id)!;
  return t.seconds + (PAD[id] ?? 0.8);
};
export const totalSeconds = () => timeline.reduce((a, s) => a + sceneSeconds(s.id), 0);

const SCENES: Record<string, React.FC> = {
  hook: Hook,
  problem: Problem,
  name: Name,
  watch: () => <WithIntro src="broll/shot04.mp4" title="Learning from one video."><Watch /></WithIntro>,
  understand: Understand,
  redesign: () => <WithIntro src="broll/shot05.mp4" title="Now, somewhere the video never went."><Runs which="redesign" heading="The app was redesigned." sub="Dark theme, a sidebar, bigger cells, and the columns shuffled." leftTitle="Copying the clicks" leftVerdict="Wrong cells, no sum" rightVerdict="Done: =SUM(A2:A11), checked" /></WithIntro>,
  otherapp: () => <Runs which="other_app" heading="A different app entirely." sub="Jspreadsheet: different toolbar, different layout, rows numbered differently." leftTitle="Copying the clicks" leftVerdict="Formula breaks: #ERROR" rightVerdict="Done: =SUM(E1:E10), checked" />,
  interrupt: () => <WithIntro src="broll/shot06.mp4" title="When something gets in the way."><Runs which="interrupt" heading="Interrupted mid-task." sub="A dialog pops up and swallows input until it is dismissed." leftTitle="EIDOS with checks off" leftVerdict="Carried on blindly: task failed" rightVerdict="Noticed, dismissed, redid the step" /></WithIntro>,
  results: () => <WithIntro src="broll/shot07.mp4" title="Measured, not claimed."><Results /></WithIntro>,
  robot: () => <WithIntro src="broll/shot08.mp4" title="The same idea, off the screen." seconds={3} label="Generated illustration"><Robot /></WithIntro>,
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
