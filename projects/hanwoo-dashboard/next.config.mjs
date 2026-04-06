// import withSerwist from "@serwist/next";  // Disabled: Turbopack incompatibility in Next.js 16

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  experimental: {
    optimizePackageImports: ["lucide-react", "recharts"],
  },
};

// const withPWA = withSerwist({
//   swSrc: "src/sw.js",
//   swDest: "public/sw.js",
//   disable: process.env.NODE_ENV === "development",
// });

export default nextConfig;
