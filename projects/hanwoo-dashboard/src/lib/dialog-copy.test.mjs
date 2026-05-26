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

test("shared dialog close control uses contextual Korean labels", () => {
	const source = readSource("components/ui/dialog.js");

	assert.match(source, /closeLabel = "대화상자 닫기"/);
	assert.match(source, /aria-label=\{closeLabel\}/);
	assert.match(source, /title=\{closeLabel\}/);
	assert.match(source, /<span className="sr-only">\{closeLabel\}<\/span>/);
	assert.match(source, /<X className="h-4 w-4" aria-hidden="true" \/>/);
	assert.doesNotMatch(source, /<span className="sr-only">Close<\/span>/);
	assert.doesNotMatch(source, /<span className="sr-only">닫기<\/span>/);
});

test("feedback confirmation dialog provides a specific close label", () => {
	const source = readSource("components/feedback/FeedbackProvider.js");

	assert.match(
		source,
		/<DialogContent className="sm:max-w-md" closeLabel="확인 창 닫기">/,
	);
});

test("shared select icons stay decorative", () => {
	const source = readSource("components/ui/select.js");

	assert.match(
		source,
		/<ChevronDown className="h-4 w-4 opacity-50" aria-hidden="true" \/>/,
	);
	assert.match(source, /<ChevronUp className="h-4 w-4" aria-hidden="true" \/>/);
	assert.match(
		source,
		/<ChevronDown className="h-4 w-4" aria-hidden="true" \/>/,
	);
	assert.match(source, /<Check className="h-4 w-4" aria-hidden="true" \/>/);
});
