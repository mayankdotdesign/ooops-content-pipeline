// Calibrated from Remotion's Social Safe Zones reference overlay
// (elements/overlays/social-safe-zones -- a real capture-based IG Reels
// interface image, not a guess) at 1080x1920, 2026-09-22.
//
// Top chrome (status bar + back/search icons):  y = 0-230
// Right action rail (like/comment/share/save):  x = 910-1010, y = 1110-1830
// Bottom chrome (username/caption/nav pill):     y = 1780+
//
// SAFE_RIGHT is deliberately well inside 910 -- text runs right-to-left-
// ragged (left-aligned), so the danger is a LONG line's right edge
// drifting into the icon rail, not just the box boundary.
export const SAFE_TOP = 260;
export const SAFE_BOTTOM = 1740;
export const SAFE_LEFT = 80;
export const SAFE_RIGHT = 900; // canvas is 1080 wide -> 180px right margin
export const SAFE_CENTER_Y = (SAFE_TOP + SAFE_BOTTOM) / 2;
