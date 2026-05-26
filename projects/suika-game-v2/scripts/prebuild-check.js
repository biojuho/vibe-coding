/* global process */
import cp from "node:child_process";
import fs from "node:fs";
import path from "node:path";

const cwd = process.cwd();
const normalized = path.normalize(cwd);
const hasNonAscii = Array.from(normalized).some((char) => char.codePointAt(0) > 127);
const shouldUseAsciiFallback = hasNonAscii && process.platform === "win32";
const extraArgs = process.argv.slice(2);

const sourceNodeModules = path.join(cwd, "node_modules");
const asciiTempCandidates = [
	"C:\\Temp",
	"C:\\TEMP",
	path.join(process.cwd().replace(/:\\.*/, ":\\Temp"), "ViteBuild"),
];

function getAsciiTempBase() {
	for (const candidate of asciiTempCandidates) {
		const cleaned = path.normalize(candidate);
		try {
			if (!fs.existsSync(cleaned)) {
				fs.mkdirSync(cleaned, { recursive: true });
			}
			const real = fs.realpathSync(cleaned);
			if (/^[\x00-\x7F]+$/.test(real)) {
				return real.endsWith(path.sep) ? real : `${real}${path.sep}`;
			}
		} catch {
			// Ignore and continue.
		}
	}
	return `${path.join("C:", "Temp")}${path.sep}`;
}

function runViteBuild(targetCwd, outputDir = null, viteRoot = targetCwd) {
	const viteBinary = path.join(
		viteRoot,
		"node_modules",
		"vite",
		"bin",
		"vite.js",
	);
	const args = [viteBinary, "build"];
	if (outputDir) {
		args.push("--outDir", outputDir);
	}
	args.push(...extraArgs);
	const result = cp.spawnSync(process.execPath, args, {
		cwd: targetCwd,
		stdio: "inherit",
	});
	if (result.error) {
		throw result.error;
	}
	return result.status ?? 0;
}

function copyForFallback(targetRoot) {
	const exclude = new Set([".git", "dist", "node_modules", ".tmp"]);
	fs.cpSync(cwd, targetRoot, {
		recursive: true,
		filter(sourcePath) {
			const base = path.basename(sourcePath);
			return !exclude.has(base);
		},
	});

	const tempNodeModules = path.join(targetRoot, "node_modules");
	if (fs.existsSync(sourceNodeModules)) {
		fs.symlinkSync(sourceNodeModules, tempNodeModules, "junction");
	}
}

function copyOutDist(sourceRoot, destinationRoot) {
	const sourceDist = path.join(sourceRoot, "dist");
	const targetDist = path.join(destinationRoot, "dist");
	if (!fs.existsSync(sourceDist)) return;

	const result = cp.spawnSync(
		"robocopy",
		[
			sourceDist,
			targetDist,
			"/E",
			"/MIR",
			"/NFL",
			"/NDL",
			"/NJH",
			"/NJS",
			"/NP",
		],
		{ stdio: "inherit" },
	);
	if (result.error) {
		throw result.error;
	}
	if ((result.status ?? 0) > 7) {
		throw new Error(`robocopy failed with exit code ${result.status}`);
	}
}

function cleanupTempWorkspace(tempRoot) {
	try {
		if (fs.existsSync(tempRoot)) {
			fs.rmSync(tempRoot, { recursive: true, force: true });
		}
	} catch {
		// Ignore final cleanup errors to avoid masking build result.
	}
}

if (shouldUseAsciiFallback) {
	console.warn("[WARN] Non-ASCII characters detected in project path.");
	console.warn(`[WARN] Current path: ${normalized}`);
	const directStatus = runViteBuild(cwd);
	console.error(`[WARN] Direct build exit status: ${directStatus}`);
	if (directStatus === 0) {
		process.exit(0);
	}

	console.error("[ERROR] Direct Vite build failed. Running fallback in a temporary ASCII workspace.");
	const tempBase = getAsciiTempBase();
	const tempRoot = fs.mkdtempSync(path.join(tempBase, "vite-build-"));
	let status = 1;
	try {
		copyForFallback(tempRoot);
		status = runViteBuild(tempRoot, null, tempRoot);
		console.error(`[WARN] Fallback build exit status: ${status}`);
		const fallbackHasDist = fs.existsSync(path.join(tempRoot, "dist"));
		console.error(`[WARN] Fallback dist exists: ${fallbackHasDist}`);
		if (status === 0 || fallbackHasDist) {
			if (!fallbackHasDist) {
				throw new Error("Vite reported success but did not produce a fallback dist directory.");
			}
			copyOutDist(tempRoot, cwd);
			console.error("[WARN] Copied fallback dist to source project.");
			status = 0;
		} else {
			console.error("[ERROR] Vite build failed in temporary ASCII workspace.");
		}
	} catch (error) {
		console.error("[ERROR] ASCII fallback build failed.");
		console.error(error instanceof Error ? error.message : String(error));
		status = 1;
	} finally {
		cleanupTempWorkspace(tempRoot);
	}
	process.exit(status);
}

process.exit(runViteBuild(cwd));

