const CACHE_PREFIXES = ["serwist-", "workbox-"];

// NEXT_ENABLE_PWA=1 builds replace this fallback with the Serwist precache bundle.
self.addEventListener("install", () => {
	self.skipWaiting();
});

self.addEventListener("activate", (event) => {
	event.waitUntil(
		(async () => {
			const keys = await self.caches.keys();
			await Promise.all(
				keys
					.filter((key) =>
						CACHE_PREFIXES.some((prefix) => key.startsWith(prefix)),
					)
					.map((key) => self.caches.delete(key)),
			);
			await self.clients.claim();
		})(),
	);
});
