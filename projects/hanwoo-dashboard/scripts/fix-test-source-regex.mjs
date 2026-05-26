#!/usr/bin/env node
// scripts/fix-test-source-regex.mjs
//
// hanwoo-dashboard 테스트 회귀 자동 수정 도구.
//
// 배경: T-372 Biome 마이그레이션이 src 파일들을 single→double quote로 reformat하면서,
// `assert.match(source, /...'foo'.../)` 같은 source-string 정규식 테스트들이 일괄 fail.
//
// 이 도구는 .test.mjs 파일들의 정규식 리터럴 내부 unescaped single quote를 ["']
// 문자 클래스로 변환하여 두 따옴표 스타일 모두에 매칭되게 한다. 안전한 변환이다 —
// 정규식 의미가 더 관대해지기만 하고, 기존에 매칭되던 single-quote case는 그대로 매칭.
//
// 사용: node scripts/fix-test-source-regex.mjs [--dry-run] [--verbose]

import { promises as fs } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = path.resolve(SCRIPT_DIR, "..", "src");

const args = new Set(process.argv.slice(2));
const DRY_RUN = args.has("--dry-run");
const VERBOSE = args.has("--verbose");
const RELAX_JSX = args.has("--relax-jsx");

async function walk(dir) {
	const entries = await fs.readdir(dir, { withFileTypes: true });
	const files = [];
	for (const entry of entries) {
		const full = path.join(dir, entry.name);
		if (entry.isDirectory()) {
			files.push(...(await walk(full)));
		} else if (entry.isFile() && entry.name.endsWith(".test.mjs")) {
			files.push(full);
		}
	}
	return files;
}

// Match a JS regex literal: /BODY/FLAGS
// BODY allows escaped chars (\.) and disallows unescaped / and newline.
// We deliberately keep this conservative: regex on a single line.
const REGEX_LITERAL = /\/((?:\\.|[^/\\\n])+)\/([gimsuy]*)/g;

function transformRegexBody(body, { relaxJsxSpaces = false } = {}) {
	// Replace each unescaped ' with ["'] character class.
	// Walk char-by-char so we correctly skip \' escapes.
	let out = "";
	let i = 0;
	let changed = false;
	let insideJsxAngle = false;
	while (i < body.length) {
		const ch = body[i];
		if (ch === "\\" && i + 1 < body.length) {
			out += ch + body[i + 1];
			i += 2;
			continue;
		}
		if (ch === "'") {
			out += `["']`;
			changed = true;
			i += 1;
			continue;
		}
		if (relaxJsxSpaces && ch === "<" && /[a-zA-Z\/]/.test(body[i + 1] ?? "")) {
			insideJsxAngle = true;
			out += ch;
			i += 1;
			continue;
		}
		if (relaxJsxSpaces && ch === ">" && insideJsxAngle) {
			insideJsxAngle = false;
			out += ch;
			i += 1;
			continue;
		}
		if (relaxJsxSpaces && insideJsxAngle && ch === " ") {
			// Collapse one or more literal spaces inside a JSX-like opening tag
			// into a single \s+ (newlines + tabs after Biome reformat will match).
			while (body[i] === " ") i += 1;
			out += "\\s+";
			changed = true;
			continue;
		}
		out += ch;
		i += 1;
	}
	return { body: out, changed };
}

function transformSource(source) {
	let totalChanges = 0;
	let totalRegexes = 0;
	const transformed = source.replace(REGEX_LITERAL, (match, body, flags) => {
		totalRegexes += 1;
		const hasQuote = body.includes("'");
		const hasJsxSpace = RELAX_JSX && /<[a-zA-Z\/][^>]* [^>]*>/.test(body);
		if (!hasQuote && !hasJsxSpace) return match;

		// Skip if already contains ["'] alternation — avoid double-wrapping.
		if (hasQuote && /\["']|\['"]/.test(body)) {
			if (!hasJsxSpace) return match;
		}

		const result = transformRegexBody(body, { relaxJsxSpaces: RELAX_JSX });
		if (!result.changed) return match;
		totalChanges += 1;
		return `/${result.body}/${flags}`;
	});
	return { source: transformed, totalChanges, totalRegexes };
}

async function main() {
	const files = await walk(SRC_ROOT);
	let filesChanged = 0;
	let regexesChanged = 0;
	for (const file of files) {
		const original = await fs.readFile(file, "utf8");
		const { source: next, totalChanges, totalRegexes } =
			transformSource(original);
		if (totalChanges === 0) {
			if (VERBOSE) {
				console.log(`skip  ${path.relative(SRC_ROOT, file)} (${totalRegexes} regexes, no quotes)`);
			}
			continue;
		}
		filesChanged += 1;
		regexesChanged += totalChanges;
		if (DRY_RUN) {
			console.log(`would-fix ${path.relative(SRC_ROOT, file)} (+${totalChanges} regex bodies)`);
		} else {
			await fs.writeFile(file, next, "utf8");
			console.log(`fixed     ${path.relative(SRC_ROOT, file)} (+${totalChanges} regex bodies)`);
		}
	}
	console.log("");
	console.log(
		`${DRY_RUN ? "would change" : "changed"} ${filesChanged} file(s), ${regexesChanged} regex bodies (${files.length} test files scanned)`,
	);
}

main().catch((error) => {
	console.error("fix-test-source-regex failed:", error);
	process.exit(1);
});
