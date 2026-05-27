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

test("audio synthesizer guards browser audio and vibration APIs", () => {
	const source = readSource("lib/audio.js");

	assert.match(source, /let AudioContextClass = null;/);
	assert.match(
		source,
		/try \{\s+AudioContextClass = window\.AudioContext \|\| window\.webkitAudioContext;\s+\} catch \(e\) \{/,
	);
	assert.match(source, /console\.warn\("Audio context access failed:", e\);/);
	assert.match(
		source,
		/try \{\s+audioCtx = new AudioContextClass\(\);\s+\} catch \(e\) \{/,
	);
	assert.match(source, /console\.warn\("Audio context creation failed:", e\);/);
	assert.match(
		source,
		/typeof audioCtx\.resume === "function"[\s\S]*?try \{\s+const resumeResult = audioCtx\.resume\(\);/,
	);
	assert.match(source, /console\.warn\("Audio context resume failed:", e\);/);
	assert.match(source, /let vibrate = null;/);
	assert.match(source, /let navigatorRef = null;/);
	assert.match(
		source,
		/try \{\s+navigatorRef = window\.navigator;\s+vibrate = navigatorRef\?\.vibrate;\s+\} catch \{/,
	);
	assert.match(source, /if \(typeof vibrate !== "function"\) return;/);
	assert.match(source, /vibrate\.call\(navigatorRef, duration\);/);
	assert.doesNotMatch(
		source,
		/typeof window\.navigator\.vibrate === "function"/,
	);
	assert.doesNotMatch(source, /window\.navigator\.vibrate\(duration\);/);
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

test("FieldModeView normalizes persisted checklist state safely", () => {
	const source = readSource("components/widgets/FieldModeView.js");

	assert.match(source, /function createFreshChecklist\(\) \{/);
	assert.match(source, /function normalizeStoredChecklist\(value\) \{/);
	assert.match(source, /function readStoredChecklist\(todayKey\) \{/);
	assert.match(source, /function writeStoredChecklist\(todayKey, checklist\) \{/);
	assert.match(source, /if \(!Array\.isArray\(value\)\) \{/);
	assert.match(source, /return createFreshChecklist\(\);/);
	assert.match(source, /const savedById = new Map/);
	assert.match(source, /DEFAULT_CHECKLIST\.map\(\(item\) => \(\{/);
	assert.match(source, /checked: Boolean\(savedById\.get\(item\.id\)\?\.checked\)/);
	assert.match(source, /return normalizeStoredChecklist\(JSON\.parse\(saved\)\);/);
	assert.match(source, /return readStoredChecklist\(todayKey\);/);
	assert.match(
		source,
		/function readStoredChecklist\(todayKey\) \{[\s\S]*?catch \{\}[\s\S]*?return createFreshChecklist\(\);[\s\S]*?\}/,
	);
	assert.match(
		source,
		/try \{\s*localStorage\.setItem\(todayKey, JSON\.stringify\(checklist\)\);[\s\S]*?\} catch \{\}/,
	);
	assert.match(source, /writeStoredChecklist\(todayKey, fresh\);/);
	assert.match(source, /writeStoredChecklist\(getTodayKey\(\), updated\);/);
	assert.doesNotMatch(source, /return JSON\.parse\(saved\);/);
	assert.doesNotMatch(
		source,
		/localStorage\.setItem\(todayKey, JSON\.stringify\(fresh\)\);/,
	);
});

test("FieldModeView ignores stale full-list loading completions after cleanup", () => {
	const source = readSource("components/widgets/FieldModeView.js");

	assert.match(
		source,
		/useEffect\(\(\) => \{\s+let cancelled = false;[\s\S]*?ensureAllCattleLoaded\(\{ silent: true \}\)/,
	);
	assert.match(
		source,
		/\.finally\(\(\) => \{\s+if \(!cancelled\) \{\s+setLoadingAllCattle\(false\);/,
	);
	assert.match(
		source,
		/return \(\) => \{\s+cancelled = true;\s+\};\s+\}, \[ensureAllCattleLoaded\]\);/,
	);
	assert.doesNotMatch(
		source,
		/\.finally\(\(\) => setLoadingAllCattle\(false\)\)/,
	);
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

	assert.match(source, /현장 점검 준비/);
	assert.match(source, /오프라인 대응/);
	assert.match(source, /현장 점검 화면/);
	assert.match(source, /개체 빠른 검색/);
	assert.match(source, /축사 점검 목록/);
	assert.match(source, /이표 정보 기준 집계/);
	assert.match(source, /기상 경보 확인 필요/);
	assert.match(source, /검색된 개체/);
	assert.match(source, /전체 목록 불러오는 중\.\.\./);
	assert.doesNotMatch(source, /현장 기동성 극대화/);
	assert.doesNotMatch(source, /오프라인 자가생존/);
	assert.doesNotMatch(source, /Smart Field Overlay/);
	assert.doesNotMatch(source, /개체 초고속 검색/);
	assert.doesNotMatch(source, /Tactile stables list/);
	assert.doesNotMatch(source, /이표 검수 100% 완료/);
	assert.doesNotMatch(source, /가축 기상 경보 확인 요망/);
	assert.doesNotMatch(source, /검색 매칭 개체/);
	assert.doesNotMatch(source, /전체 로드 중\.\.\./);
	assert.match(source, /placeholder="이표번호 4자리 또는 개체명 입력"/);
	assert.doesNotMatch(source, /소 이름 입력/);
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
	assert.match(source, /animationId = scheduleFieldModeAnimationFrame\(animate\)/);
});

test("FieldModeView guards celebration animation frame scheduling and cleanup", () => {
	const source = readSource("components/widgets/FieldModeView.js");

	assert.match(
		source,
		/function scheduleFieldModeAnimationFrame\(callback\) \{/,
	);
	assert.match(
		source,
		/try \{\s+return window\.requestAnimationFrame\(callback\);\s+\} catch \(error\) \{/,
	);
	assert.match(
		source,
		/console\.error\("Failed to schedule field mode animation frame:", error\);/,
	);
	assert.match(source, /return null;/);
	assert.match(
		source,
		/function cancelFieldModeAnimationFrame\(animationId\) \{/,
	);
	assert.match(source, /if \(animationId === null\) \{\s+return;\s+\}/);
	assert.match(
		source,
		/try \{\s+window\.cancelAnimationFrame\(animationId\);\s+\} catch \{\}/,
	);
	assert.match(source, /let animationId = null;/);
	assert.match(
		source,
		/useEffect\(\(\) => \{\s+if \(!showCelebration\) return;\s+let cancelled = false;/,
	);
	assert.match(
		source,
		/animationId = scheduleFieldModeAnimationFrame\(animate\);\s+if \(animationId === null\) \{\s+frameFailureTimer = scheduleFieldModeTimer\(\(\) => \{\s+if \(!cancelled\) \{\s+setShowCelebration\(false\);/,
	);
	assert.match(source, /clearFieldModeTimer\(frameFailureTimer\);/);
	assert.match(source, /cancelFieldModeAnimationFrame\(animationId\);/);
	assert.match(
		source,
		/try \{\s+window\.addEventListener\("resize", handleResize\);\s+\} catch \{\}/,
	);
	assert.match(
		source,
		/try \{\s+window\.removeEventListener\("resize", handleResize\);\s+\} catch \{\}/,
	);
	assert.match(
		source,
		/const ctx = canvas\.getContext\("2d"\);\s+if \(!ctx\) \{\s+const closeTimer = scheduleFieldModeTimer\(\(\) => \{\s+if \(!cancelled\) \{\s+setShowCelebration\(false\);/,
	);
	assert.match(
		source,
		/return \(\) => \{\s+cancelled = true;\s+clearFieldModeTimer\(closeTimer\);/,
	);
	assert.match(
		source,
		/return \(\) => \{\s+cancelled = true;\s+try \{\s+window\.removeEventListener\("resize", handleResize\);/,
	);
	assert.match(
		source,
		/const t1 = scheduleFieldModeTimer\(\s+\(\) => \{\s+if \(!cancelled\) \{\s+createFirework\(width \* 0\.25, height \* 0\.6\);/,
	);
	assert.match(
		source,
		/const t2 = scheduleFieldModeTimer\(\s+\(\) => \{\s+if \(!cancelled\) \{\s+createFirework\(width \* 0\.75, height \* 0\.6\);/,
	);
	assert.doesNotMatch(source, /animationId = requestAnimationFrame\(animate\)/);
	assert.doesNotMatch(source, /\n\s*cancelAnimationFrame\(animationId\);/);
	assert.doesNotMatch(source, /window\.addEventListener\("resize", handleResize\);\s+const particles/);
	assert.doesNotMatch(source, /window\.removeEventListener\("resize", handleResize\);\s+cancel/);
	assert.doesNotMatch(
		source,
		/const t1 = scheduleFieldModeTimer\(\s+\(\) => createFirework/,
	);
	assert.doesNotMatch(
		source,
		/const t2 = scheduleFieldModeTimer\(\s+\(\) => createFirework/,
	);
	assert.doesNotMatch(
		source,
		/scheduleFieldModeTimer\(\(\) => \{\s+setShowCelebration\(false\);/,
	);
});

test("FieldModeView guards celebration timer scheduling and cleanup", () => {
	const source = readSource("components/widgets/FieldModeView.js");

	assert.match(source, /function scheduleFieldModeTimer\(callback, delay\) \{/);
	assert.match(source, /function clearFieldModeTimer\(timeoutId\) \{/);
	assert.match(
		source,
		/try \{\s+return window\.setTimeout\(callback, delay\);\s+\} catch \(error\) \{/,
	);
	assert.match(
		source,
		/console\.error\("Failed to schedule field mode celebration timer:", error\);/,
	);
	assert.match(source, /if \(timeoutId === null\) \{\s+return;\s+\}/);
	assert.match(
		source,
		/try \{\s+window\.clearTimeout\(timeoutId\);\s+\} catch \{\}/,
	);
	assert.match(source, /const t1 = scheduleFieldModeTimer\(/);
	assert.match(source, /const t2 = scheduleFieldModeTimer\(/);
	assert.match(
		source,
		/const timer = scheduleFieldModeTimer\(\(\) => \{\s+if \(!cancelled\) \{\s+setShowCelebration\(false\);/,
	);
	assert.match(source, /clearFieldModeTimer\(timer\);/);
	assert.match(source, /clearFieldModeTimer\(t1\);/);
	assert.match(source, /clearFieldModeTimer\(t2\);/);
	assert.doesNotMatch(source, /const t1 = setTimeout\(/);
	assert.doesNotMatch(source, /const t2 = setTimeout\(/);
	assert.doesNotMatch(source, /const timer = setTimeout\(/);
	assert.doesNotMatch(source, /clearTimeout\(timer\);/);
	assert.doesNotMatch(source, /clearTimeout\(t1\);/);
	assert.doesNotMatch(source, /clearTimeout\(t2\);/);
});

test("FieldModeView search results use specific missing-building copy", () => {
	const source = readSource("components/widgets/FieldModeView.js");

	assert.match(
		source,
		/cow\.buildingId \? `\$\{cow\.buildingId\}동` : ["']축사 미지정["']/,
	);
	assert.doesNotMatch(
		source,
		/cow\.buildingId \? `\$\{cow\.buildingId\}동` : ["']미지정["']/,
	);
});
