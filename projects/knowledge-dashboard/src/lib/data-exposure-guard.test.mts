import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

// Security invariant (ADR-023): authenticated /api/data/* routes must read from
// server-side data/ storage, never public/ web assets. The route shells enforce
// auth and delegate all path selection to the shared helper below.
const ROUTE_FILES = [
	"src/app/api/data/dashboard/route.ts",
	"src/app/api/data/qaqc/route.ts",
	"src/app/api/data/readiness/route.ts",
	"src/app/api/data/skills/route.ts",
];

test("every data route resolves under data/ and never public/", async () => {
	const helperSource = await readFile(
		path.join(process.cwd(), "src/lib/dashboard-data.ts"),
		"utf8",
	);
	assert.match(
		helperSource,
		/"data"/,
		"dashboard-data helper must default to the data/ directory",
	);
	assert.doesNotMatch(
		helperSource,
		/"public"/,
		"dashboard-data helper must NOT default to public/",
	);

	for (const rel of ROUTE_FILES) {
		const source = await readFile(path.join(process.cwd(), rel), "utf8");
		assert.match(
			source,
			/dashboardDataFile/,
			`${rel} must use the shared data path helper`,
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
