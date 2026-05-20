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
  assert.match(source, /console\.error\('Failed to add cattle:', error\);/);
  assert.match(source, /console\.error\('Failed to update cattle:', error\);/);
  assert.doesNotMatch(source, /showError\(errorTitle, error\.message\)/);
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

  assert.match(source, /한우 시세를 불러오는 중입니다/);
  assert.match(source, /지금은 한우 시세 데이터를 확인할 수 없습니다/);
  assert.match(source, /시세 흐름/);
  assert.match(source, /한우 도매 시세/);
  assert.match(source, /가중평균 거래가/);
  assert.match(source, /실시간 KAPE/);
  assert.match(source, /저장된 KAPE/);
  assert.match(source, /이전 저장가/);
  assert.match(source, /수소 \/ kg/);
  assert.match(source, /암소 \/ kg/);
  assert.match(source, /갱신/);
  assert.match(source, /출처: KAPE/);
  assert.match(source, /aria-label=\{loading \? '시세 갱신 중' : '한우 시세 새로고침'\}/);
  assert.match(source, /title=\{loading \? '시세 갱신 중' : '한우 시세 새로고침'\}/);
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

test('weather widget uses Korean product copy for unavailable state', () => {
  const source = readSource('components/widgets/widgets.js');
  const dashboardSource = readSource('components/DashboardClient.js');
  const hookSource = readSource('lib/hooks/useWeather.js');

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
  assert.match(source, /<div aria-label=\{getWeatherDesc\(day\.weatherCode\)\} style=\{\{fontSize:"24px",marginBottom:"4px"\}\}>\{getWeatherIcon\(day\.weatherCode\)\}<\/div>/);
  assert.match(source, /<span aria-hidden="true">🌧<\/span> 강수 \{day\.precipProb\}%/);
  assert.match(source, /<span aria-hidden="true">🐄<\/span> 가축 기상 경고/);
  assert.match(source, /<span aria-hidden="true">\{a\.icon\}<\/span> \{a\.msg\}/);
  assert.match(dashboardSource, /WEATHER_STALE_MESSAGE/);
  assert.match(hookSource, /WEATHER_STALE_MESSAGE/);
  assert.doesNotMatch(dashboardSource, /Showing the last available weather snapshot/);
  assert.doesNotMatch(hookSource, /Showing the last available weather snapshot/);
  assert.doesNotMatch(source, /'Seoul'/);
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

test('dashboard API fallback messages stay operator-facing Korean', () => {
  const cattleRoute = readSource('app/api/dashboard/cattle/route.js');
  const salesRoute = readSource('app/api/dashboard/sales/route.js');
  const summaryRoute = readSource('app/api/dashboard/summary/route.js');
  const listQueries = readSource('lib/dashboard/list-queries.js');

  assert.match(cattleRoute, /개체 목록을 불러오지 못했습니다/);
  assert.match(salesRoute, /판매 기록을 불러오지 못했습니다/);
  assert.match(summaryRoute, /대시보드 요약을 불러오지 못했습니다/);
  assert.match(listQueries, /목록 개수는 1 이상 숫자로 입력해 주세요/);
  assert.match(listQueries, /목록 위치 정보가 올바르지 않습니다/);
  assert.match(listQueries, /시작일은 종료일보다 늦을 수 없습니다/);
  assert.doesNotMatch(cattleRoute, /message: error\.message \|\|/);
  assert.doesNotMatch(salesRoute, /message: error\.message \|\|/);
  assert.doesNotMatch(summaryRoute, /message: error\.message \|\|/);
  assert.doesNotMatch(cattleRoute, /Failed to load cattle list/);
  assert.doesNotMatch(salesRoute, /Failed to load sales list/);
  assert.doesNotMatch(summaryRoute, /Failed to load dashboard summary/);
  assert.doesNotMatch(listQueries, /must be a positive integer|cursor.*malformed|valid YYYY-MM-DD|before or equal/);
});
