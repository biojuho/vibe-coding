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

test("qr widget print action uses Korean operator copy and icon button", () => {
	const source = readSource("components/widgets/QRCodeWidget.js");
	assert.match(source, /import \{ useRef, useState \} from ["']react["']/);
	assert.match(
		source,
		/const printButtonLabel = isPrinting\s*\?\s*`\$\{label\} QR 라벨 인쇄 준비 중`\s*:\s*`\$\{label\} QR 라벨 인쇄`;/,
	);
	assert.match(source, /aria-label=\{printButtonLabel\}/);
	assert.match(source, /title=\{printButtonLabel\}/);

	assert.match(source, /QR 출력/);
	assert.match(source, /QR 라벨 인쇄/);
	assert.match(source, /QR 라벨 인쇄 준비 중/);
	assert.match(source, /QR 라벨 인쇄 준비 중\.\.\./);
	assert.match(source, /Joolife 한우 스마트팜/);
	assert.match(source, /import \{ Printer \} from ["']lucide-react["']/);
	assert.match(source, /<button\s+type="button"\s+onClick=\{handlePrint\}/);
	assert.doesNotMatch(source, /QR Code/);
	assert.doesNotMatch(source, /Smart Farm/);
	assert.doesNotMatch(source, /🖨️/);
});

test("qr widget print action blocks duplicate print windows while printing is in flight", () => {
	const source = readSource("components/widgets/QRCodeWidget.js");

	assert.match(source, /const printInFlightRef = useRef\(false\);/);
	assert.match(
		source,
		/const \[isPrinting, setIsPrinting\] = useState\(false\);/,
	);
	assert.match(
		source,
		/const \[printStatusMessage, setPrintStatusMessage\] = useState\(["']["']\);/,
	);
	assert.match(source, /if \(printInFlightRef\.current\) \{/);
	assert.match(source, /printInFlightRef\.current = true;/);
	assert.match(source, /setIsPrinting\(true\);/);
	assert.match(
		source,
		/setPrintStatusMessage\(`\$\{label\} QR 라벨 인쇄 창을 준비하는 중입니다\.`\);/,
	);
	assert.match(
		source,
		/printInFlightRef\.current = false;\s+setIsPrinting\(false\);\s+setPrintStatusMessage\(\s*["']팝업 차단으로 QR 인쇄 창을 열지 못했습니다\. 브라우저 팝업 허용 후 다시 시도해 주세요\.["'],?\s*\);\s+return;/,
	);
	assert.match(
		source,
		/printWindow\.close\(\);\s+printInFlightRef\.current = false;\s+setIsPrinting\(false\);\s+setPrintStatusMessage\(`\$\{label\} QR 라벨 인쇄 창을 열었습니다\.`\);/,
	);
	assert.match(source, /disabled=\{isPrinting\}/);
	assert.match(source, /aria-busy=\{isPrinting\}/);
	assert.doesNotMatch(source, /title=\{isPrinting \?/);
	assert.match(
		source,
		/\{isPrinting \? ["']QR 라벨 인쇄 준비 중\.\.\.["'] : ["']QR 라벨 인쇄["']\}/,
	);
	assert.match(source, /cursor: isPrinting \? ["']wait["'] : ["']pointer["']/);
});

test("qr widget print failures and completion are announced", () => {
	const source = readSource("components/widgets/QRCodeWidget.js");

	assert.match(source, /printStatusMessage && \(/);
	assert.match(source, /role="status"/);
	assert.match(source, /aria-live="polite"/);
	assert.match(source, /aria-atomic="true"/);
	assert.match(source, /\{printStatusMessage\}/);
	assert.match(source, /팝업 차단으로 QR 인쇄 창을 열지 못했습니다/);
	assert.match(source, /브라우저 팝업 허용 후 다시 시도해 주세요/);
	assert.doesNotMatch(source, /브라우저 팝업 허용 후 다시 시도하세요/);
});
