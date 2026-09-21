import { paper } from "@remotion/effects/paper";
import {
  AbsoluteFill,
  Audio,
  Img,
  Sequence,
  Solid,
  cancelRender,
  continueRender,
  delayRender,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { useEffect, useState } from "react";
import { PaperSlides } from "./PaperSlides";
import manifest from "./emojiManifest.json";
import { ensureFontsLoaded } from "./fonts";

// Paper-vibe variant of OoopsReel (revised 2026-09-22, per feedback): the
// REAL background is our own brand gradient (bg.png, same asset the v2
// template uses) -- paper() is a thin TEXTURE layered on top, not the
// primary background itself. Text is PaperHookText (letter-by-letter
// PaperWobble + quantized word reveal), positioned inside the calibrated
// safe zone.
//
// paperOpacity/paperBlendMode are exposed as live Studio controls (see
// Root.tsx's zod schema for this composition) so the exact texture
// strength can be dialed in by eye in the Props panel rather than
// guessed at in code -- opacity 0.08 read as "not visible" on the first
// pass, this makes it a slider instead of a re-render loop.
export const PaperReel: React.FC<{
  slides: string[];
  bgVariant: 1 | 2;
  bgSrc: string;
  paperOpacity: number;
  paperBlendMode:
    | "normal"
    | "multiply"
    | "screen"
    | "overlay"
    | "darken"
    | "lighten"
    | "color-dodge"
    | "color-burn"
    | "hard-light"
    | "soft-light"
    | "difference"
    | "exclusion";
  musicSrc: string;
}> = ({ slides, bgVariant, bgSrc, paperOpacity, paperBlendMode, musicSrc }) => {
  const frame = useCurrentFrame();
  const { durationInFrames, width, height } = useVideoConfig();
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

  // Paper texture color pair follows the same bg_variant as the real
  // background so the grain reads as part of the same surface, not a
  // mismatched overlay -- cream/coral on the light variant, coral/deeper
  // coral on the dark one.
  const colorFront = bgVariant === 1 ? "#FFFAF8" : "#EA4330";
  const colorBack = bgVariant === 1 ? "#FDE4DE" : "#C7301F";

  const audioVolume = interpolate(
    frame,
    [0, 10, durationInFrames - 20, durationInFrames],
    [0, 0.4, 0.4, 0],
    { extrapolateRight: "clamp" },
  );

  return (
    <AbsoluteFill style={{ backgroundColor: "#FFFAF8" }}>
      {/* Named Sequence wrappers (layout="none" so they don't add their own
          positioning) are the standard Remotion way to label a layer group
          in Studio's timeline -- same pattern the official Social Safe
          Zones element uses. Without this every layer in the timeline
          shows up as the generic tag name (<AbsoluteFill>, <Solid>...),
          impossible to tell apart (2026-09-22, per feedback). */}
      <Sequence name="1. Background gradient" layout="none">
        <AbsoluteFill>
          <Img
            src={bgSrc}
            style={{ width: "100%", height: "100%", objectFit: "cover" }}
          />
        </AbsoluteFill>
      </Sequence>

      <Sequence name="2. Paper grain texture (opacity + blend mode below)" layout="none">
        <AbsoluteFill style={{ opacity: paperOpacity, mixBlendMode: paperBlendMode }}>
          <Solid
            color={colorFront}
            width={width}
            height={height}
            effects={[
              paper({
                colorFront,
                colorBack,
                seed: interpolate(frame, [0, durationInFrames], [0, 1000], {
                  extrapolateLeft: "clamp",
                  extrapolateRight: "clamp",
                  posterize: 30,
                }),
              }),
            ]}
          />
        </AbsoluteFill>
      </Sequence>

      <Sequence name="3. Text (letter-wobble)" layout="none">
        {fontsReady && (
          <PaperSlides slides={slides} bgVariant={bgVariant} manifest={manifest} />
        )}
      </Sequence>

      <Sequence name="4. Music" from={0}>
        <Audio src={musicSrc} volume={audioVolume} />
      </Sequence>
    </AbsoluteFill>
  );
};
