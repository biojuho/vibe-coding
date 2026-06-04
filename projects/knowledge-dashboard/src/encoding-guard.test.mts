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
const GUARD_TEST_FILE = "encoding-guard.test.mts";

const COMMON_KOREAN_MOJIBAKE_FRAGMENTS = [
	"以",
	"李⑤",
	"醫낇",
	"肄섏",
	"誘명",
	"蹂",
	"臾몄",
	"源⑤",
	"寃",
	"寃쎄",
	"?쒗",
	"?댁",
	"?꾨",
	"?뚰",
	"?" + "\u317d",
];

const READABLE_KOREAN_COPY_BY_FILE: ReadonlyArray<{
	file: string;
	copy: readonly string[];
}> = [
	{
		file: path.join("app", "page.tsx"),
		copy: [
			"본문으로 건너뛰기",
			"나만의 지식 관리 대시보드",
			"운영 콘솔",
			"지식 현황",
			"QA/QC 현황",
			"활동 타임라인",
		],
	},
	{
		file: path.join("components", "ProductReadinessPanel.tsx"),
		copy: [
			"제품 운영 콘솔",
			"종합 점수",
			"프로젝트",
			"차단됨",
			"워크스페이스 작업",
			"준비된 프로젝트",
			"에이전트 스킬 상태",
			"준비도",
			"통과",
			"실패",
			"미해결 작업",
			"담당자 없음",
			"변경된 파일",
			"깨끗함",
			"문서",
			"필수 파일",
			"다음 작업",
			"워크스페이스 블로커",
		],
	},
];

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

test("no source file contains common Korean mojibake fragments", () => {
	const offenders: string[] = [];

	for (const file of collectSourceFiles(SRC_DIR)) {
		const rel = path.relative(SRC_DIR, file);
		if (rel === GUARD_TEST_FILE) {
			continue;
		}

		const source = readFileSync(file, "utf8");
		const fragments = COMMON_KOREAN_MOJIBAKE_FRAGMENTS.filter((fragment) =>
			source.includes(fragment),
		);
		if (fragments.length > 0) {
			offenders.push(`${rel}: ${fragments.join(", ")}`);
		}
	}

	assert.deepEqual(
		offenders,
		[],
		`Korean mojibake fragments detected (re-save the file as UTF-8):\n${offenders.join(
			"\n",
		)}`,
	);
});

test("product operations copy stays readable Korean", () => {
	const missing: string[] = [];

	for (const { file, copy } of READABLE_KOREAN_COPY_BY_FILE) {
		const source = readFileSync(path.join(SRC_DIR, file), "utf8");
		for (const expected of copy) {
			if (!source.includes(expected)) {
				missing.push(`${file}: ${expected}`);
			}
		}
	}

	assert.deepEqual(
		missing,
		[],
		`Expected Korean operations copy is missing or corrupted:\n${missing.join(
			"\n",
		)}`,
	);
});
