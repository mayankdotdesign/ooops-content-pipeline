import {
  AbsoluteFill,
  Audio,
  Img,
  Sequence,
  cancelRender,
  continueRender,
  delayRender,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { useEffect, useState } from "react";
import { Grain } from "./Grain";
import { HookText } from "./HookText";
import manifest from "./emojiManifest.json";
import { ensureFontsLoaded } from "./fonts";

// Background and text are two independent layers (2026-09-21, per
// request) -- the background is a full-bleed 9:16 gradient with its own
// slow Ken Burns zoom, and the text is real DOM text (HookText) animating
// in per-word, not a flattened PNG. Previous version pasted the whole
// already-rendered static post as one image; this version only reuses
// the background gradient asset and re-implements render_hook's exact
// typographic spec (font/size/tracking/margins/color) so brand output
// stays identical while the text can move independently of the backdrop.
export const OoopsReel: React.FC<{
  text: string;
  bgVariant: 1 | 2;
  bgSrc: string;
}> = ({ text, bgVariant, bgSrc }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const [fontsReady, setFontsReady] = useState(false);

  useEffect(() => {
    const handle = delayRender("Loading Nunito");
    ensureFontsLoaded()
      .then(() => {
        setFontsReady(true);
        continueRender(handle);
      })
      .catch((err) => cancelRender(err));
  }, []);

  const zoom = interpolate(frame, [0, durationInFrames], [1, 1.1], {
    extrapolateRight: "clamp",
  });

  const audioVolume = interpolate(
    frame,
    [0, 10, durationInFrames - 20, durationInFrames],
    [0, 0.4, 0.4, 0],
    { extrapolateRight: "clamp" },
  );

  return (
    <AbsoluteFill style={{ backgroundColor: "#FFFAF8" }}>
      {/* Background layer */}
      <AbsoluteFill>
        <Img
          src={bgSrc}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            transform: `scale(${zoom})`,
          }}
        />
      </AbsoluteFill>

      {/* Text layer -- independent of the background's zoom */}
      {fontsReady && (
        <HookText text={text} bgVariant={bgVariant} manifest={manifest} />
      )}

      {/* Grain layer -- above everything */}
      <Grain opacity={0.05} />

      <Sequence from={0}>
        <Audio src={staticFile("carefree.mp3")} volume={audioVolume} />
      </Sequence>
    </AbsoluteFill>
  );
};
