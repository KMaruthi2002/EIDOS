import { Composition } from "remotion";
import { Explainer, totalSeconds } from "./Explainer";

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="EidosExplainer"
      component={Explainer}
      durationInFrames={Math.round(totalSeconds() * 30)}
      fps={30}
      width={1920}
      height={1080}
    />
  );
};
