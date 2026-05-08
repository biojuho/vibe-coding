import withSerwist from "@serwist/next";

const enablePWA = process.env.NEXT_ENABLE_PWA === "1";

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  serverExternalPackages: ["bcrypt", "@prisma/adapter-pg"],
  cacheComponents: true,
  experimental: {
    optimizePackageImports: ["lucide-react", "recharts"],
  },
};

const withPWA = enablePWA
  ? withSerwist({
      swSrc: "src/sw.js",
      swDest: "public/sw.js",
      disable: process.env.NODE_ENV === "development",
    })
  : (config) => config;

export default withPWA(nextConfig);
