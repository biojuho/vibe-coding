import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

// Guards against the cp949↔utf-8 mojibake regression that corrupted the Korean
// fallback strings in page.tsx (isolated Hangul jamo / U+FFFD replacement chars
// leak in when source is re-saved under the wrong codec on the Korean Windows
// host). Ranges are expressed numerically so this guard never trips on itself.
const FORBIDDEN_RANGES: ReadonlyArray<readonly [number, number]> = [
	[0x1100, 0x11ff], // Hangul Jamo (isolated leading/medial/trailing)
	[0x3130, 0x318f], // Hangul Compatibility Jamo (isolated)
	[0xa960, 0xa97f], // Hangul Jamo Extended-A
	[0xd7b0, 0xd7ff], // Hangul Jamo Extended-B
	[0xfffd, 0xfffd], // Unicode replacement character
];

const SOURCE_EXTENSIONS = new Set([".ts", ".tsx", ".mts"]);
const SRC_DIR = path.dirname(fileURLToPath(import.meta.url));

function isForbidden(codePoint: number): boolean {
	return FORBIDDEN_RANGES.some(([lo, hi]) => codePoint >= lo && codePoint <= hi);
}

function collectSourceFiles(dir: string): string[] {
	const out: string[] = [];
	for (const entry of readdirSync(dir, { withFileTypes: true })) {
		const full = path.join(dir, entry.name);
		if (entry.isDirectory()) {
			out.push(...collectSourceFiles(full));
		} else if (SOURCE_EXTENSIONS.has(path.extname(entry.name))) {
			out.push(full);
		}
	}
	return out;
}

test("no source file contains isolated Hangul jamo or replacement characters", () => {
	const offenders: string[] = [];

	for (const file of collectSourceFiles(SRC_DIR)) {
		const lines = readFileSync(file, "utf8").split("\n");
		lines.forEach((line, index) => {
			for (const char of line) {
				const cp = char.codePointAt(0);
				if (cp !== undefined && isForbidden(cp)) {
					const rel = path.relative(SRC_DIR, file);
					offenders.push(
						`${rel}:${index + 1} contains U+${cp
							.toString(16)
							.toUpperCase()
							.padStart(4, "0")}`,
					);
					break;
				}
			}
		});
	}

	assert.deepEqual(
		offenders,
		[],
		`Mojibake detected (re-save the file as UTF-8):\n${offenders.join("\n")}`,
	);
});
