import path from "path";

/** @type {import('next').NextConfig} */
const nextConfig = {

  serverExternalPackages: [
    "@cline/sdk",
    "@cline/core",
    "@cline/agents",
    "@cline/llms",
    "@cline/shared",
  ],
};

export default nextConfig;
