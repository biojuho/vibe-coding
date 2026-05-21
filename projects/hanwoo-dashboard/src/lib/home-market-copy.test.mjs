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

test('home dashboard fallback and panel labels use Korean product copy', () => {
  const source = readSource('components/DashboardClient.js');

  assert.match(source, /Joolife 한우 농장/);
  assert.match(source, /오늘 요약/);
  assert.match(source, /빠른 기록/);
  assert.match(source, /운영 준비/);
  assert.doesNotMatch(source, /Joolife Dashboard/);
  assert.doesNotMatch(source, /Today Brief/);
  assert.doesNotMatch(source, /Quick Record/);
  assert.doesNotMatch(source, /Farm Setup/);
  assert.match(source, /대시보드 데이터를 불러오지 못했습니다/);
  assert.match(source, /대시보드 데이터를 불러오는 데 시간이 오래 걸리고 있습니다/);
  assert.match(source, /모든 권리 보유/);
  assert.match(source, /운영 문의: joolife@joolife\.io\.kr/);
  assert.doesNotMatch(source, /000-00-00000/);
  assert.doesNotMatch(source, /사업자등록번호: 000/);
  assert.doesNotMatch(source, /Failed to load/);
  assert.doesNotMatch(source, /Loading .* timed out/);
  assert.doesNotMatch(source, /All rights reserved/);
});

test('dashboard cattle mutation catch paths use safe Korean fallback copy', () => {
  const source = readSource('components/DashboardClient.js');

  assert.match(source, /요청 처리 중 오류가 발생했습니다\. 잠시 후 다시 시도해 주세요\./);
  assert.match(source, /개체를 보관 처리할까요\?/);
  assert.match(source, /보관 기록으로 남습니다/);
  assert.match(source, /개체를 보관 처리했습니다/);
  assert.match(source, /개체 보관 처리에 실패했습니다/);
  assert.match(source, /console\.error\('Failed to add cattle:', error\);/);
  assert.match(source, /console\.error\('Failed to update cattle:', error\);/);
  assert.doesNotMatch(source, /showError\(errorTitle, error\.message\)/);
  assert.doesNotMatch(source, /개체를 삭제할까요/);
  assert.doesNotMatch(source, /개체를 삭제했습니다/);
  assert.doesNotMatch(source, /개체 삭제에 실패했습니다/);
});

