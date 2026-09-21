// TS port of scripts/design_system.py's _split_emoji_runs (longest-match
// against the manifest, not first-match) -- see that file's 2026-09-17
// comment for why longest-match matters: a naive first-match can grab a
// bare codepoint and leave a lone FE0F variation-selector rendering as a
// visible tofu box instead of nothing.
export type EmojiManifest = Record<string, string>;

export type TextRun =
  | { type: "text"; value: string }
  | { type: "emoji"; file: string };

export const splitEmojiRuns = (
  text: string,
  manifest: EmojiManifest,
): TextRun[] => {
  const runs: TextRun[] = [];
  let i = 0;
  let buf = "";
  const flushText = () => {
    if (buf) {
      runs.push({ type: "text", value: buf });
      buf = "";
    }
  };
  while (i < text.length) {
    let matched: string | null = null;
    for (const emoji of Object.keys(manifest)) {
      if (
        text.startsWith(emoji, i) &&
        (matched === null || emoji.length > matched.length)
      ) {
        matched = emoji;
      }
    }
    if (matched) {
      flushText();
      runs.push({ type: "emoji", file: manifest[matched] });
      i += matched.length;
    } else {
      buf += text[i];
      i += 1;
    }
  }
  flushText();
  return runs;
};

// Splits paragraph text into words for per-word stagger animation, each
// word already broken into text/emoji runs. Mirrors
// draw_paragraph/wrap_tracked's text.split("\n\n") -> word.split(" ")
// structure so word boundaries match the Python renderer's.
export const wordsWithRuns = (
  paragraph: string,
  manifest: EmojiManifest,
): TextRun[][] => {
  return paragraph.split(" ").map((word) => splitEmojiRuns(word, manifest));
};
