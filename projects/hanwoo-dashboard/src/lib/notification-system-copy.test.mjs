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
	assert.match(source, /function normalizeNotificationWidgetOptions\(options\) \{/);
	assert.match(
		source,
		/options && typeof options === "object" && !Array\.isArray\(options\)/,
	);
	assert.match(source, /export default function NotificationWidget\(options = \{\}\) \{/);
	assert.match(
		source,
		/const \{ notifications = \[\] \} = normalizeNotificationWidgetOptions\(options\);/,
	);
	assert.match(source, /if \(!Array\.isArray\(notifications\)\) return \[\]/);
	assert.match(
		source,
		/\.filter\([\s\S]*?note\s*&&\s*typeof\s+note\s*===\s*["']object["']\s*&&\s*!Array\.isArray\(note\)[\s\S]*?\)/,
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
	assert.doesNotMatch(
		source,
		/export default function NotificationWidget\(\{ notifications = \[\] \}\)/,
	);
});

test("notification systems normalize malformed initial payloads before rendering", () => {
	const source = readSource("components/layout/NotificationSystem.js");

	assert.match(
		source,
		/function normalizeSystemNotifications\(initialNotifications\)/,
	);
	assert.match(
		source,
		/function normalizeNotificationSystemOptions\(options\) \{/,
	);
	assert.match(
		source,
		/options && typeof options === "object" && !Array\.isArray\(options\)/,
	);
	assert.match(source, /export function NotificationSystem\(options = \{\}\) \{/);
	assert.match(
		source,
		/const \{ initialNotifications = \[\] \} =\s+normalizeNotificationSystemOptions\(options\);/,
	);
	assert.match(
		source,
		/if \(!Array\.isArray\(initialNotifications\)\) return \[\]/,
	);
	assert.match(
		source,
		/\.filter\([\s\S]*?\(?notification\)?\s*=>[\s\S]*?notification\s*&&[\s\S]*?typeof\s+notification\s*===\s*["']object["'][\s\S]*?!Array\.isArray\(notification\)[\s\S]*?\)/,
	);
	assert.match(
		source,
		/useState\(\s*\(\s*\)\s*=>\s*normalizeSystemNotifications\(\s*initialNotifications\s*\),?\s*\)/,
	);
	assert.match(source, /DEFAULT_NOTIFICATION_TITLE/);
	assert.match(source, /DEFAULT_NOTIFICATION_MESSAGE/);
	assert.match(source, /const DEFAULT_NOTIFICATION_TITLE = ["']운영 알림["'];/);
	assert.doesNotMatch(source, /알림 제목 없음/);
	assert.match(
		source,
		/id: notification\.id \?\? `notification-\$\{index \+ 1\}`/,
	);
	assert.match(
		source,
		/setNotifications\(\s*\(\s*currentNotifications\s*\)\s*=>\s*currentNotifications\.map/,
	);
	assert.doesNotMatch(source, /useState\(initialNotifications\)/);
	assert.doesNotMatch(
		source,
		/export function NotificationSystem\(\{ initialNotifications = \[\] \} = \{\}\)/,
	);
	assert.doesNotMatch(source, /setNotifications\(notifications\.map/);
});

test("notification builder normalizes malformed cattle payloads before alert generation", () => {
	const source = readSource("lib/notifications.js");

	assert.match(source, /function isNotificationCattleRow\(row\) \{/);
	assert.match(
		source,
		/row && typeof row === ["']object["'] && !Array\.isArray\(row\)/,
	);
	assert.match(source, /function normalizeNotificationCattle\(cattle\) \{/);
	assert.match(
		source,
		/return Array\.isArray\(cattle\) \? cattle\.filter\(isNotificationCattleRow\) : \[\];/,
	);
	assert.match(
		source,
		/const safeCattle = normalizeNotificationCattle\(cattle\);/,
	);
	assert.match(source, /safeCattle\.forEach\(\(cow\) => \{/);
	assert.doesNotMatch(source, /cattle\.forEach\(\(cow\) => \{/);
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
		/export function DropdownMenuItem\(options = \{\}\)/,
	);
	assert.match(dropdownSource, /function normalizeDropdownMenuOptions\(options\) \{/);
	assert.match(
		dropdownSource,
		/options && typeof options === ["']object["'] && !Array\.isArray\(options\)/,
	);
	assert.match(
		dropdownSource,
		/const \{ children, onClick, className = ["']["'], \.\.\.props \} =\s+normalizeDropdownMenuOptions\(options\);/,
	);
	assert.match(
		dropdownSource,
		/const handleClick = typeof onClick === ["']function["'] \? onClick : null;/,
	);
	assert.match(dropdownSource, /onClick=\{handleClick\}/);
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

	assert.match(source, /const Element = handleClick \? ["']button["'] : ["']div["']/);
	assert.match(source, /type=\{handleClick \? ["']button["'] : undefined\}/);
	assert.match(source, /if \(!React\.isValidElement\(children\)\) \{\s+return null;\s+\}/);
	assert.match(source, /focus:ring-2/);
	assert.doesNotMatch(source, /<div\s+[^>]*onClick=\{onClick\}/);
});
