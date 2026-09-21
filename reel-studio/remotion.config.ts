/**
 * Note: When using the Node.JS APIs, the config file
 * doesn't apply. Instead, pass options directly to the APIs.
 *
 * All configuration options: https://remotion.dev/docs/config
 */

import path from "node:path";
import { Config } from "@remotion/cli/config";
import { enableTailwind } from "@remotion/tailwind-v4";

Config.setRspack(true);
Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);

// "@/*" -> "src/*" so remocn components (which import "@/components/remocn/...")
// resolve at bundle time, matching the same alias in tsconfig.json (type-check
// only). Must use process.cwd(), not __dirname -- Remotion transpiles this
// config file into its own CLI bundle, so __dirname here resolves inside
// node_modules/@remotion/cli, not the project root.
Config.overrideBundlerConfig((currentConfig) => {
  const withTailwind = enableTailwind(currentConfig);
  withTailwind.resolve = withTailwind.resolve ?? {};
  withTailwind.resolve.alias = {
    ...(withTailwind.resolve.alias ?? {}),
    "@": path.join(process.cwd(), "src"),
  };
  return withTailwind;
});
