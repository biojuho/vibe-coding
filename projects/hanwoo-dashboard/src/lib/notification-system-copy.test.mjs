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

test("notification system trigger exposes a Korean accessible label", () => {
	const source = readSource("components/layout/NotificationSystem.js");

	assert.match(source, /const notificationLabel =\s*unreadCount > 0/);
	assert.match(source, /알림 열기, 읽지 않은 알림/);
	assert.match(source, /: ["']알림 열기["']/);
	assert.match(source, /aria-label=\{notificationLabel\}/);
	assert.match(source, /title=\{notificationLabel\}/);
	assert.match(source, /aria-hidden="true"/);
	assert.doesNotMatch(source, /aria-label="Notifications"/);
	assert.doesNotMatch(source, /title="Notifications"/);
	assert.match(source, /BellIcon className="h-5 w-5" aria-hidden="true"/);
});

test("notification widget visible heading uses Korean product copy", () => {
	const source = readSource("components/widgets/NotificationWidget.js");

	assert.ok(source.includes("우선 확인 알림"));
	assert.doesNotMatch(source, /Priority Alerts/);
});

test("notification widget normalizes malformed payloads before rendering", () => {
	const source = readSource("components/widgets/NotificationWidget.js");

	assert.match(source, /function normalizeNotifications\(notifications\)/);
	assert.match(source, /if \(!Array\.isArray\(notifications\)\) return \[\]/);
	assert.match(
		source,
		/\.filter\(\s*\(?note\)?\s*=>\s*note\s*&&\s*typeof\s+note\s*===\s*["']object["']\s*\)/,
	);
	assert.match(
		source,
		/const visibleNotifications = normalizeNotifications\(notifications\)/,
	);
	assert.match(source, /\{visibleNotifications\.length\}/);
	assert.match(source, /\{visibleNotifications\.map\(\(note\) => \{/);
	assert.match(source, /DEFAULT_NOTIFICATION_TITLE/);
	assert.match(source, /DEFAULT_NOTIFICATION_MESSAGE/);
	assert.doesNotMatch(source, /notifications\.length/);
	assert.doesNotMatch(source, /notifications\.map/);
});

test("notification systems normalize malformed initial payloads before rendering", () => {
	const source = readSource("components/layout/NotificationSystem.js");

	assert.match(
		source,
		/function normalizeSystemNotifications\(initialNotifications\)/,
	);
	assert.match(
		source,
		/if \(!Array\.isArray\(initialNotifications\)\) return \[\]/,
	);
	assert.match(
		source,
		/\.filter\(\s*\(?notification\)?\s*=>\s*notification\s*&&\s*typeof\s+notification\s*===\s*["']object["']\s*\)/,
	);
	assert.match(
		source,
		/useState\(\s*\(\s*\)\s*=>\s*normalizeSystemNotifications\(\s*initialNotifications\s*\),?\s*\)/,
	);
	assert.match(source, /DEFAULT_NOTIFICATION_TITLE/);
	assert.match(source, /DEFAULT_NOTIFICATION_MESSAGE/);
	assert.match(
		source,
		/id: notification\.id \?\? `notification-\$\{index \+ 1\}`/,
	);
	assert.match(
		source,
		/setNotifications\(\s*\(\s*currentNotifications\s*\)\s*=>\s*currentNotifications\.map/,
	);
	assert.doesNotMatch(source, /useState\(initialNotifications\)/);
	assert.doesNotMatch(source, /setNotifications\(notifications\.map/);
});

test("notification systems only show unread badges when there are unread items", () => {
	const source = readSource("components/layout/NotificationSystem.js");

	assert.match(source, /\{unreadCount > 0 && \(/);
	assert.match(source, /aria-hidden="true"/);
});

test("notification mark-all actions use safe button semantics and Korean copy", () => {
	const source = readSource("components/layout/NotificationSystem.js");

	assert.match(
		source,
		/const markAllAsReadLabel = `읽지 않은 알림 \$\{unreadCount\}개 모두 읽음으로 표시`;/,
	);
	assert.match(
		source,
		/<button\s+type="button"\s+onClick=\{markAllAsRead\}\s+aria-label=\{markAllAsReadLabel\}\s+title=\{markAllAsReadLabel\}/,
	);
	assert.match(source, /모두 읽음/);
});

test("notification dropdown items identify the read action", () => {
	const source = readSource("components/layout/NotificationSystem.js");
	const dropdownSource = readSource("components/ui/dropdown-menu.js");

	assert.match(source, /onClick=\{\(\) => markAsRead\(notification\.id\)\}/);
	assert.match(
		source,
		/aria-label=\{`\$\{notification\.title\} 알림 읽음으로 표시`\}/,
	);
	assert.match(
		source,
		/title=\{`\$\{notification\.title\} 알림 읽음으로 표시`\}/,
	);
	assert.match(
		dropdownSource,
		/export function DropdownMenuItem\(\{ children, onClick, className, \.\.\.props \}\)/,
	);
	assert.match(dropdownSource, /\{\.\.\.props\}/);
});

test("notification system does not seed demo farm alerts by default", () => {
	const source = readSource("components/layout/NotificationSystem.js");

	assert.match(source, /initialNotifications = \[\]/);
	assert.match(source, /새로운 알림이 없습니다\./);
	assert.doesNotMatch(source, /useState\(\[/);
	assert.doesNotMatch(source, /NOTIFICATIONS = \[/);
	assert.equal(source.includes("우사 #"), false);
	assert.equal(source.includes("재고가 10% 미만입니다"), false);
});

test("clickable dropdown menu items use native button semantics", () => {
	const source = readSource("components/ui/dropdown-menu.js");

	assert.match(source, /const Element = onClick \? ["']button["'] : ["']div["']/);
	assert.match(source, /type=\{onClick \? ["']button["'] : undefined\}/);
	assert.match(source, /focus:ring-2/);
	assert.doesNotMatch(source, /<div\s+[^>]*onClick=\{onClick\}/);
});
