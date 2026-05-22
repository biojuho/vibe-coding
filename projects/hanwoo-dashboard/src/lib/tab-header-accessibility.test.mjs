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

test("primary tab header icons are decorative for assistive tech", () => {
	const inventorySource = readSource("components/tabs/InventoryTab.js");
	const salesSource = readSource("components/tabs/SalesTab.js");
	const scheduleSource = readSource("components/tabs/ScheduleTab.js");
	const feedSource = readSource("components/tabs/FeedTab.js");

	assert.match(
		inventorySource,
		/<span aria-hidden="true" style=\{\{\s*fontSize:\s*["']20px["'],\s*lineHeight:\s*1\s*\}\}>\s*📦\s*<\/span>/,
	);
	assert.match(
		salesSource,
		/<span aria-hidden="true" style=\{\{\s*fontSize:\s*["']20px["'],\s*lineHeight:\s*1\s*\}\}>\s*💰\s*<\/span>/,
	);
	assert.match(
		scheduleSource,
		/<span aria-hidden="true" style=\{\{\s*fontSize:\s*["']20px["'],\s*lineHeight:\s*1\s*\}\}>\s*🗓️\s*<\/span>/,
	);
	assert.match(
		feedSource,
		/<span className=["']section-header-icon["']\s+aria-hidden=["']true["']>\s*🌾\s*<\/span>/,
	);
});

test("schedule form fields expose labels and validation state", () => {
	const scheduleSource = readSource("components/tabs/ScheduleTab.js");

	assert.match(
		scheduleSource,
		/<label\s+htmlFor=["']schedule-title["'][\s\S]*?>\s*일정 제목\s*<\/label>/,
	);
	assert.match(
		scheduleSource,
		/id=["']schedule-title["'][\s\S]*?aria-invalid=\{Boolean\(errors\.title\)\}/,
	);
	assert.match(
		scheduleSource,
		/<label\s+htmlFor=["']schedule-date["'][\s\S]*?>\s*일정 날짜\s*<\/label>/,
	);
	assert.match(
		scheduleSource,
		/id=["']schedule-date["'][\s\S]*?aria-invalid=\{Boolean\(errors\.date\)\}/,
	);
	assert.match(
		scheduleSource,
		/<label\s+htmlFor=["']schedule-type["'][\s\S]*?>\s*일정 종류\s*<\/label>/,
	);
	assert.match(
		scheduleSource,
		/id=["']schedule-type["'][\s\S]*?aria-invalid=\{Boolean\(errors\.type\)\}/,
	);
});

test("schedule form validation messages are announced with their controls", () => {
	const scheduleSource = readSource("components/tabs/ScheduleTab.js");
	const fields = [
		["title", "schedule-title-error"],
		["date", "schedule-date-error"],
		["type", "schedule-type-error"],
	];

	for (const [errorPath, errorId] of fields) {
		assert.match(
			scheduleSource,
			new RegExp(
				`aria-describedby=\\{\\s*errors\\.${errorPath}\\s*\\?\\s*["']${errorId}["']\\s*:\\s*undefined\\s*\\}`,
			),
		);
		assert.match(
			scheduleSource,
			new RegExp(`<div\\s+id="${errorId}"\\s+role="alert"`),
		);
	}
});

test("schedule form waits for async saves before re-enabling actions", () => {
	const scheduleSource = readSource("components/tabs/ScheduleTab.js");

	assert.match(
		scheduleSource,
		/const \[isSaving, setIsSaving\] = useState\(false\)/,
	);
	assert.match(scheduleSource, /const saveInFlightRef = useRef\(false\)/);
	assert.match(
		scheduleSource,
		/if \(saveInFlightRef\.current \|\| isSaving\) \{\s+return;\s+\}/,
	);
	assert.match(
		scheduleSource,
		/if \(saveInFlightRef\.current\) \{\s+return;\s+\}/,
	);
	assert.match(scheduleSource, /saveInFlightRef\.current = true;/);
	assert.match(scheduleSource, /setIsSaving\(true\);/);
	assert.match(scheduleSource, /await onCreateEvent\(values\)/);
	assert.match(
		scheduleSource,
		/finally \{\s+saveInFlightRef\.current = false;\s+setIsSaving\(false\);/,
	);
	assert.match(
		scheduleSource,
		/onClick=\{toggleAddForm\}\s+disabled=\{isSaving\}/,
	);
	assert.match(
		scheduleSource,
		/const submitButtonLabel = isSaving \? ['"]일정 등록 중['"] : ['"]일정 등록하기['"];/,
	);
	assert.match(
		scheduleSource,
		/type=["']submit["']\s*disabled=\{isSaving\}\s*aria-busy=\{isSaving\}/,
	);
	assert.match(
		scheduleSource,
		/aria-label=\{submitButtonLabel\}\s+title=\{submitButtonLabel\}/,
	);
});

test("schedule completion toggles wait for async updates before re-enabling controls", () => {
	const scheduleSource = readSource("components/tabs/ScheduleTab.js");

	assert.match(
		scheduleSource,
		/const \[savingEventId, setSavingEventId\] = useState\(null\)/,
	);
	assert.match(scheduleSource, /const completionInFlightRef = useRef\(false\)/);
	assert.match(
		scheduleSource,
		/if \(completionInFlightRef\.current \|\| savingEventId\) \{\s+return;\s+\}/,
	);
	assert.match(scheduleSource, /completionInFlightRef\.current = true;/);
	assert.match(scheduleSource, /setSavingEventId\(event\.id\);/);
	assert.match(
		scheduleSource,
		/await onToggleEvent\(event\.id, !event\.isCompleted\);/,
	);
	assert.match(
		scheduleSource,
		/finally \{\s+completionInFlightRef\.current = false;\s+setSavingEventId\(null\);/,
	);
	assert.match(
		scheduleSource,
		/onChange=\{\(\) => toggleEventCompletion\(event\)\}/,
	);
	assert.match(scheduleSource, /disabled=\{savingEventId === event\.id\}/);
	assert.match(scheduleSource, /aria-busy=\{savingEventId === event\.id\}/);
});

test("schedule tab skips invalid event dates before calendar and upcoming rendering", () => {
	const scheduleSource = readSource("components/tabs/ScheduleTab.js");

	assert.match(scheduleSource, /function toValidDate\(value\) \{/);
	assert.match(
		scheduleSource,
		/const date =\s*value instanceof Date \? new Date\(value\.getTime\(\)\) : new Date\(value\);/,
	);
	assert.match(
		scheduleSource,
		/const dateKey = value\.trim\(\)\.slice\(0, 10\);/,
	);
	assert.match(
		scheduleSource,
		/date\.toISOString\(\)\.slice\(0, 10\) !== dateKey/,
	);
	assert.match(scheduleSource, /return date;/);
	assert.match(scheduleSource, /function toDateKey\(value\) \{/);
	assert.match(scheduleSource, /const date = toValidDate\(event\.date\);/);
	assert.match(
		scheduleSource,
		/return\s*\(?\s*date\s*&&\s*date\.getMonth\(\) === currentDate\.getMonth\(\)/,
	);
	assert.match(
		scheduleSource,
		/return\s*date\s*&&\s*date\s*>=\s*now\s*&&\s*!event\.isCompleted;/,
	);
	assert.match(
		scheduleSource,
		/sort\(\s*\(\s*first,\s*second\s*\)\s*=>\s*toValidDate\(first\.date\)\s*-\s*toValidDate\(second\.date\),\s*\)/,
	);
	assert.match(
		scheduleSource,
		/\(event\) => toDateKey\(event\.date\) === dateStr/,
	);
	assert.doesNotMatch(
		scheduleSource,
		/return Number\.isNaN\(date\.getTime\(\)\) \? null : date;/,
	);
	assert.doesNotMatch(
		scheduleSource,
		/new Date\(event\.date\)\.toISOString\(\)\.split\(['"]T['"]\)\[0\] === dateStr/,
	);
});

test("schedule tab normalizes malformed event payloads before rendering", () => {
	const scheduleSource = readSource("components/tabs/ScheduleTab.js");

	assert.match(scheduleSource, /function normalizeScheduleEvents\(events\) \{/);
	assert.match(scheduleSource, /if \(!Array\.isArray\(events\)\) return \[\];/);
	assert.match(
		scheduleSource,
		/\.filter\(\(event\) => event && typeof event === ['"]object['"]\)/,
	);
	assert.match(
		scheduleSource,
		/const safeEvents = useMemo\(\(\) => normalizeScheduleEvents\(events\), \[events\]\);/,
	);
	assert.match(scheduleSource, /safeEvents\.filter\(\(event\) => \{/);
	assert.match(scheduleSource, /id: event\.id \?\? `schedule-\$\{index\}`/);
	assert.match(scheduleSource, /['"]일정명 미등록['"]/);
	assert.match(
		scheduleSource,
		/type:\s*typeof event\.type === ['"]string['"] && TYPE_STYLES\[event\.type\]\s*\? event\.type\s*: ['"]General['"]/,
	);
	assert.doesNotMatch(scheduleSource, /events\.filter\(\(event\) => \{/);
	assert.match(scheduleSource, /return safeEvents\s+\.filter/);
});
