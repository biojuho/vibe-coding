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
		/<button\s+type="button"[\s\S]*?onClick=\{\(\)\s*=>\s*handleSelect\(\s*buildingId\s*,\s*penNumber\s*\)\}/,
	);
	assert.match(
		source,
		/<button\s+type="button"[\s\S]*?onClick=\{\(\)\s*=>\s*handleClick\(\s*safeCow\s*\)\}/,
	);
	assert.match(
		source,
		/const penAccessibleLabel = `\$\{penNumber\}번 칸 상세 보기, \$\{visibleCattle\.length\}두 배치됨\$\{penAlertLabel\}`;/,
	);
	assert.match(source, /aria-label=\{penAccessibleLabel\}/);
	assert.match(source, /title=\{penAccessibleLabel\}/);
	assert.match(source, /const penCowPreviewLabel = al/);
	assert.match(source, /`\$\{c\.name\} 발정 알림 있음`/);
	assert.match(source, /`\$\{c\.name\} 칸 배치됨`/);
	assert.match(source, /title=\{penCowPreviewLabel\}/);
	assert.doesNotMatch(source, /title=\{`\$\{c\.name\}`\}/);
	assert.match(source, /aria-label=\{cattleAccessibleLabel\}/);
	assert.match(source, /title=\{cattleAccessibleLabel\}/);
	assert.match(source, /<div className="pen-alert-badge" aria-hidden="true">/);
	assert.match(source, /<div className="cattle-chevron" aria-hidden="true">/);
});

