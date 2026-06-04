import type { NextConfig } from "next";

// Content-Security-Policy.
// Next.js injects inline bootstrap/hydration scripts without a nonce unless you
// add nonce middleware, so script-src must allow 'unsafe-inline'. Turbopack uses
// eval in development only, so 'unsafe-eval' is gated to NODE_ENV !== production.
// Inline style ATTRIBUTES (progress bars, recharts widths) require style-src
// 'unsafe-inline'. Everything else is locked to same-origin.
const isDev = process.env.NODE_ENV !== "production";
const contentSecurityPolicy = [
	"default-src 'self'",
	"base-uri 'self'",
	"object-src 'none'",
	"frame-ancestors 'none'",
	"form-action 'self'",
	"img-src 'self' data: blob:",
	"font-src 'self' data:",
	"connect-src 'self'",
	"style-src 'self' 'unsafe-inline'",
	`script-src 'self' 'unsafe-inline'${isDev ? " 'unsafe-eval'" : ""}`,
]
	.join("; ")
	.concat(";");

// Defense-in-depth headers applied to every response. X-Frame-Options +
// frame-ancestors both block clickjacking; the rest harden MIME sniffing,
// referrer leakage, and browser feature access for this internal tool.
const securityHeaders = [
	{ key: "Content-Security-Policy", value: contentSecurityPolicy },
	{ key: "X-Frame-Options", value: "DENY" },
	{ key: "X-Content-Type-Options", value: "nosniff" },
	{ key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
	{ key: "X-DNS-Prefetch-Control", value: "off" },
	{
		key: "Permissions-Policy",
		value: "camera=(), microphone=(), geolocation=(), browsing-topics=()",
	},
	{
		key: "Strict-Transport-Security",
		value: "max-age=63072000; includeSubDomains; preload",
	},
];

const nextConfig: NextConfig = {
	// Smaller, self-contained server bundle for container/Vercel deploys.
	output: "standalone",
	reactStrictMode: true,
	// Do not advertise the framework/version to the world.
	poweredByHeader: false,
	async headers() {
		return [{ source: "/:path*", headers: securityHeaders }];
	},
};

export default nextConfig;
