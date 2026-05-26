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

test("feedback toasts expose live-region semantics and Korean dismiss labels", () => {
	const source = readSource("components/feedback/FeedbackProvider.js");

	assert.match(
		source,
		/const isUrgent\s*=\s*toast\s*\.\s*variant\s*===\s*["']error["']\s*\|\|\s*toast\s*\.\s*variant\s*===\s*["']warning["']/,
	);
	assert.match(source, /role=\{isUrgent \? ["']alert["'] : ["']status["']\}/);
	assert.match(source, /aria-live=\{isUrgent \? ["']assertive["'] : ["']polite["']\}/);
	assert.match(source, /aria-atomic="true"/);
	assert.match(source, /const toastDismissLabel = `\$\{toast\.title\} 알림 닫기`;/);
	assert.match(source, /aria-label=\{toastDismissLabel\}/);
	assert.match(source, /title=\{toastDismissLabel\}/);
	assert.match(source, /aria-hidden="true"/);
	assert.doesNotMatch(source, /aria-label="Close"/);
});

test("shared Button defaults to safe non-submit semantics", () => {
	const source = readSource("components/ui/button.js");

	assert.match(
		source,
		/type=\{asChild \? undefined : \(type \?\? "button"\)\}/,
	);
	assert.match(
		source,
		/\(\{ className, variant, size, asChild = false, type, \.\.\.props \}/,
	);
});

test("feedback confirmation dialog actions expose stable Korean labels", () => {
	const source = readSource("components/feedback/FeedbackProvider.js");

	assert.match(
		source,
		/const cancelButtonLabel\s*=\s*`\$\{confirmation\.cancelLabel\}하고 확인 창 닫기`/,
	);
	assert.match(
		source,
		/const confirmButtonLabel\s*=\s*`\$\{confirmation\.confirmLabel\} 실행`/,
	);
	assert.match(
		source,
		/<Button[\s\S]*?variant="outline"[\s\S]*?aria-label=\{cancelButtonLabel\}[\s\S]*?title=\{cancelButtonLabel\}[\s\S]*?>/,
	);
	assert.match(
		source,
		/<Button[\s\S]*?onClick=\{\(\) => closeConfirmation\(true\)\}[\s\S]*?aria-label=\{confirmButtonLabel\}[\s\S]*?title=\{confirmButtonLabel\}[\s\S]*?>/,
	);
});
