// Defense-in-depth: strip any JSON payloads out of public/ before `next build`.
// public/ is web-served WITHOUT auth, so dashboard/QA-QC JSON must never ship
// there (ADR-023). The authenticated data lives in data/ and is served only via
// /api/data/*. This runs as the `prebuild` lifecycle hook so it executes on every
// `npm run build`. It deletes (never fails) — data/ already holds the auth-served
// mirror, so a stray public copy is purely a transient sync artifact.
import { readdir, rm } from "node:fs/promises";
import path from "node:path";

const publicDir = path.join(process.cwd(), "public");

let entries = [];
try {
	entries = await readdir(publicDir);
} catch {
	// No public/ directory — nothing to clean.
	process.exit(0);
}

const jsonFiles = entries.filter((name) => name.toLowerCase().endsWith(".json"));

for (const name of jsonFiles) {
	await rm(path.join(publicDir, name), { force: true });
	console.log(
		`[prebuild] removed non-shippable public/${name} (served without auth — see ADR-023)`,
	);
}

if (jsonFiles.length === 0) {
	console.log("[prebuild] public/ is clean (no JSON payloads to strip)");
}
