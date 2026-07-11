import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  devIndicators: false,
  output: "standalone",
  turbopack: {
    root: path.resolve(__dirname),
  },
  // Default dev/build now runs on Webpack (see package.json "dev" script) — Turbopack's
  // dev-time memory footprint was too high for an 8GB machine. This trades a slight
  // compile-time increase for materially lower peak RSS during `next dev`.
  experimental: {
    webpackMemoryOptimizations: true,
  },
  async rewrites() {
    // Server-side proxy for /api/* so the browser only ever calls this frontend's own
    // origin — lets the backend stay unpublished to the internet in prod (see
    // docker-compose.yml's BACKEND_INTERNAL_URL). Only engages when a page actually
    // fetches a relative /api/* path; local dev with an explicit (non-blank)
    // NEXT_PUBLIC_API_BASE_URL calls the backend directly and never hits this.
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.BACKEND_INTERNAL_URL || "http://localhost:8000"}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
