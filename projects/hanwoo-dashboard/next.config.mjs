import withSerwist from "@serwist/next";

const enablePWA = process.env.NEXT_ENABLE_PWA === "1";

// Baseline security headers applied to every response. These are the
// breakage-free, high-value ones; a path-scoped Content-Security-Policy is a
// deliberate follow-up because the app relies on inline styles and embeds the
// Toss payment widget, so a wrong CSP would break checkout.
const SECURITY_HEADERS = [
	// This app is never meant to be framed (it handles payments) — block
	// clickjacking. Embedding the Toss widget as a child iframe is unaffected.
	{ key: "X-Frame-Options", value: "DENY" },
	{ key: "X-Content-Type-Options", value: "nosniff" },
	{ key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
	{
		key: "Strict-Transport-Security",
		value: "max-age=63072000; includeSubDomains",
	},
	{
		key: "Permissions-Policy",
		value: "camera=(self), microphone=(), geolocation=(self)",
	},
];

/** @type {import('next').NextConfig} */
const nextConfig = {
	reactStrictMode: true,
	// Emit .next/standalone so the Dockerfile's `node server.js` runtime works;
	// without this the COPY of .next/standalone fails and the image can't build.
	output: "standalone",
	// Pin the file-tracing root to this project so standalone output lands at
	// .next/standalone/server.js. Otherwise Next walks up to a parent lockfile
	// (this project lives inside a larger workspace) and nests server.js under
	// projects/hanwoo-dashboard/, which breaks the Dockerfile's COPY + CMD.
	outputFileTracingRoot: import.meta.dirname,
	allowedDevOrigins: ["127.0.0.1"],
	devIndicators: {
		position: "top-right",
	},
	serverExternalPackages: ["bcrypt", "@prisma/adapter-pg"],
	cacheComponents: true,
	experimental: {
		optimizePackageImports: ["lucide-react", "recharts"],
	},
	async headers() {
		return [{ source: "/(.*)", headers: SECURITY_HEADERS }];
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
