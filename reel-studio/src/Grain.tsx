import { AbsoluteFill, useCurrentFrame } from "remotion";

// Subtle animated film-grain overlay. feTurbulence reseeded per frame (a
// small deterministic cycle, not truly random, so re-renders are
// reproducible) gives it a flickering "alive" texture instead of a single
// static noise pattern pasted over the video. Desaturated + low opacity so
// it reads as texture, not visible colored static.
export const Grain: React.FC<{ opacity?: number }> = ({ opacity = 0.05 }) => {
  const frame = useCurrentFrame();
  const seed = frame % 8;

  return (
    <AbsoluteFill style={{ mixBlendMode: "overlay", opacity, pointerEvents: "none" }}>
      <svg width="100%" height="100%">
        <filter id="grain-filter">
          <feTurbulence
            type="fractalNoise"
            baseFrequency="0.85"
            numOctaves={2}
            seed={seed}
            stitchTiles="stitch"
          />
          <feColorMatrix type="saturate" values="0" />
          <feComponentTransfer>
            <feFuncA type="linear" slope="0.9" />
          </feComponentTransfer>
        </filter>
        <rect width="100%" height="100%" filter="url(#grain-filter)" />
      </svg>
    </AbsoluteFill>
  );
};
