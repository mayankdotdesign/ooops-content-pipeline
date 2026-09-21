import { AbsoluteFill, Sequence, interpolate, useCurrentFrame } from "remotion";
import { PaperHookText, revealCompleteFrame } from "./PaperHookText";
import { EmojiManifest } from "./emoji";

// Sequences N slide texts (a carousel post, e.g. id 14's 3-slide "wet
// towel" arc) through one Reel. Each slide's own duration is computed
// from how long ITS text actually takes to finish revealing
// (revealCompleteFrame), plus a fixed HOLD after that, plus a small
// buffer -- fixed 2026-09-22 after reels were cutting off mid-reveal
// (the old flat 150f/slide was long enough for short posts and too
// short for longer ones) and after feedback that fully-revealed text
// needs to sit still and readable for a beat before it disappears, not
// vanish the instant the last letter lands.
const HOLD_FRAMES = 90; // 3s @ 30fps, after the text finishes revealing
const REVEAL_BUFFER_FRAMES = 6; // steppedRamp can land a step or two late
const FADE_OUT_FRAMES = 10;

export const slideDurationFrames = (text: string): number =>
  revealCompleteFrame(text) + REVEAL_BUFFER_FRAMES + HOLD_FRAMES;

export const paperSlidesDuration = (slides: string[]): number =>
  slides.reduce((sum, slide) => sum + slideDurationFrames(slide), 0);

export const PaperSlides: React.FC<{
  slides: string[];
  bgVariant: 1 | 2;
  manifest: EmojiManifest;
  colorOverride?: string;
}> = ({ slides, bgVariant, manifest, colorOverride }) => {
  let cursor = 0;
  return (
    <>
      {slides.map((slide, i) => {
        const duration = slideDurationFrames(slide);
        const from = cursor;
        cursor += duration;
        return (
          <Sequence
            key={i}
            name={`Slide ${i + 1} (${duration}f)`}
            from={from}
            durationInFrames={duration}
            layout="none"
          >
            <SlideFadeOut durationInFrames={duration}>
              <PaperHookText
                text={slide}
                bgVariant={bgVariant}
                manifest={manifest}
                colorOverride={colorOverride}
              />
            </SlideFadeOut>
          </Sequence>
        );
      })}
    </>
  );
};

const SlideFadeOut: React.FC<{ durationInFrames: number; children: React.ReactNode }> = ({
  durationInFrames,
  children,
}) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(
    frame,
    [durationInFrames - FADE_OUT_FRAMES, durationInFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );
  return <AbsoluteFill style={{ opacity }}>{children}</AbsoluteFill>;
};
