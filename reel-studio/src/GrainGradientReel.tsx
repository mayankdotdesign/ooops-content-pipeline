import {
  AbsoluteFill,
  Audio,
  Sequence,
  cancelRender,
  continueRender,
  delayRender,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { useEffect, useState } from "react";
import { ShaderGrainGradient } from "@/components/remocn/shader-grain-gradient";
import { PaperSlides } from "./PaperSlides";
import manifest from "./emojiManifest.json";
import { ensureFontsLoaded } from "./fonts";

// remocn's WebGL grain-gradient shader in Ooops' own palette. Revised
// 2026-09-22: the previous version used the shader's default `shape`
// ("corners") at speed=0.4 with two near-identical coral hues -- read as
// a flat wash sliding in one direction, not a living gradient. Switched
// to shape="blob" (paper-design/shaders' organic, non-linear preset),
// restored a natural speed, and spread the palette across three stops
// (deep coral -> mid coral -> pale peach) so the motion reads as color
// actually moving, not a tint drifting sideways. Text uses the same
// letter-by-letter PaperWobble treatment as PaperReel (shared
// PaperHookText), not the smooth HookText from the first draft.
//
// Second pass (per feedback): the blob's own curved edge was visible
// inside the frame, reading as a sticker rather than an ambient wash.
// scale/intensity/softness/colorBack are exposed as live Studio controls
// (Root.tsx's schema) so "increase the spread" can be dialed in by eye,
// same workflow as PaperReel's opacity/blend-mode controls -- starting
// point here pushes scale way up (blob's boundary lands off-canvas),
// drops intensity (softer band transitions), and maxes softness.
// colorBack switched from near-white to Ooops' actual light-background
// tone (sampled from assets/backgrounds/BG1.png's average, not a guess).
//
// Third pass (2026-09-22): `colors` and `speed` promoted from hardcoded
// constants to props -- per feedback that every grain-gradient post
// looked identical, Root.tsx now rotates through a few distinct presets
// (different scale/speed/color mix) instead of every post sharing one
// hardcoded look.
export const GrainGradientReel: React.FC<{
  slides: string[];
  scale: number;
  intensity: number;
  softness: number;
  speed: number;
  colors: string[];
  colorBack: string;
  musicSrc: string;
}> = ({ slides, scale, intensity, softness, speed, colors, colorBack, musicSrc }) => {
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

  const audioVolume = interpolate(
    frame,
    [0, 10, durationInFrames - 20, durationInFrames],
    [0, 0.4, 0.4, 0],
    { extrapolateRight: "clamp" },
  );

  return (
    <AbsoluteFill style={{ backgroundColor: colorBack }}>
      <Sequence name="1. Grain gradient shader (scale/intensity/softness/colorBack below)" layout="none">
        <ShaderGrainGradient
          shape="blob"
          speed={speed}
          scale={scale}
          colors={colors}
          colorBack={colorBack}
          softness={softness}
          intensity={intensity}
          noise={0.15}
        />
      </Sequence>

      {/* Dark-brown/maroon text (design_system.py's watermark maroon),
          not HookText's coral/cream -- coral text would disappear into
          the coral shader. */}
      <Sequence name="2. Text (letter-wobble)" layout="none">
        {fontsReady && (
          <PaperSlides
            slides={slides}
            bgVariant={1}
            manifest={manifest}
            colorOverride="#83261B"
          />
        )}
      </Sequence>

      <Sequence name="3. Music" from={0}>
        <Audio src={musicSrc} volume={audioVolume} />
      </Sequence>
    </AbsoluteFill>
  );
};
