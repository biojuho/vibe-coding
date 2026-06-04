import { readFile } from "node:fs/promises";
import path from "node:path";

// Shared path resolution + error mapping for the authenticated /api/data/*
// routes. Keeping this outside next/server makes the file-read branches easy to
// exercise in node:test.
export const DATA_DIR_ENV = "KNOWLEDGE_DASHBOARD_DATA_DIR";

export type JsonFileResult =
	| { status: 200; data: unknown }
	| { status: 404; error: string }
	| { status: 500; error: string };

export function getDashboardDataDir(): string {
	const configured = process.env[DATA_DIR_ENV]?.trim();
	if (configured) {
		return path.resolve(configured);
	}
	return path.join(process.cwd(), "data");
}

export function dashboardDataFile(filename: string): string {
	const configured = process.env[DATA_DIR_ENV]?.trim();
	if (configured) {
		return path.join(path.resolve(configured), filename);
	}
	return path.join(process.cwd(), "data", filename);
}

export async function readJsonFileResult(
	absPath: string,
	notFoundMessage: string,
): Promise<JsonFileResult> {
	let raw: string;
	try {
		raw = await readFile(absPath, "utf8");
	} catch (error) {
		if ((error as NodeJS.ErrnoException).code === "ENOENT") {
			return { status: 404, error: notFoundMessage };
		}
		console.error(`Error reading ${absPath}:`, error);
		return { status: 500, error: "Internal Server Error" };
	}

	try {
		return { status: 200, data: JSON.parse(raw) };
	} catch (error) {
		// Never surface raw file contents in the error body.
		console.error(`Error parsing ${absPath}:`, error);
		return { status: 500, error: "Internal Server Error" };
	}
}
