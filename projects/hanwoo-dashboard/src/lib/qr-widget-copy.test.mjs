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
	assert.match(source, /import \{ useEffect, useRef, useState \} from ["']react["']/);
	assert.match(source, /const DEFAULT_QR_LABEL = ["']QR 라벨["'];/);
	assert.match(source, /function normalizeQRCodeWidgetOptions\(options\) \{/);
	assert.match(
		source,
		/options && typeof options === ["']object["'] && !Array\.isArray\(options\)/,
	);
	assert.match(source, /function normalizeQRCodeText\(value, fallback\) \{/);
	assert.match(source, /typeof value === ["']number["'] && Number\.isFinite\(value\)/);
	assert.match(source, /export default function QRCodeWidget\(options = \{\}\) \{/);
	assert.match(
		source,
		/const \{ value, label \} = normalizeQRCodeWidgetOptions\(options\);/,
	);
	assert.match(
		source,
		/const qrLabel = normalizeQRCodeText\(label, DEFAULT_QR_LABEL\);/,
	);
	assert.match(source, /const qrValue = normalizeQRCodeText\(value, qrLabel\);/);
	assert.match(
		source,
		/const printButtonLabel = isPrinting\s*\?\s*`\$\{qrLabel\} QR 라벨 인쇄 준비 중`\s*:\s*`\$\{qrLabel\} QR 라벨 인쇄`;/,
	);
	assert.match(source, /aria-label=\{printButtonLabel\}/);
	assert.match(source, /title=\{printButtonLabel\}/);
	assert.match(source, /<QRCodeSVG value=\{qrValue\} size=\{120\} \/>/);
	assert.doesNotMatch(source, /export default function QRCodeWidget\(\{ value, label \}\)/);

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
	assert.match(source, /const isMountedRef = useRef\(false\);/);
	assert.match(source, /isMountedRef\.current = true;/);
	assert.match(
		source,
		/return \(\) => \{\s+isMountedRef\.current = false;\s+printInFlightRef\.current = false;/,
	);
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
	assert.match(source, /const openPrintWindow = \(\) => \{/);
	assert.match(
		source,
		/return window\.open\("", "", "width=600,height=600"\);/,
	);
	assert.match(source, /console\.error\("Failed to open QR print window:", error\);/);
	assert.match(source, /const printWindow = openPrintWindow\(\);/);
	assert.match(
		source,
		/const resetPrintState = \(\) => \{\s+printInFlightRef\.current = false;\s+if \(isMountedRef\.current\) \{\s+setIsPrinting\(false\);/,
	);
	assert.match(
		source,
		/const updatePrintStatusMessage = \(message\) => \{\s+if \(isMountedRef\.current\) \{\s+setPrintStatusMessage\(message\);/,
	);
	assert.match(
		source,
		/updatePrintStatusMessage\(`\$\{qrLabel\} QR 라벨 인쇄 창을 준비하는 중입니다\.`\);/,
	);
	assert.match(
		source,
		/resetPrintState\(\);\s+updatePrintStatusMessage\(\s*["']팝업 차단으로 QR 인쇄 창을 열지 못했습니다\. 브라우저 팝업 허용 후 다시 시도해 주세요\.["'],?\s*\);\s+return;/,
	);
	assert.match(
		source,
		/try \{\s+printWindow\.focus\(\);\s+printWindow\.print\(\);\s+updatePrintStatusMessage\(`\$\{qrLabel\} QR 라벨 인쇄 창을 열었습니다\.`\);\s+\} catch \(error\) \{/,
	);
	assert.match(
		source,
		/if \(!isMountedRef\.current\) \{\s+printCommitted = true;\s+closePrintWindow\(printWindow\);\s+resetPrintState\(\);\s+return;\s+\}/,
	);
	assert.doesNotMatch(source, /setPrintStatusMessage\(`\$\{qrLabel\} QR 라벨 인쇄 창을 열었습니다\.`\);/);
	assert.match(source, /disabled=\{isPrinting\}/);
	assert.match(source, /aria-busy=\{isPrinting\}/);
	assert.doesNotMatch(source, /title=\{isPrinting \?/);
	assert.match(
		source,
		/\{isPrinting \? ["']QR 라벨 인쇄 준비 중\.\.\.["'] : ["']QR 라벨 인쇄["']\}/,
	);
	assert.match(source, /cursor: isPrinting \? ["']wait["'] : ["']pointer["']/);
	assert.doesNotMatch(
		source,
		/const printWindow = window\.open\("", "", "width=600,height=600"\);/,
	);
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

test("qr widget always unlocks print state when browser print APIs fail", () => {
	const source = readSource("components/widgets/QRCodeWidget.js");

	assert.match(source, /console\.error\("Failed to print QR label:", error\);/);
	assert.match(
		source,
		/updatePrintStatusMessage\(\s*`\$\{qrLabel\} QR 라벨 인쇄를 시작하지 못했습니다\. 다시 시도해 주세요\.`/,
	);
	assert.match(
		source,
		/finally \{\s+closePrintWindow\(printWindow\);\s+resetPrintState\(\);\s+\}/,
	);
	assert.doesNotMatch(
		source,
		/printWindow\.print\(\);\s+printWindow\.close\(\);\s+printInFlightRef\.current = false;/,
	);
});

test("qr widget always unlocks print state when print-window preparation fails", () => {
	const source = readSource("components/widgets/QRCodeWidget.js");

	assert.match(
		source,
		/const closePrintWindow = \(printWindow\) => \{\s+try \{\s+printWindow\.close\(\);\s+\} catch \(error\) \{\s+console\.error\("Failed to close QR print window:", error\);\s+\}\s+\};/,
	);
	assert.match(source, /let printCommitted = false;/);
	assert.match(source, /try \{\s+const doc = printWindow\.document;/);
	assert.match(
		source,
		/const registeredLoadHandler = registerPrintLoadHandler\(\s+printWindow,\s+finishPrint,\s+\);/,
	);
	assert.match(
		source,
		/const scheduledFallback = schedulePrintFallback\(printWindow, finishPrint\);/,
	);
	assert.match(source, /doc\.close\(\);/);
	assert.match(
		source,
		/\} catch \(error\) \{\s+printCommitted = true;\s+console\.error\("Failed to prepare QR print window:", error\);\s+closePrintWindow\(printWindow\);\s+resetPrintState\(\);\s+updatePrintStatusMessage\(\s*`\$\{qrLabel\} QR 라벨 인쇄 창을 준비하지 못했습니다\. 다시 시도해 주세요\.`/,
	);
	assert.match(
		source,
		/try \{[\s\S]*?const doc = printWindow\.document;[\s\S]*?doc\.close\(\);[\s\S]*?\} catch \(error\) \{/,
	);
});

test("qr widget guards print fallback timer scheduling", () => {
	const source = readSource("components/widgets/QRCodeWidget.js");

	assert.match(
		source,
		/const schedulePrintFallback = \(printWindow, finishPrint\) => \{\s+try \{\s+printWindow\.setTimeout\(finishPrint, 120\);\s+return true;\s+\} catch \(error\) \{/,
	);
	assert.match(
		source,
		/console\.error\("Failed to schedule QR print fallback:", error\);/,
	);
	assert.match(source, /return false;/);
	assert.match(source, /schedulePrintFallback\(printWindow, finishPrint\);/);
	assert.doesNotMatch(
		source,
		/printWindow\.addEventListener\("load", finishPrint, \{ once: true \}\);\s+printWindow\.setTimeout\(finishPrint, 120\);/,
	);
});

test("qr widget guards print load listener registration", () => {
	const source = readSource("components/widgets/QRCodeWidget.js");

	assert.match(
		source,
		/const registerPrintLoadHandler = \(printWindow, finishPrint\) => \{\s+try \{\s+printWindow\.addEventListener\("load", finishPrint, \{ once: true \}\);\s+return true;\s+\} catch \(error\) \{/,
	);
	assert.match(
		source,
		/console\.error\("Failed to register QR print load handler:", error\);/,
	);
	assert.match(
		source,
		/const registeredLoadHandler = registerPrintLoadHandler\(\s+printWindow,\s+finishPrint,\s+\);/,
	);
	assert.match(
		source,
		/const scheduledFallback = schedulePrintFallback\(printWindow, finishPrint\);/,
	);
	assert.match(
		source,
		/if \(!registeredLoadHandler && !scheduledFallback\) \{\s+finishPrint\(\);\s+\}/,
	);
	assert.doesNotMatch(
		source,
		/printWindow\.addEventListener\("load", finishPrint, \{ once: true \}\);\s+schedulePrintFallback\(printWindow, finishPrint\);/,
	);
});
