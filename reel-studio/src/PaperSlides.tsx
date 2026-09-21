import { AbsoluteFill, Sequence, interpolate, useCurrentFrame } from "remotion";
import { PaperHookText } from "./PaperHookText";
import { EmojiManifest } from "./emoji";

// Sequences N slide texts (a carousel post, e.g. id 14's 3-slide "wet
// towel" arc) through one Reel, each getting an equal time slice of
// SLIDE_DURATION_FRAMES. PaperHookText already fades each word in at the
// start of its slide; this only adds the fade-OUT in the last 10 frames
// before a hard cut to the next slide, so a multi-slide post doesn't just
// jump-cut. Single-slide posts pass a 1-element array and behave exactly
// like the old single-text prop did.
export const SLIDE_DURATION_FRAMES = 150; // 5s @ 30fps

export const paperSlidesDuration = (slideCount: number) =>
  slideCount * SLIDE_DURATION_FRAMES;

export const PaperSlides: React.FC<{
  slides: string[];
  bgVariant: 1 | 2;
  manifest: EmojiManifest;
  colorOverride?: string;
}> = ({ slides, bgVariant, manifest, colorOverride }) => {
  return (
    <>
      {slides.map((slide, i) => (
        <Sequence
          key={i}
          name={`Slide ${i + 1}`}
          from={i * SLIDE_DURATION_FRAMES}
          durationInFrames={SLIDE_DURATION_FRAMES}
          layout="none"
        >
          <SlideFadeOut>
            <PaperHookText
              text={slide}
              bgVariant={bgVariant}
              manifest={manifest}
              colorOverride={colorOverride}
            />
          </SlideFadeOut>
        </Sequence>
      ))}
    </>
  );
};

const SlideFadeOut: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(
    frame,
    [SLIDE_DURATION_FRAMES - 10, SLIDE_DURATION_FRAMES],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );
  return <AbsoluteFill style={{ opacity }}>{children}</AbsoluteFill>;
};
