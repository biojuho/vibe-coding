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
		/<button\s+type="button"[\s\S]*?onClick=\{\(\)\s*=>\s*onSelect\(\s*buildingId\s*,\s*penNumber\s*\)\}/,
	);
	assert.match(
		source,
		/<button\s+type="button"[\s\S]*?onClick=\{\(\)\s*=>\s*onClick\(\s*cow\s*\)\}/,
	);
	assert.match(
		source,
		/const penAccessibleLabel = `\$\{penNumber\}번 칸 상세 보기, \$\{visibleCattle\.length\}두 배치됨\$\{penAlertLabel\}`;/,
	);
	assert.match(source, /aria-label=\{penAccessibleLabel\}/);
	assert.match(source, /title=\{penAccessibleLabel\}/);
	assert.match(source, /aria-label=\{cattleAccessibleLabel\}/);
	assert.match(source, /title=\{cattleAccessibleLabel\}/);
	assert.match(source, /<div className="pen-alert-badge" aria-hidden="true">/);
	assert.match(source, /<div className="cattle-chevron" aria-hidden="true">/);
});

test("pen cards normalize cattle payloads before rendering", () => {
	const source = readSource("components/ui/cards.js");

	assert.match(source, /function normalizePenCattle\(cattle\) \{/);
	assert.match(source, /return Array\.isArray\(cattle\)/);
	assert.match(source, /\.filter\(\(cow\) => cow && typeof cow === ["']object["']\)/);
	assert.match(source, /id: cow\.id \?\? `pen-cattle-\$\{index\}`/);
	assert.match(
		source,
		/name:\s*typeof cow\.name\s*===\s*["']string["']\s*&&\s*cow\.name\.trim\(\)\s*\?\s*cow\.name\s*:\s*["']개체명 미등록["']/,
	);
	assert.match(source, /const visibleCattle = normalizePenCattle\(cattle\);/);
	assert.match(
		source,
		/visibleCattle\s*\.\s*some\(\s*\(\s*c\s*\)\s*=>\s*c\s*\.\s*lastEstrus\s*&&\s*isEstrusAlert\(\s*c\s*\.\s*lastEstrus\s*\)\s*,?\s*\)/,
	);
	assert.match(source, /const\s+isEmpty\s*=\s*visibleCattle\s*\.\s*length\s*===\s*0\s*;?/);
	assert.match(source, /visibleCattle\.length\}두 배치됨/);
	assert.match(source, /visibleCattle\.length\}\/5/);
	assert.match(source, /visibleCattle\s*\.\s*map\(\s*\(\s*c\s*,\s*idx\s*\)\s*=>/);
	assert.doesNotMatch(source, /cattle\.some/);
	assert.doesNotMatch(source, /cattle\.length/);
	assert.doesNotMatch(source, /cattle\.map/);
});

test("cattle row alert badges use operator-readable countdown labels", () => {
	const source = readSource("components/ui/cards.js");

	assert.match(source, /"발정 오늘"/);
	assert.match(source, /`발정 \$\{estrusD\}일 남음`/);
	assert.match(source, /분만 \{calvingDays\}일 남음/);
	assert.doesNotMatch(source, /발정D-/);
	assert.doesNotMatch(source, /분만D-/);
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
