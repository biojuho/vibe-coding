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

test("cattle detail breeding actions use an in-app date form instead of browser prompts", () => {
	const source = readSource("components/forms/CattleDetailModal.js");

	assert.doesNotMatch(source, /\bprompt\s*\(/);
	assert.match(source, /activeBreedingAction/);
	assert.match(source, /type="date"/);
	assert.match(source, /handleSaveBreedingRecord/);
	assert.match(source, /onUpdate\(nextCattle/);
	assert.match(source, /successTitle:\s*activeBreedingAction\s*===\s*["']pregnancy["']/);
});

test("cattle detail breeding date validation is announced with the date input", () => {
	const source = readSource("components/forms/CattleDetailModal.js");

	assert.match(
		source,
		/const breedingDateErrorId = "breeding-record-date-error"/,
	);
	assert.match(source, /function toStrictInputDate\(value\)/);
	assert.match(source, /date\.toISOString\(\)\.slice\(0, 10\) !== value/);
	assert.match(
		source,
		/const selectedDate = toStrictInputDate\(breedingDate\)/,
	);
	assert.doesNotMatch(
		source,
		/const selectedDate = new Date\(`\$\{breedingDate\}T00:00:00`\)/,
	);
	assert.match(source, /aria-invalid=\{Boolean\(breedingError\)\}/);
	assert.match(
		source,
		/aria-describedby=\{\s*breedingError\s*\?\s*breedingDateErrorId\s*:\s*undefined\s*\}/,
	);
	assert.match(source, /<div[\s\S]*?id=\{breedingDateErrorId\}[\s\S]*?role="alert"/);
});

test("cattle detail shows a real calving due date from pregnancy date", () => {
	const source = readSource("components/forms/CattleDetailModal.js");

	assert.match(source, /getCalvingDate/);
	assert.match(
		source,
		/label="분만 예정일"\s+value=\{\s*cattle\.pregnancyDate\s*\?\s*formatDate\(getCalvingDate\(cattle\.pregnancyDate\)\)\s*:\s*["']분만 예정일 미등록["']\s*\}/,
	);
	assert.doesNotMatch(source, /계산중/);
});

test("cattle detail breeding date fallbacks explain which date is missing", () => {
	const source = readSource("components/forms/CattleDetailModal.js");

	assert.match(
		source,
		/label="최근 발정"\s+value=\{\s*cattle\.lastEstrus\s*\?\s*formatDate\(cattle\.lastEstrus\)\s*:\s*["']발정일 미등록["']\s*\}/,
	);
	assert.match(
		source,
		/label="다음 발정 예정"\s+value=\{\s*cattle\.lastEstrus\s*\?\s*formatDaysLeftLabel\(\s*getDaysUntilEstrus\(cattle\.lastEstrus\),\s*\)\s*:\s*["']최근 발정일 미등록["']\s*\}/,
	);
	assert.match(
		source,
		/label="수정일\(임신\)"\s+value=\{\s*cattle\.pregnancyDate\s*\?\s*formatDate\(cattle\.pregnancyDate\)\s*:\s*["']수정일 미등록["']\s*\}/,
	);
	assert.doesNotMatch(
		source,
		/label="(?:최근 발정|다음 발정 예정|수정일\(임신\)|분만 예정일)"[\s\S]*?:\s*["']-["']/,
	);
});

test("cattle detail genetic fallbacks explain which lineage is missing", () => {
	const source = readSource("components/forms/CattleDetailModal.js");

	assert.match(
		source,
		/label="유전능력"\s+value=\{`부:\$\{cattle\.geneticInfo\?\.father \|\| ["']부계 미등록["']\} \/ 모:\$\{cattle\.geneticInfo\?\.mother \|\| ["']모계 미등록["']\}`\}/,
	);
	assert.doesNotMatch(
		source,
		/label="유전능력"[\s\S]*?geneticInfo\?\.father \|\| ["']-["'][\s\S]*?geneticInfo\?\.mother \|\| ["']-["']/,
	);
});

test("cattle detail uses operator-readable breeding countdown labels", () => {
	const source = readSource("components/forms/CattleDetailModal.js");

	assert.match(source, /function formatDaysLeftLabel\(daysLeft\) \{/);
	assert.match(source, /return daysLeft === 0 \? "오늘" : `\$\{daysLeft\}일 남음`;/);
	assert.match(
		source,
		/formatDaysLeftLabel\(\s*getDaysUntilEstrus\(cattle\.lastEstrus\),\s*\)/,
	);
	assert.doesNotMatch(source, /`D-\$\{getDaysUntilEstrus\(cattle\.lastEstrus\)\}`/);
});

test("cattle detail weight chart exposes an accessible chart summary", () => {
	const source = readSource("components/forms/CattleDetailModal.js");

	assert.match(
		source,
		/const weightChartLabel = `\$\{cattle\.name\} 체중 변화 차트\. 날짜별 체중 기록을 선으로 비교합니다\.`;/,
	);
	assert.match(
		source,
		/role="img"\s+aria-label=\{weightChartLabel\}\s+title=\{weightChartLabel\}[\s\S]*?<ResponsiveContainer[\s\S]*?width="100%"[\s\S]*?height="100%"[\s\S]*?minWidth=\{0\}[\s\S]*?minHeight=\{0\}[\s\S]*?initialDimension=\{\{ width: 1, height: 1 \}\}/,
	);
});

test("cattle form and detail icon-only navigation controls have Korean labels", () => {
	const formSource = readSource("components/forms/CattleForm.js");
	const detailSource = readSource("components/forms/CattleDetailModal.js");
	const safeFocusSource = readSource("lib/safeFocus.js");

	assert.match(
		safeFocusSource,
		/export function focusElementSafely\(element\) \{/,
	);
	assert.match(
		safeFocusSource,
		/if \(!element \|\| typeof element\.focus !== ["']function["']\) \{\s+return;\s+\}/,
	);
	assert.match(safeFocusSource, /try \{\s+element\.focus\(\);\s+\} catch \{\}/);
	assert.match(
		formSource,
		/import \{ focusElementSafely \} from ["']@\/lib\/safeFocus["'];/,
	);
	assert.match(formSource, /const cancelButtonLabel = isSaving/);
	assert.match(formSource, /개체 저장 중에는 취소할 수 없습니다/);
	assert.match(formSource, /개체 저장 취소/);
	assert.match(
		formSource,
		/onClick=\{onCancel\}\s+disabled=\{isSaving\}\s+aria-busy=\{isSaving\}\s+aria-label=\{cancelButtonLabel\}\s+title=\{cancelButtonLabel\}[\s\S]*?className="btn btn-ghost btn-icon"/,
	);
	assert.match(formSource, /role="dialog"/);
	assert.match(formSource, /aria-modal="true"/);
	assert.match(formSource, /aria-labelledby="cattle-form-title"/);
	assert.match(formSource, /const dialogRef = useRef\(null\)/);
	assert.match(formSource, /focusElementSafely\(dialogRef\.current\);/);
	assert.match(formSource, /tabIndex=\{-1\}/);
	assert.match(formSource, /onKeyDown=\{handleDialogKeyDown\}/);
	assert.match(
		formSource,
		/if \(event\.key === ["']Escape["']\) \{\s+if \(isSaving\) \{\s+return;\s+\}\s+onCancel\(\);/,
	);
	assert.match(formSource, /id="cattle-form-title"/);
	assert.match(formSource, /<label htmlFor="cattle-name"/);
	assert.match(formSource, /id="cattle-name"/);
	assert.match(formSource, /<label htmlFor="cattle-tag-number"/);
	assert.match(formSource, /id="cattle-tag-number"/);
	assert.match(formSource, /<label htmlFor="cattle-building"/);
	assert.match(
		formSource,
		/id="cattle-building"[^>]*aria-invalid=\{Boolean\(errors\.buildingId\)\}/,
	);
	assert.match(formSource, /<label htmlFor="cattle-pen-number"/);
	assert.match(
		formSource,
		/id="cattle-pen-number"[^>]*aria-invalid=\{Boolean\(errors\.penNumber\)\}/,
	);
	assert.match(formSource, /<label htmlFor="cattle-gender"/);
	assert.match(
		formSource,
		/id="cattle-gender"[^>]*aria-invalid=\{Boolean\(errors\.gender\)\}/,
	);
	assert.match(formSource, /<label htmlFor="cattle-status"/);
	assert.match(
		formSource,
		/id="cattle-status"[^>]*aria-invalid=\{Boolean\(errors\.status\)\}/,
	);
	assert.match(formSource, /<label htmlFor="cattle-birth-date"/);
	assert.match(
		formSource,
		/id="cattle-birth-date"[^>]*aria-invalid=\{Boolean\(errors\.birthDate\)\}/,
	);
	assert.match(formSource, /<label htmlFor="cattle-weight"/);
	assert.match(
		formSource,
		/id="cattle-weight"[^>]*aria-invalid=\{Boolean\(errors\.weight\)\}/,
	);
	assert.match(formSource, /<label htmlFor="cattle-purchase-price"/);
	assert.match(
		formSource,
		/id="cattle-purchase-price"[\s\S]*?aria-invalid=\{Boolean\(errors\.purchasePrice\)\}/,
	);
	assert.match(formSource, /<label htmlFor="cattle-purchase-date"/);
	assert.match(
		formSource,
		/id="cattle-purchase-date"[^>]*aria-invalid=\{Boolean\(errors\.purchaseDate\)\}/,
	);
	assert.match(formSource, /<label htmlFor="cattle-genetic-father"/);
	assert.match(
		formSource,
		/id="cattle-genetic-father"[\s\S]*?aria-invalid=\{Boolean\(errors\.geneticInfo\?\.father\)\}/,
	);
	assert.match(formSource, /<label htmlFor="cattle-genetic-mother"/);
	assert.match(
		formSource,
		/id="cattle-genetic-mother"[\s\S]*?aria-invalid=\{Boolean\(errors\.geneticInfo\?\.mother\)\}/,
	);
	assert.match(formSource, /<label htmlFor="cattle-memo"/);
	assert.match(
		formSource,
		/id="cattle-memo"[\s\S]*?aria-invalid=\{Boolean\(errors\.memo\)\}/,
	);
	assert.match(
		detailSource,
		/const closeButtonLabel = isDetailBusy\s*\?\s*[`"']\$\{cattle\.name\} 개체 처리 중에는 상세 창을 닫을 수 없습니다[`"']\s*:\s*["']개체 상세 닫기["'];?/,
	);
	assert.match(detailSource, /aria-label=\{closeButtonLabel\}/);
	assert.match(detailSource, /title=\{closeButtonLabel\}/);
	assert.match(detailSource, /type="button"\s+onClick=\{onClose\}/);
	assert.match(
		detailSource,
		/const editButtonLabel = isDetailBusy\s*\?\s*[`"']\$\{cattle\.name\} 개체 처리 중에는 수정할 수 없습니다[`"']\s*:\s*[`"']\$\{cattle\.name\} 개체 정보 수정[`"'];?/,
	);
	assert.match(
		detailSource,
		/const editButtonText = isDetailBusy\s*\?\s*["']개체 처리 중\.\.\.["']\s*:\s*["']개체 정보 수정["'];?/,
	);
	assert.doesNotMatch(
		detailSource,
		/const editButtonText = isDetailBusy\s*\?\s*["']개체 처리 중\.\.\.["']\s*:\s*["']수정["'];?/,
	);
	assert.match(detailSource, /aria-label=\{editButtonLabel\}/);
	assert.match(detailSource, /title=\{editButtonLabel\}/);
	assert.match(detailSource, /type="button"\s+onClick=\{onEdit\}/);
	assert.match(detailSource, /<EditIcon \/>\s*\{editButtonText\}/);
	assert.match(
		detailSource,
		/const archiveButtonLabel = isDetailBusy\s*\?\s*[`"']\$\{cattle\.name\} 개체 처리 중에는 보관할 수 없습니다[`"']\s*:\s*[`"']\$\{cattle\.name\} 개체 보관 처리[`"'];?/,
	);
	assert.match(
		detailSource,
		/const archiveButtonText = isDetailBusy \? ["']개체 처리 중\.\.\.["'] : ["']개체 보관 처리["'];?/,
	);
	assert.doesNotMatch(
		detailSource,
		/const archiveButtonText = isDetailBusy \? ["']개체 처리 중\.\.\.["'] : ["']보관["'];?/,
	);
	assert.match(detailSource, /aria-label=\{archiveButtonLabel\}/);
	assert.match(detailSource, /title=\{archiveButtonLabel\}/);
	assert.match(detailSource, /<TrashIcon \/> \{archiveButtonText\}/);
	assert.match(
		detailSource,
		/const estrusButtonLabel = isDetailBusy\s*\?\s*[`"']\$\{cattle\.name\} 개체 처리 중에는 발정 기록을 시작할 수 없습니다[`"']\s*:\s*[`"']\$\{cattle\.name\} 발정 기록[`"'];?/,
	);
	assert.match(
		detailSource,
		/const estrusButtonText = isDetailBusy\s*\?\s*["']개체 처리 중\.\.\.["']\s*:\s*["']발정 기록["'];?/,
	);
	assert.match(
		detailSource,
		/const pregnancyButtonLabel = isDetailBusy\s*\?\s*[`"']\$\{cattle\.name\} 개체 처리 중에는 수정 기록을 시작할 수 없습니다[`"']\s*:\s*[`"']\$\{cattle\.name\} 수정 기록[`"'];?/,
	);
	assert.match(
		detailSource,
		/const pregnancyButtonText = isDetailBusy\s*\?\s*["']개체 처리 중\.\.\.["']\s*:\s*["']수정 기록["'];?/,
	);
	assert.match(
		detailSource,
		/onClick=\{\(\) => openBreedingForm\(["']estrus["']\)\}[\s\S]*?aria-label=\{estrusButtonLabel\}[\s\S]*?title=\{estrusButtonLabel\}/,
	);
	assert.match(
		detailSource,
		/<CalendarCheck2 size=\{16\} aria-hidden="true" \/>\s*\{estrusButtonText\}/,
	);
	assert.match(
		detailSource,
		/onClick=\{\(\) => openBreedingForm\(["']pregnancy["']\)\}[\s\S]*?aria-label=\{pregnancyButtonLabel\}[\s\S]*?title=\{pregnancyButtonLabel\}/,
	);
	assert.match(
		detailSource,
		/<CheckCircle2 size=\{16\} aria-hidden="true" \/>\s*\{pregnancyButtonText\}/,
	);
	assert.match(detailSource, /type="button"[\s\S]*?onClick=\{onDelete\}/);
	assert.match(detailSource, /role="dialog"/);
	assert.match(detailSource, /aria-modal="true"/);
	assert.match(detailSource, /aria-labelledby="cattle-detail-title"/);
	assert.match(
		detailSource,
		/import \{ focusElementSafely \} from ["']@\/lib\/safeFocus["'];/,
	);
	assert.match(detailSource, /const dialogRef = useRef\(null\)/);
	assert.match(detailSource, /focusElementSafely\(dialogRef\.current\);/);
	assert.match(detailSource, /tabIndex=\{-1\}/);
	assert.match(detailSource, /onKeyDown=\{handleDialogKeyDown\}/);
	assert.match(
		detailSource,
		/const isDetailBusy = isDeleting \|\| isBreedingSaving/,
	);
	assert.match(
		detailSource,
		/if \(event\.key === ["']Escape["']\) \{\s+if \(isDetailBusy\) \{\s+return;\s+\}\s+onClose\(\);/,
	);
	assert.match(detailSource, /id="cattle-detail-title"/);
	assert.doesNotMatch(formSource, /aria-label="Back"/);
	assert.doesNotMatch(detailSource, /aria-label="Close"/);
	assert.doesNotMatch(formSource, /dialogRef\.current\?\.focus\(\)/);
	assert.doesNotMatch(detailSource, /dialogRef\.current\?\.focus\(\)/);
});

test("cattle detail archive actions wait for async deletes before re-enabling submit actions", () => {
	const dashboardSource = readSource("components/DashboardClient.js");
	const detailSource = readSource("components/forms/CattleDetailModal.js");

	assert.match(
		dashboardSource,
		/const \[deletingCattleId, setDeletingCattleId\] = useState\(null\)/,
	);
	assert.match(
		dashboardSource,
		/if \(deletingCattleId\) \{\s+return false;\s+\}/,
	);
	assert.match(dashboardSource, /setDeletingCattleId\(id\);/);
	assert.match(dashboardSource, /await deleteCattle\(id\);/);
	assert.match(dashboardSource, /const dashboardMountedRef = useRef\(false\);/);
	assert.match(
		dashboardSource,
		/finally \{\s+if \(dashboardMountedRef\.current\) \{\s+setDeletingCattleId\(null\);\s+\}/,
	);
	assert.doesNotMatch(
		dashboardSource,
		/finally \{\s+setDeletingCattleId\(null\);/,
	);
	assert.match(
		dashboardSource,
		/isDeleting=\{deletingCattleId === selectedCow\.id\}/,
	);
	assert.match(detailSource, /isDeleting = false/);
	assert.match(
		detailSource,
		/onClick=\{onClose\}\s+disabled=\{isDetailBusy\}\s+aria-busy=\{isDetailBusy\}\s+aria-label=\{closeButtonLabel\}\s+title=\{closeButtonLabel\}/,
	);
	assert.match(
		detailSource,
		/onClick=\{onEdit\}[\s\S]*?disabled=\{isDetailBusy\}[\s\S]*?aria-busy=\{isDetailBusy\}/,
	);
	assert.match(
		detailSource,
		/onClick=\{onDelete\}[\s\S]*?disabled=\{isDetailBusy\}[\s\S]*?aria-busy=\{isDetailBusy\}/,
	);
	assert.match(detailSource, /<TrashIcon \/> \{archiveButtonText\}/);
	assert.match(
		detailSource,
		/if \(breedingSaveInFlightRef\.current \|\| isDetailBusy\) \{\s+return;\s+\}/,
	);
	assert.match(
		detailSource,
		/const breedingCancelButtonText = isBreedingSaving\s*\?\s*["']번식 기록 저장 중\.\.\.["']\s*:\s*["']번식 기록 취소["'];?/,
	);
	assert.match(detailSource, /\{breedingCancelButtonText\}/);
	assert.doesNotMatch(
		detailSource,
		/const breedingCancelButtonText = isBreedingSaving\s*\?\s*["']번식 기록 저장 중\.\.\.["']\s*:\s*["']취소["'];?/,
	);
	assert.match(
		detailSource,
		/onClick=\{\(\) => openBreedingForm\(["']estrus["']\)\}[\s\S]*?disabled=\{isDetailBusy\}/,
	);
	assert.match(
		detailSource,
		/onClick=\{\(\) => openBreedingForm\(["']pregnancy["']\)\}[\s\S]*?disabled=\{isDetailBusy\}/,
	);
});

test("cattle form validation messages are announced with their controls", () => {
	const formSource = readSource("components/forms/CattleForm.js");

	[
		["name", "errors.name"],
		["building", "errors.buildingId"],
		["pen-number", "errors.penNumber"],
		["gender", "errors.gender"],
		["status", "errors.status"],
		["birth-date", "errors.birthDate"],
		["weight", "errors.weight"],
		["purchase-price", "errors.purchasePrice"],
		["purchase-date", "errors.purchaseDate"],
		["genetic-father", "errors.geneticInfo?.father"],
		["genetic-mother", "errors.geneticInfo?.mother"],
		["memo", "errors.memo"],
	].forEach(([field, errorPath]) => {
		const errorId = `cattle-${field}-error`;
		const escapedErrorPath = errorPath.replace(/[?.]/g, "\\$&");

		assert.match(
			formSource,
			new RegExp(
				`aria-describedby=\\{\\s*${escapedErrorPath}\\s*\\?\\s*"${errorId}"\\s*:\\s*undefined\\s*\\}`,
			),
		);
		assert.match(
			formSource,
			new RegExp(`<div[\\s\\S]*?id="${errorId}"[\\s\\S]*?role="alert"`),
		);
	});
});

test("cattle tag lookup progress and results are announced", () => {
	const formSource = readSource("components/forms/CattleForm.js");

	assert.match(formSource, /const lookupInFlightRef = useRef\(false\)/);
	assert.match(formSource, /const lookupRequestIdRef = useRef\(0\)/);
	assert.match(formSource, /const mountedRef = useRef\(true\)/);
	assert.match(formSource, /const saveInFlightRef = useRef\(false\)/);
	assert.match(formSource, /lookupRequestIdRef\.current \+= 1;/);
	assert.match(
		formSource,
		/return \(\) => \{\s+mountedRef\.current = false;\s+lookupRequestIdRef\.current \+= 1;\s+lookupInFlightRef\.current = false;\s+saveInFlightRef\.current = false;/,
	);
	assert.match(
		formSource,
		/if \(lookupInFlightRef\.current\) \{\s+return;\s+\}/,
	);
	assert.match(formSource, /lookupInFlightRef\.current = true;/);
	assert.match(
		formSource,
		/const requestId = lookupRequestIdRef\.current \+ 1;/,
	);
	assert.match(formSource, /lookupRequestIdRef\.current = requestId;/);
	assert.match(
		formSource,
		/if \(!mountedRef\.current \|\| lookupRequestIdRef\.current !== requestId\) \{\s+return;\s+\}/,
	);
	assert.match(
		formSource,
		/if \(lookupRequestIdRef\.current === requestId\) \{\s+lookupInFlightRef\.current = false;/,
	);
	assert.match(
		formSource,
		/const tagNumberErrorId = ["']cattle-tag-number-error["']/,
	);
	assert.match(
		formSource,
		/const tagLookupMessageId = ["']cattle-tag-lookup-message["']/,
	);
	assert.match(
		formSource,
		/const tagLookupButtonLabel = lookupLoading\s*\?\s*["']이력번호 조회 중["']\s*:\s*["']이력번호 조회["'];?/,
	);
	assert.match(
		formSource,
		/const tagLookupButtonText = lookupLoading\s*\?\s*["']이력번호 조회 중\.\.\.["']\s*:\s*["']이력번호 조회["'];?/,
	);
	assert.match(formSource, /const tagNumberDescriptionIds\s*=\s*\[/);
	assert.match(formSource, /errors\.tagNumber\s*\?\s*tagNumberErrorId\s*:\s*null/);
	assert.match(formSource, /lookupMsg\s*\?\s*tagLookupMessageId\s*:\s*null/);
	assert.match(formSource, /aria-describedby=\{tagNumberDescriptionIds\}/);
	assert.match(formSource, /aria-busy=\{lookupLoading\}/);
	assert.match(formSource, /aria-label=\{tagLookupButtonLabel\}/);
	assert.match(formSource, /title=\{tagLookupButtonLabel\}/);
	assert.match(formSource, /\{tagLookupButtonText\}/);
	assert.doesNotMatch(formSource, /태그 조회/);
	assert.match(formSource, /id=\{tagLookupMessageId\}/);
	assert.match(formSource, /role=\{lookupMsg\.ok \? ["']status["'] : ["']alert["']\}/);
	assert.match(
		formSource,
		/aria-live=\{lookupMsg\.ok \? ["']polite["'] : ["']assertive["']\}/,
	);
});

test("cattle form waits for async saves before re-enabling submit actions", () => {
	const formSource = readSource("components/forms/CattleForm.js");

	assert.match(
		formSource,
		/const \[isSaving, setIsSaving\] = useState\(false\)/,
	);
	assert.match(formSource, /const saveInFlightRef = useRef\(false\)/);
	assert.match(
		formSource,
		/saveInFlightRef\.current = false;\s+deferCattleFormTask\(\(\) => \{[\s\S]*?setIsSaving\(false\);[\s\S]*?return \(\) => \{\s+cancelled = true;\s+\};\s+\}, \[safeBuildings, cattle, reset\]\);/,
	);
	assert.match(formSource, /setIsSaving\(false\);/);
	assert.match(
		formSource,
		/const cancelButtonLabel = isSaving\s*\?\s*["']개체 저장 중에는 취소할 수 없습니다["']\s*:\s*["']개체 저장 취소["'];?/,
	);
	assert.match(
		formSource,
		/const cancelButtonText = isSaving\s*\?\s*["']개체 저장 중\.\.\.["']\s*:\s*["']개체 저장 취소["'];?/,
	);
	assert.match(
		formSource,
		/const submitButtonLabel = isSaving\s*\?\s*["']개체 정보 저장 중["']\s*:\s*["']개체 정보 저장["'];?/,
	);
	assert.match(
		formSource,
		/const submitButtonText = isSaving\s*\?\s*["']개체 정보 저장 중\.\.\.["']\s*:\s*["']개체 정보 저장["'];?/,
	);
	assert.match(formSource, /개체 정보를 수정하고 저장해 주세요/);
	assert.match(formSource, /새 개체의 기본 정보를 입력해 주세요/);
	assert.doesNotMatch(formSource, /개체 정보를 수정하고 저장하세요/);
	assert.doesNotMatch(formSource, /새 개체의 기본 정보를 입력하세요/);
	assert.doesNotMatch(formSource, /\?\s*["']정보를 수정하고 저장하세요["']/);
	assert.match(formSource, /const submitForm = async \(values\) => \{/);
	assert.match(formSource, /if \(saveInFlightRef\.current\) \{\s+return;\s+\}/);
	assert.match(formSource, /saveInFlightRef\.current = true;/);
	assert.match(formSource, /setIsSaving\(true\);/);
	assert.match(formSource, /await onSubmit\(\{/);
	assert.match(
		formSource,
		/finally \{\s*saveInFlightRef\.current = false;\s+if \(mountedRef\.current\) \{\s+setIsSaving\(false\);/,
	);
	assert.doesNotMatch(
		formSource,
		/finally \{\s*saveInFlightRef\.current = false;\s+setIsSaving\(false\);/,
	);
	assert.match(
		formSource,
		/type="button"[\s\S]*?onClick=\{onCancel\}[\s\S]*?disabled=\{isSaving\}[\s\S]*?aria-busy=\{isSaving\}[\s\S]*?aria-label=\{cancelButtonLabel\}[\s\S]*?title=\{cancelButtonLabel\}/,
	);
	assert.match(formSource, /\{cancelButtonText\}/);
	assert.doesNotMatch(
		formSource,
		/const cancelButtonText = isSaving\s*\?\s*["']개체 저장 중\.\.\.["']\s*:\s*["']취소["'];?/,
	);
	assert.match(
		formSource,
		/onClick=\{onCancel\}\s+disabled=\{isSaving\}\s+aria-busy=\{isSaving\}[\s\S]*?className="btn btn-ghost btn-icon"/,
	);
	assert.match(
		formSource,
		/type="submit"[\s\S]*?disabled=\{isSaving\}[\s\S]*?aria-busy=\{isSaving\}[\s\S]*?aria-label=\{submitButtonLabel\}[\s\S]*?title=\{submitButtonLabel\}/,
	);
	assert.match(formSource, /\{submitButtonText\}/);
	assert.doesNotMatch(formSource, /\{isSaving \? ["']개체 정보 저장 중\.\.\.["'] : ["']저장하기["']\}/);
});

test("cattle form normalizes malformed building payloads before rendering", () => {
	const formSource = readSource("components/forms/CattleForm.js");

	assert.match(
		formSource,
		/import \{ useEffect, useMemo, useRef, useState \} from ['"]react['"];/,
	);
	assert.match(
		formSource,
		/function normalizeCattleFormBuildings\(buildings\) \{/,
	);
	assert.match(formSource, /return Array\.isArray\(buildings\)/);
	assert.match(
		formSource,
		/\.filter\(\(\s*building\s*\)\s*=>\s*building\s*&&\s*typeof\s*building\s*===\s*['"]object['"]\)/,
	);
	assert.match(
		formSource,
		/id: building\.id \?\? `cattle-building-\$\{index\}`/,
	);
	assert.match(formSource, /['"]축사 이름 미등록['"]/);
	assert.doesNotMatch(formSource, /['"]축사명 미등록['"]/);
	assert.match(
		formSource,
		/const safeBuildings = useMemo\(\s*\(\s*\)\s*=>\s*normalizeCattleFormBuildings\(buildings\),\s*\[buildings\],?\s*\);/,
	);
	assert.match(
		formSource,
		/defaultValues: createCattleFormValues\(cattle, safeBuildings\)/,
	);
	assert.match(
		formSource,
		/reset\(createCattleFormValues\(cattle, safeBuildings\)\);/,
	);
	assert.match(formSource, /\}, \[safeBuildings, cattle, reset\]\);/);
	assert.match(formSource, /safeBuildings\.map\(\(building\) => \(/);
	assert.doesNotMatch(
		formSource,
		/createCattleFormValues\(cattle, buildings\)/,
	);
	assert.doesNotMatch(formSource, /buildings\.map\(\(building\) => \(/);
});

test("cattle detail normalizes malformed building payloads before lookup", () => {
	const detailSource = readSource("components/forms/CattleDetailModal.js");

	assert.match(
		detailSource,
		/import\s+\{\s*(?:useState|useEffect|useMemo|useRef),\s*(?:useState|useEffect|useMemo|useRef),\s*(?:useState|useEffect|useMemo|useRef),\s*(?:useState|useEffect|useMemo|useRef)\s*\}\s*from\s+["']react["'];?/,
	);
	assert.match(
		detailSource,
		/function normalizeDetailBuildings\(buildings\) \{/,
	);
	assert.match(detailSource, /return Array\.isArray\(buildings\)/);
	assert.match(
		detailSource,
		/\.filter\(\(\s*building\s*\)\s*=>\s*building\s*&&\s*typeof\s*building\s*===\s*['"]object['"]\)/,
	);
	assert.match(
		detailSource,
		/id: building\.id \?\? `detail-building-\$\{index\}`/,
	);
	assert.match(detailSource, /['"]축사 이름 미등록['"]/);
	assert.doesNotMatch(detailSource, /['"]축사명 미등록['"]/);
	assert.match(
		detailSource,
		/const safeBuildings = useMemo\(\s*\(\s*\)\s*=>\s*normalizeDetailBuildings\(buildings\),\s*\[buildings\],?\s*\);/,
	);
	assert.match(
		detailSource,
		/safeBuildings\.find\(\(building\) => building\.id === cattle\.buildingId\)/,
	);
	assert.doesNotMatch(
		detailSource,
		/buildings\.find\(\(building\) => building\.id === cattle\.buildingId\)/,
	);
});

test("cattle detail breeding records wait for async saves before re-enabling submit actions", () => {
	const detailSource = readSource("components/forms/CattleDetailModal.js");

	assert.match(
		detailSource,
		/const \[isBreedingSaving, setIsBreedingSaving\] = useState\(false\)/,
	);
	assert.match(detailSource, /const mountedRef = useRef\(false\)/);
	assert.match(detailSource, /const breedingSaveInFlightRef = useRef\(false\)/);
	assert.match(
		detailSource,
		/useEffect\(\(\) => \{\s+mountedRef\.current = true;[\s\S]*?return \(\) => \{\s+mountedRef\.current = false;\s+breedingSaveInFlightRef\.current = false;/,
	);
	assert.match(
		detailSource,
		/breedingSaveInFlightRef\.current = false;\s+deferCattleDetailTask\(\(\) => \{[\s\S]*?setIsBreedingSaving\(false\);[\s\S]*?return \(\) => \{\s+cancelled = true;\s+\};\s+\}, \[cattle\?\.id\]\);/,
	);
	assert.match(
		detailSource,
		/if \(breedingSaveInFlightRef\.current \|\| isBreedingSaving\) \{\s+return;\s+\}/,
	);
	assert.match(detailSource, /breedingSaveInFlightRef\.current = true;/);
	assert.match(detailSource, /setIsBreedingSaving\(true\);/);
	assert.match(detailSource, /await onUpdate\(nextCattle,/);
	assert.match(
		detailSource,
		/if \(saved !== false && mountedRef\.current\) \{\s+setActiveBreedingAction\(null\);/,
	);
	assert.doesNotMatch(
		detailSource,
		/if \(saved !== false\) \{\s+setActiveBreedingAction\(null\);/,
	);
	assert.match(
		detailSource,
		/finally \{\s+breedingSaveInFlightRef\.current = false;\s+if \(mountedRef\.current\) \{\s+setIsBreedingSaving\(false\);/,
	);
	assert.doesNotMatch(
		detailSource,
		/finally \{\s+breedingSaveInFlightRef\.current = false;\s+setIsBreedingSaving\(false\);/,
	);
	assert.match(
		detailSource,
		/const breedingCancelButtonLabel = isBreedingSaving\s*\?\s*["']번식 기록 저장 중에는 취소할 수 없습니다["']\s*:\s*["']번식 기록 취소["'];?/,
	);
	assert.match(
		detailSource,
		/const breedingSubmitButtonLabel = isBreedingSaving\s*\?\s*["']번식 기록 저장 중["']\s*:\s*["']번식 기록 저장["'];?/,
	);
	assert.match(
		detailSource,
		/const breedingSubmitButtonText = isBreedingSaving\s*\?\s*["']번식 기록 저장 중\.\.\.["']\s*:\s*["']번식 기록 저장["'];?/,
	);
	assert.match(
		detailSource,
		/onClick=\{\(\) => openBreedingForm\(["']estrus["']\)\}[\s\S]*?disabled=\{isDetailBusy\}[\s\S]*?aria-busy=\{isDetailBusy\}[\s\S]*?aria-label=\{estrusButtonLabel\}/,
	);
	assert.match(
		detailSource,
		/onClick=\{\(\) => openBreedingForm\(["']pregnancy["']\)\}[\s\S]*?disabled=\{isDetailBusy\}[\s\S]*?aria-busy=\{isDetailBusy\}[\s\S]*?aria-label=\{pregnancyButtonLabel\}/,
	);
	assert.match(
		detailSource,
		/type="button"[\s\S]*?onClick=\{\(\) => setActiveBreedingAction\(null\)\}[\s\S]*?disabled=\{isBreedingSaving\}[\s\S]*?aria-busy=\{isBreedingSaving\}[\s\S]*?aria-label=\{breedingCancelButtonLabel\}[\s\S]*?title=\{breedingCancelButtonLabel\}/,
	);
	assert.match(
		detailSource,
		/type="submit"[\s\S]*?disabled=\{isBreedingSaving\}[\s\S]*?aria-busy=\{isBreedingSaving\}[\s\S]*?aria-label=\{breedingSubmitButtonLabel\}[\s\S]*?title=\{breedingSubmitButtonLabel\}/,
	);
	assert.match(
		detailSource,
		/\{breedingSubmitButtonText\}/,
	);
	assert.doesNotMatch(detailSource, /\{isBreedingSaving \? ["']번식 기록 저장 중\.\.\.["'] : ["']저장["']\}/);
});

test("cattle detail decorative icons are hidden from assistive tech", () => {
	const source = readSource("components/forms/CattleDetailModal.js");
	const commonSource = readSource("components/ui/common.js");

	assert.match(
		source,
		/function SectionTitle\(\{ icon, title, color = "var\(--color-text\)" \}\) \{[\s\S]*?<div\s+role="heading"\s+aria-level=\{3\}/,
	);
	assert.match(
		source,
		/<span\s+aria-hidden="true"\s+style=\{\{\s*fontSize:\s*["']18px["'],\s*lineHeight:\s*1\s*\}\}>[\s\S]*?\{icon\}[\s\S]*?<\/span>[\s\S]*?\{title\}/,
	);
	assert.match(source, /<div[\s\S]*?aria-hidden="true"[\s\S]*?style=\{\{/);
	for (const iconName of ["BackIcon", "EditIcon", "TrashIcon"]) {
		assert.match(
			commonSource,
			new RegExp(
				`export const ${iconName} = \\(\\) => \\(\\s*<svg\\s+aria-hidden="true"\\s+focusable="false"`,
			),
		);
	}
});

test("cattle form and detail reset paths avoid lint suppressions", () => {
	const formSource = readSource("components/forms/CattleForm.js");
	const detailSource = readSource("components/forms/CattleDetailModal.js");

	assert.match(
		formSource,
		/function deferCattleFormTask\(callback\) \{\s+try \{\s+queueMicrotask\(callback\);\s+\} catch \{\s+Promise\.resolve\(\)\.then\(callback\);/,
	);
	assert.match(
		formSource,
		/deferCattleFormTask\(\(\) => \{\s+if \(cancelled\) \{\s+return;\s+\}\s+setLookupLoading\(false\);\s+setLookupMsg\(null\);\s+setIsSaving\(false\);/,
	);
	assert.match(
		formSource,
		/const handleCattleFormSubmit = \(event\) => \{\s+void handleSubmit\(submitForm\)\(event\);\s+\};/,
	);
	assert.match(formSource, /onSubmit=\{handleCattleFormSubmit\}/);
	assert.match(
		detailSource,
		/function deferCattleDetailTask\(callback\) \{\s+try \{\s+queueMicrotask\(callback\);\s+\} catch \{\s+Promise\.resolve\(\)\.then\(callback\);/,
	);
	assert.match(
		detailSource,
		/deferCattleDetailTask\(\(\) => \{\s+if \(cancelled\) \{\s+return;\s+\}\s+setActiveBreedingAction\(null\);\s+setBreedingDate\(toInputDate\(new Date\(\)\)\);\s+setBreedingError\(""\);\s+setIsBreedingSaving\(false\);/,
	);
	assert.doesNotMatch(
		formSource,
		/queueMicrotask\(\(\) => \{\s+if \(cancelled\) \{/,
	);
	assert.doesNotMatch(
		detailSource,
		/queueMicrotask\(\(\) => \{\s+if \(cancelled\) \{/,
	);
	assert.doesNotMatch(formSource, /eslint-disable/);
	assert.doesNotMatch(detailSource, /eslint-disable/);
	assert.doesNotMatch(formSource, /onSubmit=\{handleSubmit\(submitForm\)\}/);
});
