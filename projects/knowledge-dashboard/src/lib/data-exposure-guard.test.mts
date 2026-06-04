import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

// Security invariant (ADR-023): the authenticated /api/data/* routes must read
// from data/ (auth-gated), never from public/ (web-served without auth). A path
// regression here would be a silent auth bypass, so we assert the literal path
// in each route source. This is the one place a source-scan is the right test —
// the path string IS the security control.

const ROUTE_FILES = [
	"src/app/api/data/dashboard/route.ts",
	"src/app/api/data/qaqc/route.ts",
	"src/app/api/data/readiness/route.ts",
	"src/app/api/data/skills/route.ts",
];

test("every data route resolves under data/ and never public/", async () => {
	for (const rel of ROUTE_FILES) {
		const source = await readFile(path.join(process.cwd(), rel), "utf8");
		assert.match(
			source,
			/"data"/,
			`${rel} must read from the data/ directory`,
		);
		assert.doesNotMatch(
			source,
			/"public"/,
			`${rel} must NOT read from the web-served public/ directory`,
		);
		assert.match(
			source,
			/isDashboardRequestAuthorized/,
			`${rel} must enforce authentication`,
		);
	}
});

test(".gitignore keeps data/ and public/ JSON payloads out of git", async () => {
	const gitignore = await readFile(
		path.join(process.cwd(), ".gitignore"),
		"utf8",
	);
	assert.match(gitignore, /\/data\/\*\.json/, "data/*.json must be gitignored");
	assert.match(
		gitignore,
		/\/public\/\*\.json/,
		"public/*.json must be gitignored",
	);
});
