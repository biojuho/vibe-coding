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
