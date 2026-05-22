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

test("notification modal close button has Korean accessible copy", () => {
	const source = readSource("components/ui/NotificationModal.js");

	assert.match(source, /aria-label="닫기"/);
	assert.match(source, /title="닫기"/);
	assert.match(
		source,
		/<button\s+type="button"\s+onClick=\{onClose\}\s+disabled=\{isTestingSMS\}\s+aria-busy=\{isTestingSMS\}/,
	);
	assert.doesNotMatch(source, /aria-label="Close"/);
	assert.doesNotMatch(source, /title="Close"/);
});

test("notification modal exposes dialog semantics with a visible title label", () => {
	const source = readSource("components/ui/NotificationModal.js");

	assert.match(source, /role="dialog"/);
	assert.match(source, /aria-modal="true"/);
	assert.match(source, /aria-labelledby="notification-modal-title"/);
	assert.match(source, /id="notification-modal-title"/);
	assert.match(source, /알림 센터/);
});

test("notification modal can be dismissed with Escape from the dialog surface", () => {
	const source = readSource("components/ui/NotificationModal.js");

	assert.match(
		source,
		/import \{ useEffect, useRef, useState \} from 'react';/,
	);
	assert.match(source, /const dialogRef = useRef\(null\);/);
	assert.match(source, /useEffect\(\(\) => \{/);
	assert.match(source, /dialogRef\.current\?\.focus\(\);/);
	assert.match(source, /ref=\{dialogRef\}/);
	assert.match(source, /const handleDialogKeyDown = \(event\) => \{/);
	assert.match(source, /event\.key === 'Escape'/);
	assert.match(source, /event\.stopPropagation\(\);/);
	assert.match(source, /if \(isTestingSMS\) \{\s+return;\s+\}\s+onClose\(\);/);
	assert.match(source, /onKeyDown=\{handleDialogKeyDown\}/);
	assert.match(source, /tabIndex=\{-1\}/);
});

test("notification modal decorative status icons are hidden from assistive tech", () => {
	const source = readSource("components/ui/NotificationModal.js");

	assert.match(source, /className="animate-bounce" aria-hidden="true"/);
	assert.match(source, /<div aria-hidden="true" style=\{\{ fontSize: '40px'/);
	assert.match(source, /className="animate-pulse" aria-hidden="true"/);
});

test("notification modal SMS action uses safe button semantics and Korean copy", () => {
	const source = readSource("components/ui/NotificationModal.js");
	const dashboardSource = readSource("components/DashboardClient.js");

	assert.match(
		source,
		/<button\s+type="button"\s+onClick=\{handleTestSMSClick\}/,
	);
	assert.match(
		source,
		/<span aria-hidden="true">📱<\/span>[\s\S]*?문자 알림 서비스/,
	);
	assert.match(source, /중요한 알림을 문자로 받아보시겠습니까\?/);
	assert.match(source, /테스트 전송/);
	assert.match(
		source,
		/문자 알림 연동이 필요하며 발송 비용이 발생할 수 있습니다\./,
	);
	assert.match(dashboardSource, /테스트 문자를 발송했습니다/);
	assert.match(dashboardSource, /등록된 연락처로 전송되었습니다/);
	assert.doesNotMatch(source, /Twilio \/ Kakao API/);
	assert.doesNotMatch(source, /SMS 알림 서비스/);
	assert.doesNotMatch(dashboardSource, /테스트 SMS를 발송했습니다/);
});

test("notification modal SMS test action waits for async sends before re-enabling", () => {
	const source = readSource("components/ui/NotificationModal.js");

	assert.match(
		source,
		/const \[isTestingSMS, setIsTestingSMS\] = useState\(false\)/,
	);
	assert.match(source, /const handleTestSMSClick = async \(\) => \{/);
	assert.match(source, /if \(isTestingSMS\) \{\s+return;\s+\}/);
	assert.match(source, /setIsTestingSMS\(true\);/);
	assert.match(source, /await Promise\.resolve\(onTestSMS\?\.\(\)\);/);
	assert.match(source, /finally \{\s+setIsTestingSMS\(false\);/);
	assert.match(source, /disabled=\{isTestingSMS\}/);
	assert.match(source, /aria-busy=\{isTestingSMS\}/);
	assert.match(
		source,
		/onClick=\{\(\) => \{\s+if \(!isTestingSMS\) \{\s+onClose\(\);\s+\}\s+\}\}/,
	);
	assert.match(source, /cursor: isTestingSMS \? 'wait' : 'pointer'/);
});

test("notification modal normalizes malformed notification payloads before rendering", () => {
	const source = readSource("components/ui/NotificationModal.js");

	assert.match(
		source,
		/function normalizeModalNotifications\(notifications\) \{/,
	);
	assert.match(source, /return Array\.isArray\(notifications\)/);
	assert.match(
		source,
		/\.filter\(\(notification\) => notification && typeof notification === 'object'\)/,
	);
	assert.match(
		source,
		/const visibleNotifications = normalizeModalNotifications\(notifications\);/,
	);
	assert.match(source, /visibleNotifications\.length === 0/);
	assert.match(
		source,
		/visibleNotifications\.map\(\(notification, index\) => \(/,
	);
	assert.doesNotMatch(source, /notifications\.length === 0/);
	assert.doesNotMatch(
		source,
		/notifications\.map\(\(notification, index\) => \(/,
	);
});

test("notification modal visible copy is readable Korean product copy", () => {
	const source = readSource("components/ui/NotificationModal.js");
	const dashboardSource = readSource("components/DashboardClient.js");

	for (const copy of [
		"알림 센터",
		"새로운 알림이 없습니다.",
		"문자 알림 서비스",
		"중요한 알림을 문자로 받아보시겠습니까?",
		"테스트 전송",
		"문자 알림 연동이 필요하며 발송 비용이 발생할 수 있습니다.",
	]) {
		assert.equal(source.includes(copy), true);
	}

	assert.equal(dashboardSource.includes("테스트 문자를 발송했습니다."), true);
	assert.equal(
		dashboardSource.includes(
			"Joolife 알림 예시가 등록된 연락처로 전송되었습니다.",
		),
		true,
	);

	for (const broken of ["?뚮┝", "臾몄옄", "諛쒖넚", "?꾩넚", "?リ린"]) {
		assert.equal(source.includes(broken), false);
		assert.equal(dashboardSource.includes(broken), false);
	}
});
