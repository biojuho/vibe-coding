// Shared file-read + error-mapping for the /api/data/* routes. Extracted so the
// ENOENT→404 / parse-error→500 / ok→200 branches are unit-testable without
// importing next/server (which the bare node:test runtime cannot load). The
// routes become thin auth+adapter shells over this helper.
import { readFile } from "node:fs/promises";

export type JsonFileResult =
	| { status: 200; data: unknown }
	| { status: 404; error: string }
	| { status: 500; error: string };

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
