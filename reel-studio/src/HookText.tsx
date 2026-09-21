import { Easing, interpolate, staticFile, useCurrentFrame } from "remotion";
import { EmojiManifest, wordsWithRuns } from "./emoji";

// Reproduces render_hook's exact typographic spec (scripts/design_system.py):
// Nunito Bold 64px, -3% tracking, 100% line-height, 108px margins,
// left-aligned, vertically centered, coral/cream by bg_variant -- so the
// video text matches the already-approved static brand look. Difference
// from the Pillow renderer: word-wrap is left to the browser (no manual
// wrap_tracked port needed) and each word fades/rises in with a stagger,
// per the request to animate text as its own layer instead of pasting a
// flattened image. Stagger (4f) and ease-out entrance follow remocn's
// motion-principles guidance (3-6f sibling stagger, ease-out for entrances,
// avoid linear interpolate on visible motion) -- reviewed 2026-09-21.
const FONT_SIZE = 64;
const MARGIN = 108;
const TRACKING_EM = -0.03;
const LINE_HEIGHT = 1;
const STAGGER_FRAMES = 4;
const WORD_RISE_PX = 14;
const WORD_ANIM_FRAMES = 16;
const WORD_EASING = Easing.out(Easing.cubic);

export const HookText: React.FC<{
  text: string;
  bgVariant: 1 | 2;
  manifest: EmojiManifest;
  startFrame?: number;
  colorOverride?: string;
}> = ({ text, bgVariant, manifest, startFrame = 0, colorOverride }) => {
  const frame = useCurrentFrame() - startFrame;
  const color = colorOverride ?? (bgVariant === 1 ? "#EA4330" : "#FFFAF8");
  const paragraphs = text.split("\n\n");

  let wordIndex = 0;

  return (
    <div
      style={{
        position: "absolute",
        left: MARGIN,
        right: MARGIN,
        top: "50%",
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
          {wordsWithRuns(paragraph, manifest).map((runs, wIdx) => {
            const thisWord = wordIndex;
            wordIndex += 1;
            const localFrame = frame - thisWord * STAGGER_FRAMES;
            const progress = interpolate(localFrame, [0, WORD_ANIM_FRAMES], [0, 1], {
              easing: WORD_EASING,
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            });
            return (
              <span
                key={wIdx}
                style={{
                  display: "inline-block",
                  opacity: progress,
                  transform: `translateY(${(1 - progress) * WORD_RISE_PX}px)`,
                  whiteSpace: "nowrap",
                }}
              >
                {runs.map((run, rIdx) =>
                  run.type === "text" ? (
                    <span key={rIdx}>{run.value}</span>
                  ) : (
                    <img
                      key={rIdx}
                      src={staticFile(`emoji/${run.file}`)}
                      alt=""
                      style={{
                        width: FONT_SIZE * 0.95,
                        height: FONT_SIZE * 0.95,
                        verticalAlign: "-0.15em",
                        display: "inline-block",
                      }}
                    />
                  ),
                )}
                {" "}
              </span>
            );
          })}
        </div>
      ))}
    </div>
  );
};
