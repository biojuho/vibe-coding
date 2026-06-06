export { auth as proxy } from "@/auth";

export const config = {
	matcher: [
		"/((?!login|privacy|terms|subscription/fail|api/auth|api/health|_next/static|_next/image|favicon.ico|manifest.json|icon-192x192.png|icon-512x512.png|sw.js|workbox-.*\\.js).*)",
	],
};