test('dashboard drag-and-drop cattle moves wait for confirmation and update before accepting another move', () => {
  const source = readSource('components/DashboardClient.js');

  assert.match(source, /const movingCattleIdRef = useRef\(null\)/);
  assert.match(source, /if \(movingCattleIdRef\.current\) return false;/);
  assert.match(source, /movingCattleIdRef\.current = cattleId;/);
  assert.match(source, /const shouldMove = await confirm\(\{/);
  assert.match(source, /return handleUpdateCattle\(updated, \{/);
  assert.match(source, /finally \{\s+movingCattleIdRef\.current = null;/);
  assert.match(source, /개체를 이동할까요\?/);
  assert.match(source, /개체를 이동했습니다/);
});

test('calving flow requires an operator-entered calf tag number', () => {
  const dashboardSource = readSource('components/DashboardClient.js');
  const calvingTabSource = readSource('components/tabs/CalvingTab.js');
  const formSchemaSource = readSource('lib/formSchemas.js');

  assert.match(calvingTabSource, /송아지 이력번호/);
  assert.match(calvingTabSource, /register\('calfTagNumber'\)/);
  assert.match(calvingTabSource, /calfTagNumber: values\.calfTagNumber/);
  assert.match(formSchemaSource, /const DATE_INPUT_PATTERN = \/\^\\d\{4\}-\\d\{2\}-\\d\{2\}\$\/;/);
  assert.match(formSchemaSource, /const PLAIN_NUMBER_INPUT_PATTERN = \/\^-\?\(\?:\\d\+\|\\d\+\\\.\\d\+\|\\\.\\d\+\)\$\/;/);
  assert.match(formSchemaSource, /const toPlainNumber = \(value\) =>/);
  assert.match(formSchemaSource, /PLAIN_NUMBER_INPUT_PATTERN\.test\(normalized\)/);
  assert.match(formSchemaSource, /const isDateInputString = \(value\) =>/);
  assert.match(formSchemaSource, /parsed\.toISOString\(\)\.slice\(0, 10\) === value/);
  assert.match(formSchemaSource, /\.refine\(isDateInputString,/);
  assert.doesNotMatch(formSchemaSource, /z\.coerce\.number/);
  assert.doesNotMatch(formSchemaSource, /new Date\(value\)\.getTime\(\)/);
  assert.match(formSchemaSource, /calfTagNumber: requiredText\('송아지 이력번호를 입력해 주세요\.', 30\)/);
  assert.doesNotMatch(dashboardSource, /KR0000/);
  assert.doesNotMatch(dashboardSource, /Math\.random\(\) \* 900000/);
});

test('dashboard full-list loading failures show retry feedback instead of silent placeholders', () => {
  const source = readSource('components/DashboardClient.js');

  assert.match(source, /FULL_CATTLE_LOAD_ERROR_MESSAGE/);
  assert.match(source, /FULL_SALES_LOAD_ERROR_MESSAGE/);
  assert.match(source, /setAllCattleLoadError\(FULL_CATTLE_LOAD_ERROR_MESSAGE\)/);
  assert.match(source, /setAllSalesLoadError\(FULL_SALES_LOAD_ERROR_MESSAGE\)/);
  assert.match(source, /const preloadForTab = useCallback/);
  assert.match(source, /preloadForTab\(nextTab\)/);
  assert.match(source, /preloadForTab\(action\.targetTab\)/);
  assert.match(source, /onNavigate=\{handleTabChange\}/);
  assert.match(source, /ensureAllCattleLoaded\(\{ silent: true \}\)\.catch\(\(\) => \{\}\)/);
  assert.match(source, /ensureAllSalesLoaded\(\{ silent: true \}\)\.catch\(\(\) => \{\}\)/);
  assert.match(source, /다시 불러오기/);
  assert.doesNotMatch(source, /void ensureAllCattleLoaded\(\{ silent: true \}\);/);
  assert.doesNotMatch(source, /void ensureAllSalesLoaded\(\{ silent: true \}\);/);
});

test('home building navigation uses semantic buttons', () => {
  const source = readSource('components/DashboardClient.js');
  const css = readSource('app/globals.css');

  assert.match(source, /<button\s+type="button"\s+className="empty-state-cta/);
  assert.match(source, /onClick=\{\(\) => handleTabChange\('settings'\)\}/);
  assert.match(source, /type="button"\s+onClick=\{\(\) => handleSelectBuilding\(building\.id\)\}/);
  assert.match(source, /className="clay-surface rounded-\[28px\][^"]*group\/building w-full text-left"/);
  assert.match(css, /\.empty-state-cta \{\s+background:[\s\S]*?font: inherit;/);
  assert.doesNotMatch(source, /<div className="empty-state-cta[^"]*"[^>]*onClick/);
  assert.doesNotMatch(source, /<Card key=\{building\.id\} onClick/);
});

test('home dashboard icon-only actions expose Korean accessible labels', () => {
  const source = readSource('components/DashboardClient.js');

  assert.match(source, /aria-label="알림 센터 열기"/);
  assert.match(source, /title="알림 센터"/);
  assert.match(source, /aria-label="개체 등록 열기"/);
  assert.match(source, /title="개체 등록"/);
  assert.match(source, /aria-label="축사 목록으로 돌아가기"/);
  assert.match(source, /aria-label="칸 목록으로 돌아가기"/);
  assert.match(source, /<Bell className="h-5 w-5" aria-hidden="true" \/>/);
  assert.match(source, /<Plus className="h-5 w-5" aria-hidden="true" \/>/);
  assert.match(source, /<ArrowLeft className="h-5 w-5" aria-hidden="true" \/>/);
  assert.match(source, /shadow-\[0_0_10px_hsl\(var\(--destructive\)\)\]"\s+aria-hidden="true"/);
  assert.doesNotMatch(source, /aria-label="Notifications"/);
  assert.doesNotMatch(source, /aria-label="Add cattle"/);
  assert.doesNotMatch(source, /aria-label="Back"/);
});

test('market price widget uses Korean product copy for visible states', () => {
  const source = readSource('components/widgets/MarketPriceWidget.js');

  assert.match(source, /function toValidUpdatedAt\(value, fallback = new Date\(\)\) \{/);
  assert.match(source, /return Number\.isNaN\(date\.getTime\(\)\) \? fallback : date;/);
  assert.match(source, /function normalizePriceSnapshot\(data\) \{/);
  assert.match(source, /bull: data\.bull \?\? \{\}/);
  assert.match(source, /cow: data\.cow \?\? \{\}/);
  assert.match(source, /useState\(\(\) => normalizePriceSnapshot\(initialData\)\)/);
  assert.match(source, /setPrices\(normalizePriceSnapshot\(data\)\)/);
  assert.match(source, /initialData \? toValidUpdatedAt\(initialData\.fetchedAt\) : null/);
  assert.match(source, /setLastUpdated\(toValidUpdatedAt\(data\?\.fetchedAt\)\)/);

  assert.match(source, /한우 시세를 불러오는 중입니다/);
  assert.match(source, /지금은 한우 시세 데이터를 확인할 수 없습니다/);
  assert.match(source, /시세 흐름/);
  assert.match(source, /한우 도매 시세/);
  assert.match(source, /가중평균 거래가/);
  assert.match(source, /실시간 KAPE/);
  assert.match(source, /저장된 KAPE/);
  assert.match(source, /이전 저장값/);
  assert.match(source, /수소 \/ kg/);
  assert.match(source, /암소 \/ kg/);
  assert.match(source, /갱신/);
  assert.match(source, /출처: KAPE/);
  assert.match(source, /role="status" aria-live="polite"/);
  assert.match(source, /disabled=\{loading\}\s+aria-busy=\{loading\}/);
  assert.match(source, /aria-label=\{loading \? '시세 갱신 중' : '한우 시세 새로고침'\}/);
  assert.match(source, /title=\{loading \? '시세 갱신 중' : '한우 시세 새로고침'\}/);
  assert.match(source, /<RefreshCwIcon aria-hidden="true"/);
  assert.doesNotMatch(source, /Loading market prices/);
  assert.doesNotMatch(source, /Market price data is unavailable/);
  assert.doesNotMatch(source, /Market Pulse/);
  assert.doesNotMatch(source, /Hanwoo Market Prices/);
  assert.doesNotMatch(source, /weighted average transaction price/);
  assert.doesNotMatch(source, /Live KAPE|Cached KAPE|Stale Cache|Unavailable/);
  assert.doesNotMatch(source, /Bull \/ kg|Cow \/ kg/);
  assert.doesNotMatch(source, />Updated /);
  assert.doesNotMatch(source, />Source: KAPE/);
  assert.doesNotMatch(source, /aria-label="Refresh"/);
  assert.doesNotMatch(source, /new Date\(initialData\.fetchedAt\)/);
  assert.doesNotMatch(source, /setLastUpdated\(data\?\.fetchedAt \? new Date\(data\.fetchedAt\) : new Date\(\)\)/);
  assert.doesNotMatch(source, /[吏媛異諛湲]/);
  assert.doesNotMatch(source, /\?[가-힣]/);
});

test('schedule calendar navigation exposes Korean accessible labels', () => {
  const source = readSource('components/tabs/ScheduleTab.js');

  assert.match(source, /aria-label="이전 달 보기"/);
  assert.match(source, /title="이전 달 보기"/);
  assert.match(source, /aria-label="다음 달 보기"/);
  assert.match(source, /title="다음 달 보기"/);
  assert.match(source, /<PlusCircle size=\{14\} aria-hidden="true" \/>/);
  assert.doesNotMatch(source, /aria-label="Previous month"/);
  assert.doesNotMatch(source, /aria-label="Next month"/);
});

test('schedule calendar date cells are semantic buttons', () => {
  const source = readSource('components/tabs/ScheduleTab.js');

  assert.match(source, /<button\s+type="button"\s+key=\{dateStr\}\s+onClick=\{\(\) => openFormForDate\(dateStr\)\}/);
  assert.match(source, /aria-label=\{`\$\{dateStr\} 일정 등록 열기`\}/);
  assert.match(source, /title=\{`\$\{dateStr\} 일정 등록 열기`\}/);
  assert.match(source, /textAlign: 'left'/);
  assert.doesNotMatch(source, /<div\s+key=\{dateStr\}\s+onClick=\{\(\) => openFormForDate\(dateStr\)\}/);
});

test('upcoming schedule toggle identifies the target event', () => {
  const source = readSource('components/tabs/ScheduleTab.js');

  assert.match(source, /aria-label=\{`\$\{event\.title\} 일정 완료 상태 변경`\}/);
  assert.match(source, /title=\{`\$\{event\.title\} 일정 완료 상태 변경`\}/);
});

test('weather widget uses Korean product copy for unavailable state', () => {
  const source = readSource('components/widgets/widgets.js');
  const dashboardSource = readSource('components/DashboardClient.js');
  const hookSource = readSource('lib/hooks/useWeather.js');

  assert.match(source, /toFiniteNumber \} from '@\/lib\/utils';/);
  assert.match(source, /const temp = toFiniteNumber\(weather\.temp\);/);
  assert.match(source, /const humidity = toFiniteNumber\(weather\.humidity\);/);
  assert.match(source, /const apparentTemp = toFiniteNumber\(weather\.apparentTemp, temp\);/);
  assert.match(source, /const windSpeed = toFiniteNumber\(weather\.windSpeed\);/);
  assert.match(source, /const tempMax = toFiniteNumber\(weather\.tempMax, temp\);/);
  assert.match(source, /const tempMin = toFiniteNumber\(weather\.tempMin, temp\);/);
  assert.match(source, /const precipitation = toFiniteNumber\(weather\.precipitation\);/);
  assert.match(source, /const thi=calcTHI\(temp,humidity\);/);

  assert.match(source, /날씨 확인 불가/);
  assert.match(source, /지금은 날씨 데이터를 확인할 수 없습니다/);
  assert.match(source, /'서울'/);
  assert.match(dashboardSource, /'서울'/);
  assert.match(hookSource, /'서울'/);
  assert.doesNotMatch(source, /Weather Unavailable/);
  assert.doesNotMatch(source, /Weather data is temporarily unavailable/);
  assert.match(source, /<div className="weather-icon-bg" aria-hidden="true">\{icon\}<\/div>/);
  assert.match(source, /<div aria-hidden="true" style=\{\{fontSize:"18px",marginBottom:"3px",lineHeight:1\}\}>\{item\.i\}<\/div>/);
  assert.match(source, /<span aria-hidden="true">📍<\/span> \{weather\.locationName\}/);
  assert.match(source, /<span aria-hidden="true">\{icon\}<\/span> \{desc\}/);
  assert.match(source, /<span aria-hidden="true">🐂<\/span> 온열지수: \{thiLevel\.label\}/);
  assert.match(source, /<span aria-hidden="true">📅<\/span> 3일 예보/);
  assert.match(source, /formatForecastDateLabel\(day\.date, \{ weekday: 'short', month: 'short', day: 'numeric' \}\)/);
  assert.match(source, /<div aria-label=\{getWeatherDesc\(day\.weatherCode\)\} style=\{\{fontSize:"24px",marginBottom:"4px"\}\}>\{getWeatherIcon\(day\.weatherCode\)\}<\/div>/);
  assert.match(source, /<span aria-hidden="true">🌧<\/span> 강수 \{day\.precipProb\}%/);
  assert.match(source, /<span aria-hidden="true">🐄<\/span> 가축 기상 경고/);
  assert.match(source, /<span aria-hidden="true">\{a\.icon\}<\/span> \{a\.msg\}/);
  assert.doesNotMatch(source, /Math\.round\(weather\.(?:temp|apparentTemp|tempMax|tempMin)\)/);
  assert.doesNotMatch(source, /\$\{weather\.(?:humidity|windSpeed|precipitation)\}/);
  assert.match(source, /Math\.round\(toFiniteNumber\(day\.tempMax\)\)/);
  assert.match(source, /Math\.round\(toFiniteNumber\(day\.tempMin\)\)/);
  assert.match(dashboardSource, /WEATHER_STALE_MESSAGE/);
  assert.match(hookSource, /WEATHER_STALE_MESSAGE/);
  assert.match(dashboardSource, /WEATHER_TIMEOUT_MESSAGE/);
  assert.match(hookSource, /WEATHER_TIMEOUT_MESSAGE/);
  assert.doesNotMatch(dashboardSource, /Showing the last available weather snapshot/);
  assert.doesNotMatch(hookSource, /Showing the last available weather snapshot/);
  assert.doesNotMatch(dashboardSource, /Weather lookup timed out after 5000ms/);
  assert.doesNotMatch(hookSource, /Weather lookup timed out after 5000ms/);
  assert.doesNotMatch(source, /'Seoul'/);
  assert.doesNotMatch(source, /new Date\(day\.date\)\.toLocaleDateString\('ko-KR'/);
  assert.doesNotMatch(dashboardSource, /'Seoul'/);
  assert.doesNotMatch(hookSource, /locationName.*'Seoul'/);
});

test('sales tab missing cattle fallback copy stays Korean', () => {
  const source = readSource('components/tabs/SalesTab.js');

  assert.match(source, /개체명 미등록/);
  assert.match(source, /이력번호 미등록/);
  assert.doesNotMatch(source, /Unknown/);
  assert.doesNotMatch(source, /000-0000-0000/);
});

test('sales tab normalizes numeric inputs before sales and profit aggregation', () => {
  const source = readSource('components/tabs/SalesTab.js');

  assert.match(source, /import \{ formatMoney, toFiniteNumber \} from '@\/lib\/utils';/);
  assert.match(source, /const salePrice = toFiniteNumber\(record\.price\);/);
  assert.match(source, /const purchaseCost = toFiniteNumber\(cow\.purchasePrice\);/);
  assert.match(source, /sum \+ toFiniteNumber\(expense\.amount\)/);
  assert.match(source, /price: salePrice,/);
  assert.match(source, /profit: hasExpenseData \? salePrice - totalCost : null,/);
  assert.match(source, /sum \+ toFiniteNumber\(record\.price\)/);
  assert.match(source, /sum \+ toFiniteNumber\(record\.profit\)/);
  assert.doesNotMatch(source, /const purchaseCost = cow\.purchasePrice \|\| 0;/);
  assert.doesNotMatch(source, /sum \+ expense\.amount/);
  assert.doesNotMatch(source, /profit: hasExpenseData \? record\.price - totalCost : null,/);
});

test('dashboard fallback average weight normalizes cattle weights', () => {
  const source = readSource('components/DashboardClient.js');

  assert.match(source, /import \{ formatMoney, toFiniteNumber \} from '@\/lib\/utils';/);
  assert.match(source, /sum \+ toFiniteNumber\(cow\.weight\)/);
  assert.doesNotMatch(source, /sum \+ \(cow\.weight \|\| 0\)/);
});

test('dashboard fallback monthly sales count filters by current year and valid sale dates', () => {
  const source = readSource('components/DashboardClient.js');

  assert.match(source, /function toValidCalendarDate\(value\) \{/);
  assert.match(source, /const dateKey = value\.trim\(\)\.slice\(0, 10\);/);
  assert.match(source, /strictDate\.toISOString\(\)\.slice\(0, 10\) !== dateKey/);
  assert.match(source, /const today = new Date\(\);/);
  assert.match(source, /const currentMonth = today\.getMonth\(\);/);
  assert.match(source, /const currentYear = today\.getFullYear\(\);/);
  assert.match(source, /const saleDate = toValidCalendarDate\(record\.saleDate\);/);
  assert.match(source, /saleDate\.getMonth\(\) === currentMonth/);
  assert.match(source, /saleDate\.getFullYear\(\) === currentYear/);
  assert.doesNotMatch(source, /const saleDate = new Date\(record\.saleDate\);/);
  assert.doesNotMatch(source, /return saleRecords\.filter\(\(record\) => new Date\(record\.saleDate\)\.getMonth\(\) === currentMonth\)\.length;/);
});

test('sales form fields expose explicit labels and invalid state', () => {
  const source = readSource('components/tabs/SalesTab.js');

  assert.match(source, /<PremiumLabel htmlFor="sale-date">출하일자<\/PremiumLabel>/);
  assert.match(source, /id="sale-date"[\s\S]*?aria-invalid=\{Boolean\(errors\.saleDate\)\}/);
  assert.match(source, /<PremiumLabel htmlFor="sale-price">판매 가격 \(원\)<\/PremiumLabel>/);
  assert.match(source, /id="sale-price"[\s\S]*?aria-invalid=\{Boolean\(errors\.price\)\}/);
  assert.match(source, /<PremiumLabel htmlFor="sale-cattle">출하 개체<\/PremiumLabel>/);
  assert.match(source, /id="sale-cattle"[\s\S]*?aria-invalid=\{Boolean\(errors\.cattleId\)\}/);
  assert.match(source, /<PremiumLabel htmlFor="sale-grade">등급<\/PremiumLabel>/);
  assert.match(source, /id="sale-grade"[\s\S]*?aria-invalid=\{Boolean\(errors\.grade\)\}/);
  assert.match(source, /<PremiumLabel htmlFor="sale-purchaser">구매처<\/PremiumLabel>/);
  assert.match(source, /id="sale-purchaser"[\s\S]*?aria-invalid=\{Boolean\(errors\.purchaser\)\}/);
});

test('sales form validation messages are announced by their controls', () => {
  const source = readSource('components/tabs/SalesTab.js');
  const fields = [
    ['saleDate', 'sale-date-error'],
    ['price', 'sale-price-error'],
    ['cattleId', 'sale-cattle-error'],
    ['grade', 'sale-grade-error'],
    ['purchaser', 'sale-purchaser-error'],
  ];

  for (const [errorPath, errorId] of fields) {
    assert.match(
      source,
      new RegExp(`aria-describedby=\\{errors\\.${errorPath} \\? "${errorId}" : undefined\\}`),
    );
    assert.match(source, new RegExp(`<div id="${errorId}" role="alert"`));
  }
});

test('sales form waits for async saves before re-enabling actions', () => {
  const source = readSource('components/tabs/SalesTab.js');

  assert.match(source, /const \[isSaving, setIsSaving\] = useState\(false\)/);
  assert.match(source, /const saveInFlightRef = useRef\(false\)/);
  assert.match(source, /if \(saveInFlightRef\.current \|\| isSaving\) \{\s+return;\s+\}/);
  assert.match(source, /if \(saveInFlightRef\.current\) \{\s+return;\s+\}/);
  assert.match(source, /saveInFlightRef\.current = true;/);
  assert.match(source, /setIsSaving\(true\);/);
  assert.match(source, /await onCreateSale\(values\)/);
  assert.match(source, /finally \{\s+saveInFlightRef\.current = false;\s+setIsSaving\(false\);/);
  assert.match(source, /onClick=\{toggleAddForm\}\s+disabled=\{isSaving\}/);
  assert.match(source, /disabled=\{!cattleList\?\.length \|\| isSaving\}\s+aria-busy=\{isSaving\}/);
});

test('inventory form fields expose explicit labels and invalid state', () => {
  const source = readSource('components/tabs/InventoryTab.js');

  assert.match(source, /<PremiumLabel htmlFor="inventory-name">자재명<\/PremiumLabel>/);
  assert.match(source, /id="inventory-name"[\s\S]*?aria-invalid=\{Boolean\(errors\.name\)\}/);
  assert.match(source, /<PremiumLabel htmlFor="inventory-category">분류<\/PremiumLabel>/);
  assert.match(source, /id="inventory-category"[\s\S]*?aria-invalid=\{Boolean\(errors\.category\)\}/);
  assert.match(source, /<PremiumLabel htmlFor="inventory-quantity">수량<\/PremiumLabel>/);
  assert.match(source, /id="inventory-quantity"[\s\S]*?aria-invalid=\{Boolean\(errors\.quantity\)\}/);
  assert.match(source, /<PremiumLabel htmlFor="inventory-unit">단위<\/PremiumLabel>/);
  assert.match(source, /id="inventory-unit"[\s\S]*?aria-invalid=\{Boolean\(errors\.unit\)\}/);
  assert.match(source, /<PremiumLabel htmlFor="inventory-threshold">경고 기준값<\/PremiumLabel>/);
  assert.match(source, /id="inventory-threshold"[\s\S]*?aria-invalid=\{Boolean\(errors\.threshold\)\}/);
});

test('inventory form validation messages are announced by their controls', () => {
  const source = readSource('components/tabs/InventoryTab.js');
  const fields = [
    ['name', 'inventory-name-error'],
    ['category', 'inventory-category-error'],
    ['quantity', 'inventory-quantity-error'],
    ['unit', 'inventory-unit-error'],
    ['threshold', 'inventory-threshold-error'],
  ];

  for (const [errorPath, errorId] of fields) {
    assert.match(
      source,
      new RegExp(`aria-describedby=\\{errors\\.${errorPath} \\? "${errorId}" : undefined\\}`),
    );
    assert.match(source, new RegExp(`<div id="${errorId}" role="alert"`));
  }
});

test('inventory form waits for async saves before re-enabling actions', () => {
  const source = readSource('components/tabs/InventoryTab.js');

  assert.match(source, /const \[isSaving, setIsSaving\] = useState\(false\)/);
  assert.match(source, /const saveInFlightRef = useRef\(false\)/);
  assert.match(source, /if \(saveInFlightRef\.current \|\| isSaving\) \{\s+return;\s+\}/);
  assert.match(source, /if \(saveInFlightRef\.current\) \{\s+return;\s+\}/);
  assert.match(source, /saveInFlightRef\.current = true;/);
  assert.match(source, /setIsSaving\(true\);/);
  assert.match(source, /await onAddItem\(values\)/);
  assert.match(source, /finally \{\s+saveInFlightRef\.current = false;\s+setIsSaving\(false\);/);
  assert.match(source, /onClick=\{toggleAddForm\}\s+disabled=\{isSaving\}/);
  assert.match(source, /type="submit" disabled=\{isSaving\} aria-busy=\{isSaving\}/);
});

test('inventory inline quantity editor exposes item-specific input label', () => {
  const source = readSource('components/tabs/InventoryTab.js');

  assert.match(source, /aria-label=\{`\$\{item\.name\} 재고 수량 입력`\}/);
  assert.match(source, /title=\{`\$\{item\.name\} 재고 수량 입력`\}/);
});

test('inventory inline quantity updates wait for async saves before re-enabling controls', () => {
  const source = readSource('components/tabs/InventoryTab.js');

  assert.match(source, /const PLAIN_NONNEGATIVE_NUMBER_INPUT_PATTERN = \/\^\(\?:\\d\+\|\\d\+\\\.\\d\+\|\\\.\\d\+\)\$\/;/);
  assert.match(source, /function parseInlineQuantityInput\(value\)/);
  assert.match(source, /const parsedQuantity = parseInlineQuantityInput\(editQty\);/);
  assert.match(source, /if \(!Number\.isFinite\(parsedQuantity\)\) \{/);
  assert.match(source, /const \[savingQuantityId, setSavingQuantityId\] = useState\(null\)/);
  assert.match(source, /const quantityInFlightRef = useRef\(false\)/);
  assert.match(source, /if \(quantityInFlightRef\.current \|\| savingQuantityId\) \{\s+return;\s+\}/);
  assert.match(source, /quantityInFlightRef\.current = true;/);
  assert.match(source, /setSavingQuantityId\(id\);/);
  assert.match(source, /await onUpdateQuantity\(id, parsedQuantity\);/);
  assert.match(source, /finally \{\s+quantityInFlightRef\.current = false;\s+setSavingQuantityId\(null\);/);
  assert.match(source, /disabled=\{savingQuantityId === item\.id\}/);
  assert.match(source, /aria-busy=\{savingQuantityId === item\.id\}/);
  assert.doesNotMatch(source, /Number\(editQty\) < 0/);
});

test('dashboard API fallback messages stay operator-facing Korean', () => {
  const cattleRoute = readSource('app/api/dashboard/cattle/route.js');
  const salesRoute = readSource('app/api/dashboard/sales/route.js');
  const summaryRoute = readSource('app/api/dashboard/summary/route.js');
  const listQueries = readSource('lib/dashboard/list-queries.js');

  assert.match(cattleRoute, /개체 목록을 불러오지 못했습니다/);
  assert.match(cattleRoute, /개체 목록 조회 조건을 확인해 주세요/);
  assert.match(salesRoute, /판매 기록을 불러오지 못했습니다/);
  assert.match(salesRoute, /판매 기록 조회 조건을 확인해 주세요/);
  assert.match(summaryRoute, /대시보드 요약을 불러오지 못했습니다/);
  assert.match(listQueries, /목록 개수는 1 이상 숫자로 입력해 주세요/);
  assert.match(cattleRoute, /AUTHENTICATION_REQUIRED_MESSAGE/);
  assert.match(salesRoute, /AUTHENTICATION_REQUIRED_MESSAGE/);
  assert.match(summaryRoute, /AUTHENTICATION_REQUIRED_MESSAGE/);
  assert.match(listQueries, /const normalized = String\(value\)\.trim\(\);/);
  assert.match(listQueries, /Number\.parseInt\(normalized, 10\)/);
  assert.match(listQueries, /목록 위치 정보가 올바르지 않습니다/);
  assert.match(listQueries, /시작일은 종료일보다 늦을 수 없습니다/);
  assert.match(listQueries, /\/\^\\d\{4\}-\\d\{2\}-\\d\{2\}\$\/\.test/);
  assert.match(listQueries, /toDateKey\(parsed\) !== normalized/);
  assert.doesNotMatch(listQueries, /Number\.parseInt\(String\(value\), 10\)/);
  assert.doesNotMatch(cattleRoute, /message: error\.message \|\|/);
  assert.doesNotMatch(salesRoute, /message: error\.message \|\|/);
  assert.doesNotMatch(summaryRoute, /message: error\.message \|\|/);
  assert.doesNotMatch(cattleRoute, /message: error\.message/);
  assert.doesNotMatch(salesRoute, /message: error\.message/);
  assert.doesNotMatch(cattleRoute, /message: error\.message \}, \{ status: 401/);
  assert.doesNotMatch(salesRoute, /message: error\.message \}, \{ status: 401/);
  assert.doesNotMatch(summaryRoute, /message: error\.message \}, \{ status: 401/);
  assert.doesNotMatch(cattleRoute, /Failed to load cattle list/);
  assert.doesNotMatch(salesRoute, /Failed to load sales list/);
  assert.doesNotMatch(summaryRoute, /Failed to load dashboard summary/);
  assert.doesNotMatch(listQueries, /must be a positive integer|cursor.*malformed|valid YYYY-MM-DD|before or equal/);
});
