import "./index.css";
import { Composition, staticFile } from "remotion";
import { z } from "zod";
import { OoopsReel } from "./OoopsReel";
import { PaperReel } from "./PaperReel";
import { GrainGradientReel } from "./GrainGradientReel";
import { JarBanter, JAR_BANTER_MESSAGES } from "./JarBanter";
import { paperSlidesDuration } from "./PaperSlides";
import reelPosts from "./reelPosts.json";
import { imessageChatFlowDuration } from "@/components/remocn/imessage-chat-flow";

const FPS = 30;

// All standard CSS mix-blend-mode values that make sense on a texture
// overlay (excludes hue/saturation/color/luminosity -- those need a
// colored top layer to do anything useful; paper's grain is monochrome).
const BLEND_MODES = [
  "normal",
  "multiply",
  "screen",
  "overlay",
  "darken",
  "lighten",
  "color-dodge",
  "color-burn",
  "hard-light",
  "soft-light",
  "difference",
  "exclusion",
] as const;

// Live-adjustable in Studio's Props panel (2026-09-22, per request): drag
// the opacity slider and switch blend modes without touching code, then
// report back the value that looks right. `slides` (2026-09-22, real-post
// batch): a carousel post (e.g. id 14's 3-slide arc) needs more than one
// text block in sequence -- see PaperSlides. `musicSrc` is a staticFile()
// path so real batches can rotate tracks per post instead of one hardcoded
// file.
const paperReelSchema = z.object({
  slides: z.array(z.string()),
  bgVariant: z.union([z.literal(1), z.literal(2)]),
  bgSrc: z.string(),
  paperOpacity: z.number().min(0).max(1).step(0.01),
  paperBlendMode: z.enum(BLEND_MODES),
  musicSrc: z.string(),
});

// Same live-control workflow for the grain gradient's "how spread out is
// the blob" tuning (2026-09-22, per feedback: the blob's edge was
// visible as a hard curve instead of blending smoothly).
const grainGradientReelSchema = z.object({
  slides: z.array(z.string()),
  scale: z.number().min(0.5).max(8).step(0.05),
  intensity: z.number().min(0).max(1).step(0.01),
  softness: z.number().min(0).max(1).step(0.01),
  speed: z.number().min(0.1).max(3).step(0.05),
  colors: z.array(z.string()),
  colorBack: z.string(),
  musicSrc: z.string(),
});

const POST_17_TEXT =
  "said bye at the airport. found three notes in my bag before I even got through security. ✈️\n\ncrying in the TSA line is a whole LDR thingy nobody warns you about. 😭";

const JAR_TEXT = "you owe the jar. settle at month end. 🫙";

// Third pass on the grain gradient (2026-09-22): scale=8 (the second-pass
// value) turned out to blow full coral coverage across the WHOLE
// duration with no cream visible at any point -- higher scale zooms the
// blob shape itself up, covering more of the frame, the opposite of what
// "increase the spread" (meaning: soften the edge) needed. Dialed back to
// a scale that keeps the blob's edge soft (still high softness) while
// guaranteeing cream shows through at every point in the animation, not
// just some frames -- verified with `npx remotion still` at several
// frames across the duration, not just one, since the requirement is
// "at least 25% visible at any moment," not "looks fine at frame 0."
//
// Fourth pass (2026-09-22, per feedback: every grain-gradient post
// looked identical): rotated into a small set of distinct presets --
// different scale/speed/softness/intensity AND a different color mix
// per preset, not just the same look copy-pasted. Each was individually
// eyeballed the same way (multiple `remotion still` frames) to keep the
// "light background visible at every moment" guarantee before being
// added here -- don't add a new preset without doing that check.
type GrainPreset = {
  scale: number;
  intensity: number;
  softness: number;
  speed: number;
  colors: string[];
};

const GRAIN_PRESETS: GrainPreset[] = [
  {
    scale: 1.3,
    intensity: 0.15,
    softness: 0.9,
    speed: 1.3,
    colors: ["#EA4330", "#F2765F", "#FFD9CC"],
  },
  {
    scale: 1.6,
    intensity: 0.12,
    softness: 0.85,
    speed: 0.85,
    colors: ["#F2765F", "#EA4330"],
  },
  {
    scale: 1.0,
    intensity: 0.2,
    softness: 0.95,
    speed: 1.7,
    colors: ["#EA4330", "#FFD9CC", "#F2765F"],
  },
];

// A generous hold after the scripted exchange settles, so the last
// bubble/reaction doesn't cut off the instant it lands.
const JAR_BANTER_HOLD_FRAMES = 45;

