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

test("ear tag scanner modal exposes dialog purpose and hides visual-only scanner canvas", () => {
	const source = readSource("components/widgets/EarTagScannerModal.js");

	assert.match(source, /aria-labelledby="scanner-modal-title"/);
	assert.match(source, /aria-describedby="scanner-modal-description"/);
	assert.match(source, /id="scanner-modal-description"/);
	assert.match(
		source,
		/<canvas\s+ref=\{canvasRef\}[\s\S]*?aria-hidden="true"/,
	);
	assert.match(
		source,
		/<Camera size=\{18\} className="animate-pulse" aria-hidden="true" \/>/,
	);
	assert.match(
		source,
		/title="이표 스캐너 닫기"[\s\S]*?aria-label="이표 스캐너 닫기"/,
	);
	assert.doesNotMatch(source, /aria-label="닫기"/);
	assert.match(
		source,
		/className="inline-flex min-h-11 min-w-11 items-center justify-center[\s\S]*?<X size=\{18\} aria-hidden="true" \/>/,
	);
	assert.doesNotMatch(source, /className="p-2 text-muted-foreground/);
	assert.match(source, /<X size=\{18\} aria-hidden="true" \/>/);
});

test("ear tag scanner actions have stable Korean task labels", () => {
	const source = readSource("components/widgets/EarTagScannerModal.js");

	assert.match(
		source,
		/onClick=\{triggerMockScanSuccess\}[\s\S]*?aria-label="이표 자동 인식 실행"[\s\S]*?title="이표 자동 인식 실행"/,
	);
	assert.match(source, /> 이표 자동 인식\s*<\/div>/);
	assert.doesNotMatch(source, /\(Click\)/);
	assert.doesNotMatch(source, /감색/);
	assert.match(
		source,
		/onClick=\{triggerMockScanSuccess\}[\s\S]*?aria-label="모의 이표 스캔 실행"[\s\S]*?title="모의 이표 스캔 실행"/,
	);
	assert.match(
		source,
		/onClick=\{handleRetry\}[\s\S]*?aria-label="이표 다시 스캔하기"[\s\S]*?title="이표 다시 스캔하기"/,
	);
	assert.match(
		source,
		/aria-label=\{`\$\{matchedCow\?\.name \?\? "선택한 개체"\} 상세 정보 보기`\}/,
	);
	assert.match(
		source,
		/title=\{`\$\{matchedCow\?\.name \?\? "선택한 개체"\} 상세 정보 보기`\}/,
	);
});

test("ear tag scanner announces scan results and labels manual simulation choices", () => {
	const source = readSource("components/widgets/EarTagScannerModal.js");

	assert.match(source, /role="status"[\s\S]*?aria-live="polite"/);
	assert.match(source, /aria-atomic="true"/);
	assert.match(source, /인식된 개체 정보가 없습니다/);
	assert.doesNotMatch(source, /인식된 개체 정보 없음/);
	assert.match(source, /등록되지 않은 번호입니다\. 다시 스캔해 주세요\./);
	assert.doesNotMatch(source, /스캔해주십시오/);
	assert.match(
		source,
		/const manualChoiceLabel = `\$\{cow\.name\} 이표번호 끝자리 \$\{String\(cow\.tagNumber\)\.slice\(-4\)\} 개체로 스캐너 결과 지정`;/,
	);
	assert.match(source, /aria-label=\{manualChoiceLabel\}/);
	assert.match(
		source,
		/title=\{manualChoiceLabel\}/,
	);
	assert.match(source, /<Camera size=\{14\} aria-hidden="true" \/>/);
	assert.match(source, /<RefreshCw size=\{13\} aria-hidden="true" \/>/);
	assert.match(source, /<Eye size=\{13\} aria-hidden="true" \/>/);
});

test("ear tag scanner normalizes malformed props and callbacks before rendering", () => {
	const source = readSource("components/widgets/EarTagScannerModal.js");

	assert.match(source, /function normalizeEarTagScannerModalOptions\(options\) \{/);
	assert.match(source, /function normalizeScannerCattleList\(cattleList\) \{/);
	assert.match(
		source,
		/return options && typeof options === ["']object["'] && !Array\.isArray\(options\)\s*\?\s*options\s*:\s*\{\s*\}\s*;?/,
	);
	assert.match(
		source,
		/return Array\.isArray\(cattleList\)[\s\S]*?\? cattleList\.filter\([\s\S]*?\(cow\) => cow && typeof cow === ["']object["'] && !Array\.isArray\(cow\)[\s\S]*?\)[\s\S]*?: \[\s*\]\s*;?/,
	);
	assert.match(source, /export default function EarTagScannerModal\(options = \{\}\) \{/);
	assert.match(source, /normalizeEarTagScannerModalOptions\(options\);/);
	assert.match(source, /const safeCattleList = normalizeScannerCattleList\(cattleList\);/);
	assert.match(
		source,
		/const handleClose = typeof onClose === ["']function["'] \? onClose : \(\) => \{\};/,
	);
	assert.match(
		source,
		/const handleSelect = typeof onSelect === ["']function["'] \? onSelect : \(\) => \{\};/,
	);
	assert.match(
		source,
		/const currentCattleList = normalizeScannerCattleList\(cattleList\);/,
	);
	assert.match(source, /if \(isOpen && currentCattleList\.length > 0\) \{/);
	assert.match(
		source,
		/const idx = Math\.floor\(Math\.random\(\) \* currentCattleList\.length\);/,
	);
	assert.match(source, /setTargetCandidate\(currentCattleList\[idx\]\);/);
	assert.match(source, /const cow = safeCattleList\.find\(\(c\) => c\.id === cowId\);/);
	assert.match(source, /handleSelect\(matchedCow\);/);
	assert.match(source, /handleClose\(\);/);
	assert.match(source, /if \(safeCattleList\.length > 0\) \{/);
	assert.match(source, /setTargetCandidate\(safeCattleList\[idx\]\);/);
	assert.match(source, /safeCattleList\.slice\(0, 5\)\.map\(\(cow\) => \{/);
	assert.doesNotMatch(
		source,
		/export default function EarTagScannerModal\(\{\s+isOpen,/,
	);
	assert.doesNotMatch(source, /onSelect\(matchedCow\);/);
	assert.doesNotMatch(source, /onClose\(\);/);
	assert.doesNotMatch(source, /cattleList\.find\(\(c\) => c\.id === cowId\)/);
	assert.doesNotMatch(source, /cattleList\.slice\(0, 5\)\.map/);
});

test("ear tag scanner explains missing birth dates instead of showing dash placeholders", () => {
	const source = readSource("components/widgets/EarTagScannerModal.js");

	assert.match(source, /function formatScannerBirthDate\(value\) \{/);
	assert.match(source, /return ["']생년월일 미등록["'];/);
	assert.match(source, /Number\.isNaN\(date\.getTime\(\)\)/);
	assert.match(source, /\{formatScannerBirthDate\(matchedCow\?\.birthDate\)\}/);
	assert.doesNotMatch(
		source,
		/matchedCow\?\.birthDate[\s\S]*?:\s*["']-["']/,
	);
});

test("ear tag scanner guards animation frame scheduling and cleanup", () => {
	const source = readSource("components/widgets/EarTagScannerModal.js");

	assert.match(source, /function scheduleScannerFrame\(callback\) \{/);
	assert.match(
		source,
		/try \{\s+return window\.requestAnimationFrame\(callback\);\s+\} catch \(error\) \{/,
	);
	assert.match(
		source,
		/console\.error\("Failed to schedule ear tag scanner frame:", error\);/,
	);
	assert.match(source, /function cancelScannerFrame\(animationId\) \{/);
	assert.match(source, /if \(animationId === null\) \{\s+return;\s+\}/);
	assert.match(
		source,
		/try \{\s+window\.cancelAnimationFrame\(animationId\);\s+\} catch \{\}/,
	);
	assert.match(
		source,
		/function deferScannerTask\(callback\) \{/,
	);
	assert.match(
		source,
		/try \{\s+queueMicrotask\(callback\);\s+\} catch \{\s+Promise\.resolve\(\)\.then\(callback\);/,
	);
	assert.match(
		source,
		/function deferScannerNoMatch\(setScanStatus, shouldApply = \(\) => true\) \{/,
	);
	assert.match(
		source,
		/const applyNoMatch = \(\) => \{\s+if \(shouldApply\(\)\) \{\s+setScanStatus\("no_match"\);/,
	);
	assert.match(
		source,
		/deferScannerTask\(applyNoMatch\);/,
	);
	assert.match(
		source,
		/deferScannerTask\(\(\) => \{\s+if \(cancelled\) \{/,
	);
	assert.match(source, /let cancelled = false;\s+const canvas = canvasRef\.current;/);
	assert.match(source, /cancelScannerFrame\(animationRef\.current\);/);
	assert.match(source, /animationRef\.current = null;/);
	assert.match(
		source,
		/if \(!ctx\) \{\s+deferScannerNoMatch\(setScanStatus, \(\) => !cancelled\);\s+return \(\) => \{\s+cancelled = true;\s+\};/,
	);
	assert.match(
		source,
		/animationRef\.current = scheduleScannerFrame\(render\);\s+if \(animationRef\.current === null && !cancelled\) \{/,
	);
	assert.match(source, /deferScannerNoMatch\(setScanStatus, \(\) => !cancelled\);/);
	assert.match(
		source,
		/return \(\) => \{\s+cancelled = true;\s+cancelScannerFrame\(animationRef\.current\);/,
	);
	assert.doesNotMatch(
		source,
		/animationRef\.current = requestAnimationFrame\(render\);/,
	);
	assert.doesNotMatch(
		source,
		/if \(animationRef\.current\) cancelAnimationFrame\(animationRef\.current\);/,
	);
	assert.doesNotMatch(
		source,
		/queueMicrotask\(\(\) => setScanStatus\("no_match"\)\);/,
	);
	assert.doesNotMatch(
		source,
		/queueMicrotask\(\(\) => \{\s+if \(cancelled\) \{/,
	);
});
