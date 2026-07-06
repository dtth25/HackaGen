import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  turbopack: {
    root: path.resolve(__dirname),
  },
  // Default dev/build now runs on Webpack (see package.json "dev" script) — Turbopack's
  // dev-time memory footprint was too high for an 8GB machine. This trades a slight
  // compile-time increase for materially lower peak RSS during `next dev`.
  experimental: {
    webpackMemoryOptimizations: true,
  },
};

export default nextConfig;
