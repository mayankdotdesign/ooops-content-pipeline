import { loadFont } from "@remotion/fonts";
import { staticFile } from "remotion";

let loaded: Promise<unknown> | null = null;

// Registers the brand font (Nunito Bold, the only weight render_hook
// uses) so it's ready before the first frame renders -- without this the
// text falls back to a system sans-serif for a flash of frames (or, on a
// headless CI renderer with no fallback sans installed, indefinitely).
export const ensureFontsLoaded = () => {
  if (!loaded) {
    loaded = loadFont({
      family: "Nunito",
      url: staticFile("fonts/Nunito-Bold.ttf"),
      weight: "700",
    });
  }
  return loaded;
};
