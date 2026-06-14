export default function sitemap() {
	const base = process.env.NEXTAUTH_URL || process.env.AUTH_URL || "https://hanwoo.joolife.com";
	const now = new Date().toISOString();

	return [
		{ url: base, lastModified: now, changeFrequency: "weekly", priority: 1.0 },
		{ url: `${base}/register`, lastModified: now, changeFrequency: "monthly", priority: 0.9 },
		{ url: `${base}/login`, lastModified: now, changeFrequency: "monthly", priority: 0.8 },
		{ url: `${base}/terms`, lastModified: now, changeFrequency: "yearly", priority: 0.3 },
		{ url: `${base}/privacy`, lastModified: now, changeFrequency: "yearly", priority: 0.3 },
	];
}
