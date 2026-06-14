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
		/import \{ focusElementSafely \} from ["']@\/lib\/safeFocus["'];/,
	);
	assert.match(
		scheduleSource,
		/function normalizeScheduleTabOptions\(options\) \{/,
	);
	assert.match(
		scheduleSource,
		/return options && typeof options === ["']object["'] && !Array\.isArray\(options\)/,
	);
	assert.match(
		scheduleSource,
		/export default function ScheduleTab\(options = \{\}\) \{/,
	);
	assert.match(scheduleSource, /normalizeScheduleTabOptions\(options\);/);
	assert.match(
		scheduleSource,
		/const handleCreateEvent =\s+typeof onCreateEvent === ["']function["'] \? onCreateEvent : async \(\) => false;/,
	);
	assert.match(
		scheduleSource,
		/const \[isSaving, setIsSaving\] = useState\(false\)/,
	);
	assert.match(scheduleSource, /const isMountedRef = useRef\(false\)/);
	assert.match(scheduleSource, /const scheduleFormRef = useRef\(null\);/);
	assert.match(scheduleSource, /const scheduleTitleInputRef = useRef\(null\);/);
	assert.match(scheduleSource, /const saveInFlightRef = useRef\(false\)/);
	assert.match(scheduleSource, /const scheduleTitleRegistration = register\("title"\);/);
	assert.match(
		scheduleSource,
		/useEffect\(\(\) => \{\s+isMountedRef\.current = true;[\s\S]*?return \(\) => \{\s+isMountedRef\.current = false;\s+saveInFlightRef\.current = false;\s+completionInFlightRef\.current = false;/,
	);
	assert.match(
		scheduleSource,
		/useEffect\(\(\) => \{\s+if \(quickActionIntent\?\.actionId === ["']add-schedule["']\) \{\s+setIsAdding\(true\);\s+\}\s+\}, \[quickActionIntent\?\.actionId, quickActionIntent\?\.nonce\]\);/,
	);
	assert.match(
		scheduleSource,
		/useEffect\(\(\) => \{\s+if \(!isAdding\) \{\s+return;\s+\}[\s\S]*?const timeoutId = window\.setTimeout\(\(\) => \{[\s\S]*?scheduleFormRef\.current\?\.scrollIntoView\(\{\s+behavior: "smooth",\s+block: "start",\s+inline: "nearest",\s+\}\);[\s\S]*?scheduleFormRef\.current\?\.scrollIntoView\(\);[\s\S]*?focusElementSafely\(scheduleTitleInputRef\.current\);[\s\S]*?\}, 0\);[\s\S]*?window\.clearTimeout\(timeoutId\);[\s\S]*?\}, \[isAdding, quickActionIntent\?\.nonce\]\);/,
	);
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
	assert.match(scheduleSource, /await handleCreateEvent\(values\)/);
	assert.doesNotMatch(scheduleSource, /await onCreateEvent\(values\)/);
	assert.match(
		scheduleSource,
		/if \(!saved \|\| !isMountedRef\.current\) \{\s+return;\s+\}/,
	);
	assert.match(
		scheduleSource,
		/finally \{\s+saveInFlightRef\.current = false;\s+if \(isMountedRef\.current\) \{\s+setIsSaving\(false\);/,
	);
	assert.doesNotMatch(
		scheduleSource,
		/finally \{\s+saveInFlightRef\.current = false;\s+setIsSaving\(false\);/,
	);
	assert.match(
		scheduleSource,
		/const addFormButtonLabel = isSaving/,
	);
	assert.match(scheduleSource, /일정 저장 중에는 등록 창을 닫을 수 없습니다/);
	assert.match(scheduleSource, /일정 등록 취소/);
	assert.match(scheduleSource, /일정 등록 창 열기/);
	assert.match(scheduleSource, /const addFormButtonText = isSaving/);
	assert.match(scheduleSource, /일정 저장 중\.\.\./);
	assert.match(scheduleSource, /일정 등록 취소/);
	assert.match(scheduleSource, /: "일정 등록";/);
	assert.doesNotMatch(
		scheduleSource,
		/const addFormButtonText = isSaving[\s\S]*?\? "일정 저장 중\.\.\."[\s\S]*?: isAdding[\s\S]*?\? "취소"[\s\S]*?: "새 일정";/,
	);
	assert.doesNotMatch(
		scheduleSource,
		/const addFormButtonText = isSaving[\s\S]*?: isAdding[\s\S]*?\? "취소"/,
	);
	assert.doesNotMatch(scheduleSource, /"새 일정"/);
	assert.match(
		scheduleSource,
		/onClick=\{toggleAddForm\}\s+disabled=\{isSaving\}\s+aria-busy=\{isSaving\}\s+aria-expanded=\{isAdding\}\s+aria-label=\{addFormButtonLabel\}\s+title=\{addFormButtonLabel\}/,
	);
	assert.match(
		scheduleSource,
		/className="clay-pressable inline-flex min-h-11 items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold text-\[color:var\(--color-text\)\]"/,
	);
	assert.match(scheduleSource, /\{addFormButtonText\}/);
	assert.match(
		scheduleSource,
		/<form\s+ref=\{scheduleFormRef\}[\s\S]*?onSubmit=\{handleScheduleSubmit\}/,
	);
	assert.match(
		scheduleSource,
		/id="schedule-title"[\s\S]*?\{\.\.\.scheduleTitleRegistration\}[\s\S]*?ref=\{\(element\) => \{\s+scheduleTitleRegistration\.ref\(element\);\s+scheduleTitleInputRef\.current = element;\s+\}\}/,
	);
	assert.doesNotMatch(
		scheduleSource,
		/id="schedule-title"[\s\S]{0,240}\{\.\.\.register\("title"\)\}/,
	);
	assert.match(
		scheduleSource,
		/const submitButtonLabel = isSaving \? ['"]일정 등록 중['"] : ['"]일정 등록['"];/,
	);
	assert.match(
		scheduleSource,
		/const submitButtonText = isSaving \? ['"]일정 등록 중\.\.\.['"] : ['"]일정 등록['"];/,
	);
	assert.match(
		scheduleSource,
		/type=["']submit["']\s*disabled=\{isSaving\}\s*aria-busy=\{isSaving\}/,
	);
	assert.match(
		scheduleSource,
		/aria-label=\{submitButtonLabel\}\s+title=\{submitButtonLabel\}/,
	);
	assert.match(scheduleSource, /\{submitButtonText\}/);
	assert.doesNotMatch(
		scheduleSource,
		/\{isSaving \? ["']일정 등록 중\.\.\.["'] : ["']일정 등록하기["']\}/,
	);
	assert.doesNotMatch(scheduleSource, /일정 등록하기/);
});

test("schedule completion toggles wait for async updates before re-enabling controls", () => {
	const scheduleSource = readSource("components/tabs/ScheduleTab.js");

	assert.match(
		scheduleSource,
		/const handleToggleEvent =\s+typeof onToggleEvent === ["']function["'] \? onToggleEvent : async \(\) => false;/,
	);
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
		/await handleToggleEvent\(event\.id, !event\.isCompleted\);/,
	);
	assert.doesNotMatch(
		scheduleSource,
		/await onToggleEvent\(event\.id, !event\.isCompleted\);/,
	);
	assert.match(
		scheduleSource,
		/finally \{\s+completionInFlightRef\.current = false;\s+if \(isMountedRef\.current\) \{\s+setSavingEventId\(null\);/,
	);
	assert.doesNotMatch(
		scheduleSource,
		/finally \{\s+completionInFlightRef\.current = false;\s+setSavingEventId\(null\);/,
	);
	assert.match(
		scheduleSource,
		/const isSavingEvent = savingEventId === event\.id;/,
	);
	assert.match(
		scheduleSource,
		/const eventCompletionLabel = isSavingEvent\s*\?\s*`\$\{event\.title\} 일정 완료 상태 변경 중`\s*:\s*`\$\{event\.title\} 일정 완료 상태 변경`;/,
	);
	assert.match(
		scheduleSource,
		/const eventCompletionText = isSavingEvent[\s\S]*?\? "일정 완료 상태 변경 중\.\.\."[\s\S]*?: event\.isCompleted[\s\S]*?\? "완료됨"[\s\S]*?: "미완료";/,
	);
	assert.match(
		scheduleSource,
		/onChange=\{\(\) => toggleEventCompletion\(event\)\}/,
	);
	assert.match(scheduleSource, /disabled=\{isSavingEvent\}/);
	assert.match(scheduleSource, /aria-busy=\{isSavingEvent\}/);
	assert.match(scheduleSource, /aria-label=\{eventCompletionLabel\}/);
	assert.match(scheduleSource, /title=\{eventCompletionLabel\}/);
	assert.match(scheduleSource, /\{eventCompletionText\}/);
});

test("schedule upcoming dates use operator-readable countdown labels", () => {
	const scheduleSource = readSource("components/tabs/ScheduleTab.js");

	assert.match(scheduleSource, /function formatDaysLeftLabel\(daysLeft\) \{/);
	assert.match(scheduleSource, /return daysLeft === 0 \? "오늘" : `\$\{daysLeft\}일 남음`;/);
	assert.match(scheduleSource, /\(\{formatDaysLeftLabel\(daysLeft\)\}\)/);
	assert.doesNotMatch(scheduleSource, /`\(D-\$\{daysLeft\}\)`/);
	assert.doesNotMatch(scheduleSource, /\(D-\{daysLeft\}\)/);
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
		/\.filter\(\(event\) => event && typeof event === ['"]object['"] && !Array\.isArray\(event\)\)/,
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

test("InventoryTab and ScheduleTab add-form toggle buttons declare aria-expanded for screen readers", () => {
	const inventorySource = readSource("components/tabs/InventoryTab.js");
	const scheduleSource = readSource("components/tabs/ScheduleTab.js");

	// Both tabs have a toggle button that discloses an inline add form (WCAG 4.1.2 State)
	assert.match(inventorySource, /aria-expanded=\{isAdding\}/);
	assert.match(scheduleSource, /aria-expanded=\{isAdding\}/);
});

test("ScheduleTab calendar weekday headers use abbr elements with full Korean day names", () => {
	const scheduleSource = readSource("components/tabs/ScheduleTab.js");

	// abbr with title gives screen readers full weekday names while showing short labels visually
	assert.match(scheduleSource, /<abbr title=\{full\}/);
	assert.match(scheduleSource, /일요일/); // 일요일
	assert.match(scheduleSource, /토요일/); // 토요일
	assert.match(scheduleSource, /aria-label=\{full\}/);
});

test("ScheduleTab inline form marks required fields with aria-required", () => {
	const source = readSource("components/tabs/ScheduleTab.js");
	// WCAG 4.1.2: required fields must expose required state programmatically
	// title and date are required; type has a default so not strictly required
	const requiredCount = (source.match(/aria-required="true"/g) || []).length;
	assert.ok(requiredCount >= 2, `Expected ≥2 aria-required on schedule form, found ${requiredCount}`);
	for (const fieldId of ["schedule-title", "schedule-date"]) {
		const idIdx = source.indexOf(`id="${fieldId}"`);
		const reqIdx = source.indexOf('aria-required="true"', idIdx);
		const invIdx = source.indexOf("aria-invalid=", idIdx);
		assert.ok(reqIdx !== -1 && reqIdx < invIdx, `aria-required missing or misplaced for ${fieldId}`);
	}
});