test("pen cards normalize cattle payloads before rendering", () => {
	const source = readSource("components/ui/cards.js");

	assert.match(source, /function normalizePenCattle\(cattle\) \{/);
	assert.match(source, /return Array\.isArray\(cattle\)/);
	assert.match(
		source,
		/\.filter\(\(cow\) => cow && typeof cow === ["']object["'] && !Array\.isArray\(cow\)\)/,
	);
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

test("pen card drop payloads are normalized before moving cattle", () => {
	const source = readSource("components/ui/cards.js");

	assert.match(source, /function normalizeDroppedCattleData\(value\) \{/);
	assert.match(
		source,
		/!value \|\| typeof value !== "object" \|\| Array\.isArray\(value\)/,
	);
	assert.match(source, /const cattleId = value\.cattleId;/);
	assert.match(
		source,
		/typeof cattleId === "string" && cattleId\.trim\(\)/,
	);
	assert.match(
		source,
		/typeof cattleId === "number" && Number\.isFinite\(cattleId\)/,
	);
	assert.match(
		source,
		/const data = normalizeDroppedCattleData\(\s*JSON\.parse\(e\.dataTransfer\.getData\("text\/plain"\)\),\s*\);/,
	);
	assert.match(
		source,
		/if \(data\) \{\s*handleMoveCattle\(data\.cattleId, buildingId, penNumber\);/,
	);
	assert.doesNotMatch(
		source,
		/handleMoveCattle\(data\.cattleId, buildingId, penNumber\);\s*\} catch/,
	);
});

test("cattle rows normalize malformed cow payloads before rendering", () => {
	const source = readSource("components/ui/cards.js");

	assert.match(source, /function normalizeCattleRowCow\(cow\) \{/);
	assert.match(
		source,
		/const safeCow = cow && typeof cow === "object" && !Array\.isArray\(cow\) \? cow : \{\};/,
	);
	assert.match(source, /id: safeCow\.id \?\? "cattle-row-unknown"/);
	assert.match(
		source,
		/typeof safeCow\.name === "string" && safeCow\.name\.trim\(\)/,
	);
	assert.match(
		source,
		/typeof safeCow\.status === "string" && safeCow\.status\.trim\(\)/,
	);
	assert.match(
		source,
		/typeof safeCow\.tagNumber === "string" && safeCow\.tagNumber\.trim\(\)/,
	);
	assert.match(
		source,
		/safeCow\.weight !== null && safeCow\.weight !== undefined && safeCow\.weight !== ""/,
	);
	assert.match(
		source,
		/safeCow\.geneticInfo &&\s+typeof safeCow\.geneticInfo === "object" &&\s+!Array\.isArray\(safeCow\.geneticInfo\)/,
	);
	assert.match(source, /const safeCow = normalizeCattleRowCow\(cow\);/);
	assert.match(source, /STATUS_COLORS\[safeCow\.status\]/);
	assert.match(source, /handleClick\(\s*safeCow\s*\)/);
	assert.match(
		source,
		/JSON\.stringify\(\{ cattleId: safeCow\.id, name: safeCow\.name \}\)/,
	);
	assert.match(source, /\{safeCow\.name\}/);
	assert.match(source, /\{safeCow\.status\}/);
	assert.match(source, /\{safeCow\.tagNumber\}[\s\S]*\{weightLabel\}/);
	assert.doesNotMatch(source, /STATUS_COLORS\[cow\.status\]/);
	assert.doesNotMatch(source, /onClick\(\s*cow\s*\)/);
	assert.doesNotMatch(source, /\{cow\.name\}/);
	assert.doesNotMatch(source, /\{cow\.status\}/);
	assert.doesNotMatch(source, /\{cow\.tagNumber\}/);
});

test("shared cards normalize malformed top-level props and callbacks", () => {
	const source = readSource("components/ui/cards.js");

	assert.match(source, /function normalizeCardComponentOptions\(options\) \{/);
	assert.match(
		source,
		/return options && typeof options === "object" && !Array\.isArray\(options\)\s+\? options\s+:\s+\{\};/,
	);
	assert.match(source, /export function StatCard\(options = \{\}\) \{/);
	assert.match(
		source,
		/const \{ label, value, sub, color, delay = 0 \} =\s+normalizeCardComponentOptions\(options\);/,
	);
	assert.match(source, /export function PenCard\(options = \{\}\) \{/);
	assert.match(
		source,
		/\} = normalizeCardComponentOptions\(options\);[\s\S]*?const visibleCattle = normalizePenCattle\(cattle\);/,
	);
	assert.match(
		source,
		/const handleSelect =\s+typeof onSelect === "function" \? onSelect : \(\) => undefined;/,
	);
	assert.match(
		source,
		/const handleMoveCattle =\s+typeof onDrop === "function" \? onDrop : \(\) => undefined;/,
	);
	assert.match(source, /if \(typeof onDrop === "function"\) \{/);
	assert.match(source, /export function CattleRow\(options = \{\}\) \{/);
	assert.match(
		source,
		/const \{ cow, onClick, delay = 0, draggable = false \} =\s+normalizeCardComponentOptions\(options\);/,
	);
	assert.match(
		source,
		/const handleClick =\s+typeof onClick === "function" \? onClick : \(\) => undefined;/,
	);
});

test("cattle row alert badges use operator-readable countdown labels", () => {
	const source = readSource("components/ui/cards.js");

	assert.match(source, /"발정 오늘"/);
	assert.match(source, /`발정 \$\{estrusD\}일 남음`/);
	assert.match(source, /분만 \{calvingDays\}일 남음/);
	assert.doesNotMatch(source, /발정D-/);
	assert.doesNotMatch(source, /분만D-/);
});

test("cattle rows explain missing genetic grades instead of showing dash placeholders", () => {
	const source = readSource("components/ui/cards.js");

	assert.match(
		source,
		/const geneticGradeLabel =\s+typeof safeCow\.geneticInfo\?\.grade === ["']string["'] &&\s+safeCow\.geneticInfo\.grade\.trim\(\) &&\s+safeCow\.geneticInfo\.grade !== ["']-["']\s+\?\s+safeCow\.geneticInfo\.grade\s+:/,
	);
	assert.match(source, /\{geneticGradeLabel\}/);
	assert.doesNotMatch(source, /cow\.geneticInfo\?\.grade \|\| ["']-["']/);
	assert.doesNotMatch(source, /typeof cow\.geneticInfo\?\.grade/);
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
