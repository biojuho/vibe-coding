export default function robots() {
	const base =
		process.env.NEXTAUTH_URL ||
		process.env.AUTH_URL ||
		"https://hanwoo.joolife.com";

	return {
		rules: [
			{
				userAgent: "*",
				allow: ["/", "/login", "/register", "/terms", "/privacy"],
				disallow: ["/api/", "/admin/", "/subscription"],
			},
		],
		sitemap: `${base}/sitemap.xml`,
	};
}
