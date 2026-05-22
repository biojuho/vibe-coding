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

test("pen and cattle cards use native button activation semantics", () => {
	const source = readSource("components/ui/cards.js");

	assert.doesNotMatch(source, /function runOnKeyboardActivation/);
	assert.doesNotMatch(source, /role="button"/);
	assert.doesNotMatch(source, /tabIndex=\{0\}/);

	assert.match(
		source,
		/<button\s+type="button"[\s\S]*?onClick=\{\(\)=>onSelect\(buildingId,penNumber\)\}/,
	);
	assert.match(
		source,
		/<button\s+type="button"[\s\S]*?onClick=\{\(\)=>onClick\(cow\)\}/,
	);
	assert.match(source, /aria-label=\{`\$\{penNumber\}/);
	assert.match(source, /aria-label=\{cattleAccessibleLabel\}/);
	assert.match(source, /<div className="pen-alert-badge" aria-hidden="true">/);
	assert.match(source, /<div className="cattle-chevron" aria-hidden="true">/);
});

test("pen cards normalize cattle payloads before rendering", () => {
	const source = readSource("components/ui/cards.js");

	assert.match(source, /function normalizePenCattle\(cattle\) \{/);
	assert.match(source, /return Array\.isArray\(cattle\)/);
	assert.match(source, /\.filter\(\(cow\) => cow && typeof cow === 'object'\)/);
	assert.match(source, /id: cow\.id \?\? `pen-cattle-\$\{index\}`/);
	assert.match(
		source,
		/name: typeof cow\.name === 'string' && cow\.name\.trim\(\) \? cow\.name : '개체명 미등록'/,
	);
	assert.match(source, /const visibleCattle = normalizePenCattle\(cattle\);/);
	assert.match(
		source,
		/visibleCattle\.some\(c=>c\.lastEstrus&&isEstrusAlert\(c\.lastEstrus\)\)/,
	);
	assert.match(source, /const isEmpty=visibleCattle\.length===0;/);
	assert.match(source, /visibleCattle\.length\}두 배치됨/);
	assert.match(source, /visibleCattle\.length\}\/5/);
	assert.match(source, /visibleCattle\.map\(\(c,idx\)=>/);
	assert.doesNotMatch(source, /cattle\.some/);
	assert.doesNotMatch(source, /cattle\.length/);
	assert.doesNotMatch(source, /cattle\.map/);
});

test("native card buttons keep card visual reset styles", () => {
	const source = readSource("app/globals.css");

	assert.match(
		source,
		/\.pen-card \{[\s\S]*?width: 100%;[\s\S]*?font: inherit;[\s\S]*?text-align: left;/,
	);
	assert.match(
		source,
		/\.cattle-row \{[\s\S]*?width: 100%;[\s\S]*?font: inherit;[\s\S]*?text-align: left;/,
	);
});
