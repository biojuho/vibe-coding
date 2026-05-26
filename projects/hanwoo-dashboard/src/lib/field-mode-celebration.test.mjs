import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = path.resolve(__dirname, "..");

function readSource(relativePath) {
	return readFileSync(path.join(SRC_ROOT, relativePath), "utf8");
}

test("audio synthesizer library exports playTriumphantChime", () => {
	const source = readSource("lib/audio.js");

	assert.match(source, /export function playTriumphantChime\s*\(/);
	assert.match(source, /const notes\s*=\s*\[\s*261\.63\s*,\s*329\.63\s*,\s*392(\.0+)?\s*,\s*523\.25\s*\]/);
	assert.match(source, /notes\.forEach\(/);
	assert.match(source, /osc\.connect\(gain\)/);
	assert.match(source, /gain\.connect\(ctx\.destination\)/);
});

test("FieldModeView imports playTriumphantChime and sets up celebration refs", () => {
	const source = readSource("components/widgets/FieldModeView.js");

	assert.match(source, /playTriumphantChime/);
	assert.match(
		source,
		/const \[showCelebration, setShowCelebration\] = useState\(false\)/,
	);
	assert.match(source, /const celebrationCanvasRef = useRef\(null\)/);
});

test("FieldModeView triggers playTriumphantChime and celebration state when checklist becomes 100% completed", () => {
	const source = readSource("components/widgets/FieldModeView.js");

	assert.match(
		source,
		/const previouslyCompletedAll\s*=\s*checklist\s*\.\s*length\s*>\s*0\s*&&\s*checklist\s*\.\s*every/,
	);
	assert.match(
		source,
		/const currentlyCompletedAll\s*=\s*updated\s*\.\s*length\s*>\s*0\s*&&\s*updated\s*\.\s*every/,
	);
	assert.match(
		source,
		/if\s*\(\s*!previouslyCompletedAll\s*&&\s*currentlyCompletedAll\s*\)\s*\{/,
	);
	assert.match(source, /allCompletedAfterToggle = true;/);
	assert.match(source, /if \(allCompletedAfterToggle\) \{/);
	assert.match(source, /playTriumphantChime\(\)/);
	assert.match(source, /setShowCelebration\(true\)/);
});

test("FieldModeView mounts the celebration canvas with mixBlendMode screen", () => {
	const source = readSource("components/widgets/FieldModeView.js");

	assert.match(source, /\{showCelebration && \(/);
	assert.match(source, /ref=\{celebrationCanvasRef\}/);
	assert.match(source, /style=\{\{\s*mixBlendMode:\s*["']screen["']\s*\}\}/);
});

test("FieldModeView announces full-list loading in search results", () => {
	const source = readSource("components/widgets/FieldModeView.js");

	assert.match(source, /\{loadingAllCattle && \(/);
	assert.match(source, /role="status"/);
	assert.match(source, /aria-live="polite"/);
	assert.match(
		source,
		/<Camera size=\{20\} strokeWidth=\{2\.5\} aria-hidden="true" \/>/,
	);
	assert.match(
		source,
		/<AlertTriangle[\s\S]*?className="mx-auto mb-2 text-amber-500\/40"[\s\S]*?aria-hidden="true"[\s\S]*?\/>/,
	);
});

test("FieldModeView controls expose matching title copy", () => {
	const source = readSource("components/widgets/FieldModeView.js");

	assert.match(source, /placeholder="이표번호 4자리 또는 소 이름 입력"/);
	assert.doesNotMatch(source, /소이름/);
	assert.match(
		source,
		/aria-label="개체 이름 또는 이표번호로 검색"[\s\S]*?title="개체 이름 또는 이표번호로 검색"/,
	);
	assert.match(
		source,
		/aria-label="일반 대시보드 모드로 돌아가기"[\s\S]*?title="일반 대시보드 모드로 돌아가기"[\s\S]*?<ArrowLeft size=\{14\} aria-hidden="true" \/>/,
	);
	assert.match(
		source,
		/aria-label="검색어 지우기"[\s\S]*?title="검색어 지우기"/,
	);
	assert.match(
		source,
		/const checklistProgressLabel = `\$\{checklistStats\.checked\}\/\$\{checklistStats\.total\}개 완료`;/,
	);
	assert.match(
		source,
		/aria-valuetext=\{checklistProgressLabel\}[\s\S]*?title=\{checklistProgressLabel\}/,
	);
	assert.match(
		source,
		/const checklistItemLabel = `\$\{item\.title\} \$\{item\.checked \? "완료됨" : "미완료"\} - 점검 완료 상태 변경`;/,
	);
	assert.match(
		source,
		/aria-label=\{checklistItemLabel\}[\s\S]*?title=\{checklistItemLabel\}/,
	);
	assert.match(
		source,
		/aria-label=\{`\$\{cow\.name\} 개체 상세 보기, 이표번호 \$\{formatTagNumber\(cow\.tagNumber\)\}`\}[\s\S]*?title=\{`\$\{cow\.name\} 개체 상세 보기, 이표번호 \$\{formatTagNumber\(cow\.tagNumber\)\}`\}/,
	);
});

test("FieldModeView sets up a beautiful dynamic particle confetti simulation", () => {
	const source = readSource("components/widgets/FieldModeView.js");

	assert.match(source, /useEffect\(\(\) => \{/);
	assert.match(source, /if \(!showCelebration\) return;/);
	assert.match(source, /const particles = \[\];/);
	assert.match(source, /createFirework/);
	assert.match(source, /p\.vy \+= 0\.15/); // gravity
	assert.match(source, /p\.vx \*= 0\.98/); // friction
	assert.match(source, /animationId = requestAnimationFrame\(animate\)/);
});
