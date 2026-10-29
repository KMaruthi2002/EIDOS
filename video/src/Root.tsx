import { Composition } from "remotion";
import { Explainer, totalSeconds } from "./Explainer";
import { Story, storyTotal } from "./story";

export const RemotionRoot: React.FC = () => {
  return (
    <>
    <Composition
      id="EidosStory"
      component={Story}
      durationInFrames={Math.round(storyTotal() * 30)}
      fps={30}
      width={1920}
      height={1080}
    />
    <Composition
      id="EidosExplainer"
      component={Explainer}
      durationInFrames={Math.round(totalSeconds() * 30)}
      fps={30}
      width={1920}
      height={1080}
    />
    </>
  );
};
