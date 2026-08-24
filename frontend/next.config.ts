import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // "standalone" is needed for the Docker deploy (see Dockerfile) but breaks
  // Vercel's own build/output tracing — only apply it outside Vercel's builder.
  output: process.env.VERCEL ? undefined : "standalone",
};

export default nextConfig;
