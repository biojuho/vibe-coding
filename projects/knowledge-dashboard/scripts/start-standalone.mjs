import { spawn } from "node:child_process";
import { cp, mkdir, readdir, stat } from "node:fs/promises";
import path from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { pathToFileURL } from "node:url";

const projectRoot = process.cwd();
const standaloneRoot = path.join(projectRoot, ".next", "standalone");
const appSlug = "knowledge-dashboard";
export const COPY_RETRY_ATTEMPTS = 3;
const COPY_RETRY_DELAY_MS = 250;

async function exists(filePath) {
	try {
		await stat(filePath);
		return true;
	} catch {
		return false;
	}
}

async function findStandaloneServer() {
	const candidates = [
		path.join(standaloneRoot, "server.js"),
		path.join(standaloneRoot, "projects", appSlug, "server.js"),
	];

	for (const candidate of candidates) {
		if (await exists(candidate)) {
			return candidate;
		}
	}

	const matches = [];
	async function walk(dir) {
		let entries = [];
		try {
			entries = await readdir(dir, { withFileTypes: true });
		} catch {
			return;
		}

		for (const entry of entries) {
			const entryPath = path.join(dir, entry.name);
			if (entry.isDirectory()) {
				if (entry.name !== "node_modules") {
					await walk(entryPath);
				}
			} else if (entry.name === "server.js") {
				matches.push(entryPath);
			}
		}
	}

	await walk(standaloneRoot);
	if (matches.length > 0) {
		return matches.sort((left, right) => left.length - right.length)[0];
	}

	throw new Error("Standalone server not found. Run `npm run build` first.");
}

export function isMissingSourceDuringCopy(error) {
	return (
		typeof error === "object" &&
		error !== null &&
		"code" in error &&
		error.code === "ENOENT"
	);
}

async function copyIfExists(source, destination) {
	if (!(await exists(source))) {
		return false;
	}

	await mkdir(path.dirname(destination), { recursive: true });
	for (let attempt = 1; attempt <= COPY_RETRY_ATTEMPTS; attempt += 1) {
		try {
			await cp(source, destination, { recursive: true, force: true });
			return true;
		} catch (error) {
			if (
				!isMissingSourceDuringCopy(error) ||
				attempt === COPY_RETRY_ATTEMPTS ||
				!(await exists(source))
			) {
				throw error;
			}
			await sleep(COPY_RETRY_DELAY_MS);
		}
	}
	return true;
}

async function prepareStaticAssets(serverPath) {
	const serverDir = path.dirname(serverPath);
	await copyIfExists(
		path.join(projectRoot, "public"),
		path.join(serverDir, "public"),
	);
	await copyIfExists(
		path.join(projectRoot, ".next", "static"),
		path.join(serverDir, ".next", "static"),
	);
}

async function prepareRuntimeDependencies(serverPath) {
	const serverDir = path.dirname(serverPath);
	await copyIfExists(
		path.join(projectRoot, "node_modules", "@swc", "helpers"),
		path.join(serverDir, "node_modules", "@swc", "helpers"),
	);
	await copyIfExists(
		path.join(projectRoot, "node_modules", "next", "dist", "lib"),
		path.join(serverDir, "node_modules", "next", "dist", "lib"),
	);
	await copyIfExists(
		path.join(projectRoot, "node_modules", "@next", "env"),
		path.join(serverDir, "node_modules", "@next", "env"),
	);
}

export async function resolveStandaloneServer() {
	const serverPath = await findStandaloneServer();
	await prepareStaticAssets(serverPath);
	await prepareRuntimeDependencies(serverPath);
	return serverPath;
}

export async function main() {
	const serverPath = await resolveStandaloneServer();
	const env = {
		...process.env,
		KNOWLEDGE_DASHBOARD_DATA_DIR:
			process.env.KNOWLEDGE_DASHBOARD_DATA_DIR ?? path.join(projectRoot, "data"),
	};
	const child = spawn(process.execPath, [serverPath], {
		env,
		stdio: "inherit",
	});

	for (const signal of ["SIGINT", "SIGTERM"]) {
		process.on(signal, () => {
			child.kill(signal);
		});
	}

	child.on("exit", (code) => {
		process.exit(code ?? 0);
	});
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
	main().catch((error) => {
		console.error(error.message);
		process.exit(1);
	});
}
