export default function sitemap() {
	const base = process.env.NEXTAUTH_URL || process.env.AUTH_URL || "https://hanwoo.joolife.com";
	const now = new Date().toISOString();

	// Only publicly indexable pages — authenticated and payment pages carry robots:noindex
	return [
		{ url: base, lastModified: now, changeFrequency: "weekly", priority: 1.0 },
		{ url: `${base}/terms`, lastModified: now, changeFrequency: "yearly", priority: 0.4 },
		{ url: `${base}/privacy`, lastModified: now, changeFrequency: "yearly", priority: 0.4 },
	];
}
