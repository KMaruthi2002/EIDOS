import { Composition } from "remotion";
import { Explainer, totalSeconds } from "./Explainer";
import { Story, storyTotal } from "./story";
import { StyleDark, StyleLaunch } from "./styles";
import { Launch, launchFrames } from "./launch";

export const RemotionRoot: React.FC = () => {
  return (
    <>
    <Composition id="EidosLaunch" component={Launch} durationInFrames={launchFrames} fps={30} width={1920} height={1080} />
    <Composition id="StyleDark" component={StyleDark} durationInFrames={300} fps={30} width={1920} height={1080} />
    <Composition id="StyleLaunch" component={StyleLaunch} durationInFrames={300} fps={30} width={1920} height={1080} />
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
