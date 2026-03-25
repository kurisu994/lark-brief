import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  // serverExternalPackages 用于确保 http-proxy 不被打包
  serverExternalPackages: [],
};

export default nextConfig;
