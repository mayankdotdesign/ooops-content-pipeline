import { AbsoluteFill, OffthreadVideo, Sequence, staticFile, useCurrentFrame } from "remotion";

// Amateur "edited on my phone" cut of an AI-rendered clip (2026-10-02,
// batch 3): hard cuts, per-segment speed changes, and abrupt punch-in
// zooms, the way the reference reels look when made in Edits/CapCut. No
// transitions, no grading, no audio (the user adds trending audio and IG
// text at upload). Source clips live in public/manual/ with the Gemini
// watermark already removed via ffmpeg delogo; the posts carry IG's AI label.
export type PhoneEditSegment = {
  from: number; // seconds into the source clip
  to: number; // seconds into the source clip
  rate: number; // playback speed
  // Abrupt zoom (no easing) starting `at` seconds into the source clip.
  punch?: { at: number; scale: number; originX: number; originY: number };
};

export type PhoneEditProps = {
  src: string; // path under public/
  segments: PhoneEditSegment[];
};

export const segmentFrames = (s: PhoneEditSegment, fps: number) =>
  Math.round(((s.to - s.from) / s.rate) * fps);

export const phoneEditDuration = (segments: PhoneEditSegment[], fps: number) =>
  segments.reduce((sum, s) => sum + segmentFrames(s, fps), 0);

const Segment: React.FC<{ src: string; seg: PhoneEditSegment; fps: number }> = ({ src, seg, fps }) => {
  const frame = useCurrentFrame();
  const sourceTime = seg.from + (frame / fps) * seg.rate;
  const punched = seg.punch && sourceTime >= seg.punch.at;
  return (
    <AbsoluteFill
      style={{
        transform: punched ? `scale(${seg.punch!.scale})` : undefined,
        transformOrigin: punched ? `${seg.punch!.originX * 100}% ${seg.punch!.originY * 100}%` : undefined,
      }}
    >
      <OffthreadVideo
        src={staticFile(src)}
        startFrom={Math.round(seg.from * fps)}
        endAt={Math.round(seg.to * fps)}
        playbackRate={seg.rate}
        muted
        style={{ width: "100%", height: "100%", objectFit: "cover" }}
      />
    </AbsoluteFill>
  );
};

export const PhoneEdit: React.FC<PhoneEditProps & { fps?: number }> = ({ src, segments, fps = 30 }) => {
  let cursor = 0;
  return (
    <AbsoluteFill style={{ backgroundColor: "black" }}>
      {segments.map((seg, i) => {
        const dur = segmentFrames(seg, fps);
        const from = cursor;
        cursor += dur;
        return (
          <Sequence key={i} name={`Cut ${i + 1} (${seg.from}-${seg.to}s @${seg.rate}x)`} from={from} durationInFrames={dur}>
            <Segment src={src} seg={seg} fps={fps} />
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
