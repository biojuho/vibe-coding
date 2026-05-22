// sw.js - Suika Daily service worker.
//
// Strategy: cache-first for the app shell so the game is fully playable
// offline. The cache name carries a version; bump it whenever the shipped
// assets change so old caches are purged on activate.

const CACHE_NAME = "suika-daily-v3";
const APP_SHELL = [
	"./",
	"./index.html",
	"./manifest.webmanifest",
	"./icon.svg",
];

self.addEventListener("install", (event) => {
	event.waitUntil(
		caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL)),
	);
	self.skipWaiting();
});

self.addEventListener("activate", (event) => {
	event.waitUntil(
		caches
			.keys()
			.then((keys) =>
				Promise.all(
					keys
						.filter((key) => key !== CACHE_NAME)
						.map((key) => caches.delete(key)),
				),
			),
	);
	self.clients.claim();
});

self.addEventListener("fetch", (event) => {
	const { request } = event;
	// Only handle same-origin GETs; let cross-origin (fonts/CDN) pass through.
	if (request.method !== "GET") return;
	if (new URL(request.url).origin !== self.location.origin) return;

	event.respondWith(
		caches.match(request).then((cached) => {
			if (cached) return cached;
			return fetch(request)
				.then((response) => {
					// Runtime-cache successful basic responses (built JS/CSS).
					if (response.ok && response.type === "basic") {
						const copy = response.clone();
						caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
					}
					return response;
				})
				.catch(() => caches.match("./index.html"));
		}),
	);
});
