import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = path.resolve(__dirname, '..');

function readSource(relativePath) {
  return readFileSync(path.join(SRC_ROOT, relativePath), 'utf8');
}

test('cattle detail breeding actions use an in-app date form instead of browser prompts', () => {
  const source = readSource('components/forms/CattleDetailModal.js');

  assert.doesNotMatch(source, /\bprompt\s*\(/);
  assert.match(source, /activeBreedingAction/);
  assert.match(source, /type="date"/);
  assert.match(source, /handleSaveBreedingRecord/);
  assert.match(source, /onUpdate\(nextCattle/);
  assert.match(source, /successTitle: activeBreedingAction === 'pregnancy'/);
});

test('cattle detail breeding date validation is announced with the date input', () => {
  const source = readSource('components/forms/CattleDetailModal.js');

  assert.match(source, /const breedingDateErrorId = "breeding-record-date-error"/);
  assert.match(source, /function toStrictInputDate\(value\)/);
  assert.match(source, /date\.toISOString\(\)\.slice\(0, 10\) !== value/);
  assert.match(source, /const selectedDate = toStrictInputDate\(breedingDate\)/);
  assert.doesNotMatch(source, /const selectedDate = new Date\(`\$\{breedingDate\}T00:00:00`\)/);
  assert.match(source, /aria-invalid=\{Boolean\(breedingError\)\}/);
  assert.match(source, /aria-describedby=\{breedingError \? breedingDateErrorId : undefined\}/);
  assert.match(source, /<div id=\{breedingDateErrorId\} role="alert"/);
});

test('cattle detail shows a real calving due date from pregnancy date', () => {
  const source = readSource('components/forms/CattleDetailModal.js');

  assert.match(source, /getCalvingDate/);
  assert.match(source, /label="분만 예정일" value=\{cattle\.pregnancyDate \? formatDate\(getCalvingDate\(cattle\.pregnancyDate\)\) : "-"\}/);
  assert.doesNotMatch(source, /계산중/);
});

test('cattle form and detail icon-only navigation controls have Korean labels', () => {
  const formSource = readSource('components/forms/CattleForm.js');
  const detailSource = readSource('components/forms/CattleDetailModal.js');

  assert.match(formSource, /aria-label="개체 목록으로 돌아가기"/);
  assert.match(formSource, /title="개체 목록으로 돌아가기"/);
  assert.match(formSource, /role="dialog"/);
  assert.match(formSource, /aria-modal="true"/);
  assert.match(formSource, /aria-labelledby="cattle-form-title"/);
  assert.match(formSource, /const dialogRef = useRef\(null\)/);
  assert.match(formSource, /dialogRef\.current\?\.focus\(\)/);
  assert.match(formSource, /tabIndex=\{-1\}/);
  assert.match(formSource, /onKeyDown=\{handleDialogKeyDown\}/);
  assert.match(formSource, /if \(event\.key === 'Escape'\) \{\s+if \(isSaving\) \{\s+return;\s+\}\s+onCancel\(\);/);
  assert.match(formSource, /id="cattle-form-title"/);
  assert.match(formSource, /<label htmlFor="cattle-name"/);
  assert.match(formSource, /id="cattle-name"/);
  assert.match(formSource, /<label htmlFor="cattle-tag-number"/);
  assert.match(formSource, /id="cattle-tag-number"/);
  assert.match(formSource, /<label htmlFor="cattle-building"/);
  assert.match(formSource, /id="cattle-building"[^>]*aria-invalid=\{Boolean\(errors\.buildingId\)\}/);
  assert.match(formSource, /<label htmlFor="cattle-pen-number"/);
  assert.match(formSource, /id="cattle-pen-number"[^>]*aria-invalid=\{Boolean\(errors\.penNumber\)\}/);
  assert.match(formSource, /<label htmlFor="cattle-gender"/);
  assert.match(formSource, /id="cattle-gender"[^>]*aria-invalid=\{Boolean\(errors\.gender\)\}/);
  assert.match(formSource, /<label htmlFor="cattle-status"/);
  assert.match(formSource, /id="cattle-status"[^>]*aria-invalid=\{Boolean\(errors\.status\)\}/);
  assert.match(formSource, /<label htmlFor="cattle-birth-date"/);
  assert.match(formSource, /id="cattle-birth-date"[^>]*aria-invalid=\{Boolean\(errors\.birthDate\)\}/);
  assert.match(formSource, /<label htmlFor="cattle-weight"/);
  assert.match(formSource, /id="cattle-weight"[^>]*aria-invalid=\{Boolean\(errors\.weight\)\}/);
  assert.match(formSource, /<label htmlFor="cattle-purchase-price"/);
  assert.match(formSource, /id="cattle-purchase-price"[\s\S]*?aria-invalid=\{Boolean\(errors\.purchasePrice\)\}/);
  assert.match(formSource, /<label htmlFor="cattle-purchase-date"/);
  assert.match(formSource, /id="cattle-purchase-date"[^>]*aria-invalid=\{Boolean\(errors\.purchaseDate\)\}/);
  assert.match(formSource, /<label htmlFor="cattle-genetic-father"/);
  assert.match(formSource, /id="cattle-genetic-father"[\s\S]*?aria-invalid=\{Boolean\(errors\.geneticInfo\?\.father\)\}/);
  assert.match(formSource, /<label htmlFor="cattle-genetic-mother"/);
  assert.match(formSource, /id="cattle-genetic-mother"[\s\S]*?aria-invalid=\{Boolean\(errors\.geneticInfo\?\.mother\)\}/);
  assert.match(formSource, /<label htmlFor="cattle-memo"/);
  assert.match(formSource, /id="cattle-memo"[\s\S]*?aria-invalid=\{Boolean\(errors\.memo\)\}/);
  assert.match(detailSource, /aria-label="개체 상세 닫기"/);
  assert.match(detailSource, /title="개체 상세 닫기"/);
  assert.match(detailSource, /type="button"\s+onClick=\{onClose\}/);
  assert.match(detailSource, /aria-label=\{`\$\{cattle\.name\} 개체 정보 수정`\}/);
  assert.match(detailSource, /title="개체 정보 수정"/);
  assert.match(detailSource, /type="button"\s+onClick=\{onEdit\}/);
  assert.match(detailSource, /aria-label=\{`\$\{cattle\.name\} 개체 보관 처리`\}/);
  assert.match(detailSource, /title="개체 보관 처리"/);
  assert.match(detailSource, /> 보관<\/button>/);
  assert.match(detailSource, /type="button"[\s\S]*?onClick=\{onDelete\}/);
  assert.match(detailSource, /role="dialog"/);
  assert.match(detailSource, /aria-modal="true"/);
  assert.match(detailSource, /aria-labelledby="cattle-detail-title"/);
  assert.match(detailSource, /const dialogRef = useRef\(null\)/);
  assert.match(detailSource, /dialogRef\.current\?\.focus\(\)/);
  assert.match(detailSource, /tabIndex=\{-1\}/);
  assert.match(detailSource, /onKeyDown=\{handleDialogKeyDown\}/);
  assert.match(detailSource, /const isDetailBusy = isDeleting \|\| isBreedingSaving/);
  assert.match(detailSource, /if \(event\.key === 'Escape'\) \{\s+if \(isDetailBusy\) \{\s+return;\s+\}\s+onClose\(\);/);
  assert.match(detailSource, /id="cattle-detail-title"/);
  assert.doesNotMatch(formSource, /aria-label="Back"/);
  assert.doesNotMatch(detailSource, /aria-label="Close"/);
});

test('cattle detail archive actions wait for async deletes before re-enabling submit actions', () => {
  const dashboardSource = readSource('components/DashboardClient.js');
  const detailSource = readSource('components/forms/CattleDetailModal.js');

  assert.match(dashboardSource, /const \[deletingCattleId, setDeletingCattleId\] = useState\(null\)/);
  assert.match(dashboardSource, /if \(deletingCattleId\) \{\s+return false;\s+\}/);
  assert.match(dashboardSource, /setDeletingCattleId\(id\);/);
  assert.match(dashboardSource, /await deleteCattle\(id\);/);
  assert.match(dashboardSource, /finally \{\s+setDeletingCattleId\(null\);/);
  assert.match(dashboardSource, /isDeleting=\{deletingCattleId === selectedCow\.id\}/);
  assert.match(detailSource, /isDeleting = false/);
  assert.match(detailSource, /onClick=\{onClose\}\s+disabled=\{isDetailBusy\}\s+aria-busy=\{isDetailBusy\}/);
  assert.match(detailSource, /onClick=\{onEdit\}[\s\S]*?disabled=\{isDetailBusy\}[\s\S]*?aria-busy=\{isDetailBusy\}/);
  assert.match(detailSource, /onClick=\{onDelete\}[\s\S]*?disabled=\{isDetailBusy\}[\s\S]*?aria-busy=\{isDetailBusy\}/);
  assert.match(detailSource, /if \(breedingSaveInFlightRef\.current \|\| isDetailBusy\) \{\s+return;\s+\}/);
  assert.match(detailSource, /onClick=\{\(\) => openBreedingForm\('estrus'\)\}[\s\S]*?disabled=\{isDetailBusy\}/);
  assert.match(detailSource, /onClick=\{\(\) => openBreedingForm\('pregnancy'\)\}[\s\S]*?disabled=\{isDetailBusy\}/);
});

test('cattle form validation messages are announced with their controls', () => {
  const formSource = readSource('components/forms/CattleForm.js');

  [
    ['name', 'errors.name'],
    ['building', 'errors.buildingId'],
    ['pen-number', 'errors.penNumber'],
    ['gender', 'errors.gender'],
    ['status', 'errors.status'],
    ['birth-date', 'errors.birthDate'],
    ['weight', 'errors.weight'],
    ['purchase-price', 'errors.purchasePrice'],
    ['purchase-date', 'errors.purchaseDate'],
    ['genetic-father', 'errors.geneticInfo?.father'],
    ['genetic-mother', 'errors.geneticInfo?.mother'],
    ['memo', 'errors.memo'],
  ].forEach(([field, errorPath]) => {
    const errorId = `cattle-${field}-error`;
    const escapedErrorPath = errorPath.replace(/[?.]/g, '\\$&');

    assert.match(
      formSource,
      new RegExp(`aria-describedby=\\{${escapedErrorPath} \\? "${errorId}" : undefined\\}`),
    );
    assert.match(formSource, new RegExp(`<div id="${errorId}" role="alert"`));
  });
});

test('cattle tag lookup progress and results are announced', () => {
  const formSource = readSource('components/forms/CattleForm.js');

  assert.match(formSource, /const lookupInFlightRef = useRef\(false\)/);
  assert.match(formSource, /const lookupRequestIdRef = useRef\(0\)/);
  assert.match(formSource, /const mountedRef = useRef\(true\)/);
  assert.match(formSource, /lookupRequestIdRef\.current \+= 1;/);
  assert.match(formSource, /if \(lookupInFlightRef\.current\) \{\s+return;\s+\}/);
  assert.match(formSource, /lookupInFlightRef\.current = true;/);
  assert.match(formSource, /const requestId = lookupRequestIdRef\.current \+ 1;/);
  assert.match(formSource, /lookupRequestIdRef\.current = requestId;/);
  assert.match(formSource, /if \(!mountedRef\.current \|\| lookupRequestIdRef\.current !== requestId\) \{\s+return;\s+\}/);
  assert.match(formSource, /if \(lookupRequestIdRef\.current === requestId\) \{\s+lookupInFlightRef\.current = false;/);
  assert.match(formSource, /const tagNumberErrorId = 'cattle-tag-number-error'/);
  assert.match(formSource, /const tagLookupMessageId = 'cattle-tag-lookup-message'/);
  assert.match(formSource, /const tagNumberDescriptionIds = \[/);
  assert.match(formSource, /errors\.tagNumber \? tagNumberErrorId : null/);
  assert.match(formSource, /lookupMsg \? tagLookupMessageId : null/);
  assert.match(formSource, /aria-describedby=\{tagNumberDescriptionIds\}/);
  assert.match(formSource, /aria-busy=\{lookupLoading\}/);
  assert.match(formSource, /id=\{tagLookupMessageId\}/);
  assert.match(formSource, /role=\{lookupMsg\.ok \? 'status' : 'alert'\}/);
  assert.match(formSource, /aria-live=\{lookupMsg\.ok \? 'polite' : 'assertive'\}/);
});

test('cattle form waits for async saves before re-enabling submit actions', () => {
  const formSource = readSource('components/forms/CattleForm.js');

  assert.match(formSource, /const \[isSaving, setIsSaving\] = useState\(false\)/);
  assert.match(formSource, /const saveInFlightRef = useRef\(false\)/);
  assert.match(formSource, /saveInFlightRef\.current = false;\s+\}, \[buildings, cattle, reset\]\);/);
  assert.match(formSource, /setIsSaving\(false\);/);
  assert.match(formSource, /const cancelButtonLabel = isSaving \? '개체 저장 중에는 취소할 수 없습니다' : '개체 저장 취소';/);
  assert.match(formSource, /const submitForm = async \(values\) => \{/);
  assert.match(formSource, /if \(saveInFlightRef\.current\) \{\s+return;\s+\}/);
  assert.match(formSource, /saveInFlightRef\.current = true;/);
  assert.match(formSource, /setIsSaving\(true\);/);
  assert.match(formSource, /await onSubmit\(\{/);
  assert.match(formSource, /finally \{\s*saveInFlightRef\.current = false;\s+setIsSaving\(false\);/);
  assert.match(formSource, /type="button" onClick=\{onCancel\} disabled=\{isSaving\} aria-busy=\{isSaving\} aria-label=\{cancelButtonLabel\} title=\{cancelButtonLabel\}/);
  assert.match(formSource, /onClick=\{onCancel\}\s+disabled=\{isSaving\}\s+aria-busy=\{isSaving\}[\s\S]*?className="btn btn-ghost btn-icon"/);
  assert.match(formSource, /type="submit" disabled=\{isSaving\} aria-busy=\{isSaving\}/);
});

test('cattle detail breeding records wait for async saves before re-enabling submit actions', () => {
  const detailSource = readSource('components/forms/CattleDetailModal.js');

  assert.match(detailSource, /const \[isBreedingSaving, setIsBreedingSaving\] = useState\(false\)/);
  assert.match(detailSource, /const breedingSaveInFlightRef = useRef\(false\)/);
  assert.match(detailSource, /breedingSaveInFlightRef\.current = false;\s+\}, \[cattle\?\.id\]\);/);
  assert.match(detailSource, /if \(breedingSaveInFlightRef\.current \|\| isBreedingSaving\) \{\s+return;\s+\}/);
  assert.match(detailSource, /breedingSaveInFlightRef\.current = true;/);
  assert.match(detailSource, /setIsBreedingSaving\(true\);/);
  assert.match(detailSource, /await onUpdate\(nextCattle,/);
  assert.match(detailSource, /finally \{\s+breedingSaveInFlightRef\.current = false;\s+setIsBreedingSaving\(false\);/);
  assert.match(detailSource, /onClick=\{\(\) => openBreedingForm\('estrus'\)\}[\s\S]*?disabled=\{isBreedingSaving\}/);
  assert.match(detailSource, /onClick=\{\(\) => openBreedingForm\('pregnancy'\)\}[\s\S]*?disabled=\{isBreedingSaving\}/);
  assert.match(detailSource, /type="button"[\s\S]*?onClick=\{\(\) => setActiveBreedingAction\(null\)\}[\s\S]*?disabled=\{isBreedingSaving\}/);
  assert.match(detailSource, /type="submit"[\s\S]*?disabled=\{isBreedingSaving\}[\s\S]*?aria-busy=\{isBreedingSaving\}/);
});

test('cattle detail decorative icons are hidden from assistive tech', () => {
  const source = readSource('components/forms/CattleDetailModal.js');

  assert.match(source, /<span aria-hidden="true" style=\{\{fontSize:"18px",lineHeight:1\}\}>\{icon\}<\/span> \{title\}/);
  assert.match(source, /<div aria-hidden="true" style=\{\{/);
});
