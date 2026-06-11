import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Don't fail the production build on type errors.
  typescript: { ignoreBuildErrors: true },
};

export default nextConfig;
