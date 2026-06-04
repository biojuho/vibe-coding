// One-shot pre-deploy / post-deploy sanity check. Verifies the hard runtime
// requirements without booting the server: the API key is configured and the
// data files exist and parse. Exits non-zero on any failure so it can gate a
// deploy step (e.g. `npm run verify-deploy && npm run start`).
import { readFile } from "node:fs/promises";
import path from "node:path";

const dataDir = path.join(process.cwd(), "data");
const REQUIRED_DATA = ["dashboard_data.json"];
const OPTIONAL_DATA = [
	"qaqc_result.json",
	"product_readiness.json",
	"skill_lint.json",
];

const checks = [];

function record(name, ok, detail) {
	checks.push({ name, ok, detail });
}

// 1) API key
record(
	"DASHBOARD_API_KEY configured",
	Boolean(process.env.DASHBOARD_API_KEY?.trim()),
	process.env.DASHBOARD_API_KEY?.trim() ? "set" : "MISSING — routes will 503",
);

// 2) Required + optional data files exist and parse
async function checkJson(file, required) {
	const filePath = path.join(dataDir, file);
	try {
		const raw = await readFile(filePath, "utf8");
		JSON.parse(raw);
		record(`data/${file}`, true, "present & valid JSON");
	} catch (error) {
		const missing = error.code === "ENOENT";
		const ok = !required && missing;
		record(
			`data/${file}`,
			ok,
			missing
				? required
					? "MISSING (required)"
					: "absent (optional — UI degrades gracefully)"
				: `INVALID JSON: ${error.message}`,
		);
	}
}

for (const file of REQUIRED_DATA) {
	await checkJson(file, true);
}
for (const file of OPTIONAL_DATA) {
	await checkJson(file, false);
}

const failed = checks.filter((c) => !c.ok);

console.log("knowledge-dashboard deploy verification");
console.log("=".repeat(42));
for (const c of checks) {
	console.log(`${c.ok ? "PASS" : "FAIL"}  ${c.name} — ${c.detail}`);
}
console.log("=".repeat(42));

if (failed.length > 0) {
	console.error(`${failed.length} check(s) failed.`);
	process.exitCode = 1;
} else {
	console.log("All deploy checks passed.");
}
