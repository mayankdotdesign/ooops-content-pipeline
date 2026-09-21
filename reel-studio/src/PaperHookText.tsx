import { staticFile, useCurrentFrame } from "remotion";
import { PaperWobble } from "@/components/remocn/paper-wobble";
import { steppedRamp } from "@/lib/remocn/stop-motion";
import { EmojiManifest, TextRun, splitEmojiRuns } from "./emoji";
import { SAFE_LEFT, SAFE_RIGHT, SAFE_CENTER_Y } from "./safeZone";

// Same typographic spec as HookText (render_hook: Nunito Bold 64px, -3%
// tracking, 100% line-height) but positioned inside the calibrated IG
// Reels safe zone (safeZone.ts) instead of a naive full-frame center, and
// the reveal is QUANTIZED, not smoothly interpolated (2026-09-21/22, per
// request: "paper can animate frame by frame").
//
// Two remocn stop-motion primitives do this:
//   - steppedRamp: each WORD's fade/rise progress jumps between a fixed
//     set of poses instead of gliding -- reveal pacing stays at word
//     granularity so a long sentence doesn't take forever to appear.
//   - PaperWobble: once visible, EVERY LETTER (not the whole word) gets
//     its own independent wobble instance -- corrected 2026-09-22 from an
//     earlier per-word version, which read as rigid blocks moving rather
//     than individual letters hand-placed on paper.
// Both share STEP=3 so text and the paper() background move on the same
// stop-motion cadence, per the remocn skill's "one consistent world"
// guidance.
const FONT_SIZE = 64;
const TRACKING_EM = -0.03;
const LINE_HEIGHT = 1;
const STEP = 3; // ~10 poses/sec @ 30fps -- remocn's stop-motion default
// Exported (2026-09-22, per feedback: reels were cutting off mid-reveal)
// so PaperSlides can compute exactly how many frames a given text needs
// to finish revealing, instead of guessing a fixed slide length that
// happened to be too short for longer posts.
export const STAGGER_FRAMES = 6; // between WORDS (2 poses)
const WORD_RISE_PX = 16;
export const WORD_ANIM_FRAMES = 18;

// Total word count across all paragraphs, in the exact same split order
// PaperHookText itself walks (paragraph.split("\n\n"), then
// paragraph.split(" ")) -- must stay in lockstep with the render loop
// below or the computed duration silently drifts from what actually
// plays.
export const countWords = (text: string): number =>
  text.split("\n\n").reduce((sum, paragraph) => sum + paragraph.split(" ").length, 0);

// The frame at which the LAST word finishes its reveal animation for a
// given text -- the floor for how long a slide showing this text must
// run before it's safe to hold or cut.
export const revealCompleteFrame = (text: string): number =>
  (countWords(text) - 1) * STAGGER_FRAMES + WORD_ANIM_FRAMES;

const letterRuns = (word: string, manifest: EmojiManifest): TextRun[] => {
  // Like splitEmojiRuns but each plain-text run is further split down to
  // individual characters, so every letter (and every emoji, kept whole)
  // becomes its own PaperWobble target.
  const runs: TextRun[] = [];
  for (const run of splitEmojiRuns(word, manifest)) {
    if (run.type === "emoji") {
      runs.push(run);
    } else {
      for (const ch of run.value) {
        runs.push({ type: "text", value: ch });
      }
    }
  }
  return runs;
};

export const PaperHookText: React.FC<{
  text: string;
  bgVariant: 1 | 2;
  manifest: EmojiManifest;
  colorOverride?: string;
}> = ({ text, bgVariant, manifest, colorOverride }) => {
  const frame = useCurrentFrame();
  const color = colorOverride ?? (bgVariant === 1 ? "#EA4330" : "#FFFAF8");
  const paragraphs = text.split("\n\n");

  let wordIndex = 0;

  return (
    <div
      style={{
        position: "absolute",
        left: SAFE_LEFT,
        width: SAFE_RIGHT - SAFE_LEFT,
        top: SAFE_CENTER_Y,
        transform: "translateY(-50%)",
        fontFamily: "Nunito",
        fontWeight: 700,
        fontSize: FONT_SIZE,
        letterSpacing: `${TRACKING_EM}em`,
        lineHeight: LINE_HEIGHT,
        color,
        textAlign: "left",
      }}
    >
      {paragraphs.map((paragraph, pIdx) => (
        <div key={pIdx} style={{ marginBottom: pIdx < paragraphs.length - 1 ? FONT_SIZE * 0.4 : 0 }}>
          {paragraph.split(" ").map((word, wIdx) => {
            const thisWord = wordIndex;
            wordIndex += 1;
            const localFrame = frame - thisWord * STAGGER_FRAMES;
            const progress = steppedRamp(localFrame, 0, WORD_ANIM_FRAMES, {
              step: STEP,
            });
            return (
              <span
                key={wIdx}
                style={{
                  display: "inline-block",
                  opacity: progress,
                  whiteSpace: "nowrap",
                }}
              >
                {letterRuns(word, manifest).map((run, rIdx) => (
                  <PaperWobble
                    key={rIdx}
                    seed={`p${pIdx}-w${wIdx}-l${rIdx}`}
                    amp={1.1}
                    rotAmp={1.4}
                    step={STEP}
                    style={{
                      transform: `translateY(${(1 - progress) * WORD_RISE_PX}px)`,
                    }}
                  >
                    {run.type === "text" ? (
                      <span>{run.value}</span>
                    ) : (
                      <img
                        src={staticFile(`emoji/${run.file}`)}
                        alt=""
                        style={{
                          width: FONT_SIZE * 0.95,
                          height: FONT_SIZE * 0.95,
                          verticalAlign: "-0.15em",
                          display: "inline-block",
                        }}
                      />
                    )}
                  </PaperWobble>
                ))}
                {" "}
              </span>
            );
          })}
        </div>
      ))}
    </div>
  );
};