// The first real-post Reels batch (2026-09-22): queue ids 12-18, template
// alternating paper (light/coral) <-> grain-gradient so the batch doesn't
// look identical post to post, matched by mood per angle -- not a fixed
// rotation. Source text is copied verbatim from content_queue/queue.json
// at render time, not retyped from memory.
type RealPost = {
  id: number;
  template: "paper-light" | "paper-coral" | "grain";
  music: string;
  stagger: number;
  slides: string[];
  ctaLine?: string;
};

// Generated from content_queue/queue.json (each item's `reel` block + its
// slide text) instead of retyped here -- 2026-09-25, after hand-copying
// 5 posts' text into this file in the first batch. Regenerate it whenever
// queue.json's reel plan or copy changes; never edit reelPosts.json by
// hand. Music history: owies-ukulele/smile were dropped for sounding
// childish (docs/pipeline-walkthrough.md).
const REAL_POSTS: RealPost[] = reelPosts as RealPost[];

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="OoopsReel"
        component={OoopsReel}
        durationInFrames={FPS * 8}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={{
          text: POST_17_TEXT,
          bgVariant: 1 as const,
          bgSrc: staticFile("bg.png"),
        }}
      />

      <Composition
        id="PaperReel"
        component={PaperReel}
        fps={FPS}
        width={1080}
        height={1920}
        schema={paperReelSchema}
        calculateMetadata={({ props }) => ({
          durationInFrames: paperSlidesDuration(props.slides),
        })}
        defaultProps={{
          slides: [POST_17_TEXT],
          bgVariant: 1 as const,
          bgSrc: staticFile("bg.png"),
          paperOpacity: 1,
          paperBlendMode: "color-burn" as const,
          musicSrc: staticFile("audio/just-keep-walking.mp3"),
        }}
      />

      <Composition
        id="PaperReelCoral"
        component={PaperReel}
        fps={FPS}
        width={1080}
        height={1920}
        schema={paperReelSchema}
        calculateMetadata={({ props }) => ({
          durationInFrames: paperSlidesDuration(props.slides),
        })}
        defaultProps={{
          slides: [POST_17_TEXT],
          bgVariant: 2 as const,
          bgSrc: staticFile("bg2.png"),
          paperOpacity: 1,
          paperBlendMode: "screen" as const,
          musicSrc: staticFile("audio/just-keep-walking.mp3"),
        }}
      />

      <Composition
        id="GrainGradientReel"
        component={GrainGradientReel}
        fps={FPS}
        width={1080}
        height={1920}
        schema={grainGradientReelSchema}
        calculateMetadata={({ props }) => ({
          durationInFrames: paperSlidesDuration(props.slides),
        })}
        defaultProps={{
          slides: [JAR_TEXT],
          ...GRAIN_PRESETS[0],
          colorBack: "#FDDED5",
          musicSrc: staticFile("audio/just-keep-walking.mp3"),
        }}
      />

      {(() => {
        let grainCount = 0;
        return REAL_POSTS.map((post) => {
          if (post.template === "grain") {
            const preset = GRAIN_PRESETS[grainCount % GRAIN_PRESETS.length];
            grainCount += 1;
            return (
              <Composition
                key={post.id}
                id={`Post${post.id}`}
                component={GrainGradientReel}
                fps={FPS}
                width={1080}
                height={1920}
                calculateMetadata={({ props }) => ({
                  durationInFrames: paperSlidesDuration(props.slides, props.stagger),
                })}
                defaultProps={{
                  slides: post.slides,
                  stagger: post.stagger,
                  ...preset,
                  colorBack: "#FDDED5",
                  musicSrc: staticFile(post.music),
                }}
              />
            );
          }
          return (
            <Composition
              key={post.id}
              id={`Post${post.id}`}
              component={PaperReel}
              fps={FPS}
              width={1080}
              height={1920}
              calculateMetadata={({ props }) => ({
                durationInFrames: paperSlidesDuration(props.slides, props.stagger),
              })}
              defaultProps={{
                slides: post.slides,
                stagger: post.stagger,
                ctaLine: post.ctaLine,
                bgVariant: post.template === "paper-coral" ? (2 as const) : (1 as const),
                bgSrc: staticFile(post.template === "paper-coral" ? "bg2.png" : "bg.png"),
                paperOpacity: 1,
                paperBlendMode:
                  post.template === "paper-coral" ? ("screen" as const) : ("color-burn" as const),
                musicSrc: staticFile(post.music),
              }}
            />
          );
        });
      })()}

      <Composition
        id="JarBanter"
        component={JarBanter}
        durationInFrames={
          imessageChatFlowDuration(JAR_BANTER_MESSAGES) + JAR_BANTER_HOLD_FRAMES
        }
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={{
          messages: JAR_BANTER_MESSAGES,
        }}
      />
    </>
  );
};
