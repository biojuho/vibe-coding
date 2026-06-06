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

test("feedback toasts expose live-region semantics and Korean dismiss labels", () => {
	const source = readSource("components/feedback/FeedbackProvider.js");

	assert.match(
		source,
		/function normalizeFeedbackProviderOptions\(options\) \{/,
	);
	assert.match(
		source,
		/function normalizeToastOptions\(options\) \{/,
	);
	assert.match(source, /export function FeedbackProvider\(options = \{\}\)/);
	assert.match(
		source,
		/const \{ children \} = normalizeFeedbackProviderOptions\(options\);/,
	);
	assert.match(source, /const mountedRef = useRef\(true\);/);
	assert.match(
		source,
		/const isUrgent\s*=\s*toast\s*\.\s*variant\s*===\s*["']error["']\s*\|\|\s*toast\s*\.\s*variant\s*===\s*["']warning["']/,
	);
	assert.match(source, /role=\{isUrgent \? ["']alert["'] : ["']status["']\}/);
	assert.match(source, /aria-live=\{isUrgent \? ["']assertive["'] : ["']polite["']\}/);
	assert.match(source, /aria-atomic="true"/);
	assert.match(source, /const toastDismissLabel = `\$\{toast\.title\} 알림 닫기`;/);
	assert.match(source, /aria-label=\{toastDismissLabel\}/);
	assert.match(source, /title=\{toastDismissLabel\}/);
	assert.match(
		source,
		/try \{\s+window\.clearTimeout\(timeoutId\);\s+\} catch \{\}/,
	);
	assert.match(
		source,
		/try \{\s+const timeoutId = window\.setTimeout\(\(\) => \{/,
	);
	assert.match(
		source,
		/window\.setTimeout\(\(\) => \{\s+timeoutIdsRef\.current\.delete\(id\);\s+if \(mountedRef\.current\) \{\s+dismiss\(id\);/,
	);
	assert.match(source, /const \{\s+title,\s+description = "",\s+variant = "info",\s+duration = 3600,\s+\} = normalizeToastOptions\(options\);/);
	assert.match(source, /fixed inset-x-0 bottom-4 z-\[360\]/);
	assert.doesNotMatch(source, /z-\[70\]/);
	assert.doesNotMatch(source, /export function FeedbackProvider\(\{ children \}\)/);
	assert.doesNotMatch(
		source,
		/\(\{ title, description = "", variant = "info", duration = 3600 \}\) => \{/,
	);
	assert.match(
		source,
		/console\.error\(["']Failed to schedule feedback toast dismissal:/,
	);
	assert.match(
		source,
		/timeoutIds\.forEach\(\(timeoutId\) => \{\s+try \{\s+window\.clearTimeout\(timeoutId\);/,
	);
	assert.match(source, /aria-hidden="true"/);
	assert.doesNotMatch(source, /aria-label="Close"/);
});

test("feedback provider ignores stale unmounted callbacks", () => {
	const source = readSource("components/feedback/FeedbackProvider.js");

	assert.match(source, /const mountedRef = useRef\(true\);/);
	assert.match(
		source,
		/if \(mountedRef\.current\) \{\s+setToasts\(\(current\) => current\.filter\(\(toast\) => toast\.id !== id\)\);/,
	);
	assert.match(
		source,
		/if \(!mountedRef\.current\) \{\s+return;\s+\}\s+const \{\s+title,\s+description = "",\s+variant = "info",\s+duration = 3600,\s+\} = normalizeToastOptions\(options\);\s+const id = `toast_/,
	);
	assert.match(
		source,
		/useEffect\(\(\) => \{\s+mountedRef\.current = true;[\s\S]*?return \(\) => \{\s+mountedRef\.current = false;/,
	);
	assert.match(
		source,
		/if \(resolverRef\.current\) \{\s+resolverRef\.current\(false\);\s+resolverRef\.current = null;/,
	);
	assert.match(
		source,
		/if \(!mountedRef\.current\) \{\s+return Promise\.resolve\(false\);\s+\}\s+setConfirmation\(\{/,
	);
	assert.match(
		source,
		/if \(mountedRef\.current\) \{\s+setConfirmation\(DEFAULT_CONFIRMATION\);/,
	);
	assert.doesNotMatch(
		source,
		/setToasts\(\(current\) => current\.filter\(\(toast\) => toast\.id !== id\)\);\s+\}, \[\]\);/,
	);
	assert.doesNotMatch(
		source,
		/setConfirmation\(DEFAULT_CONFIRMATION\);\s+\}, \[\]\);/,
	);
});

test("shared Button defaults to safe non-submit semantics", () => {
	const source = readSource("components/ui/button.js");

	assert.match(source, /function normalizeButtonOptions\(options\) \{/);
	assert.match(
		source,
		/return options && typeof options === "object" && !Array\.isArray\(options\)\s+\? options\s+:\s+\{\};/,
	);
	assert.match(source, /const Button = React\.forwardRef\(\(options, ref\) => \{/);
	assert.match(
		source,
		/const \{ className, variant, size, asChild = false, type, \.\.\.props \} =\s+normalizeButtonOptions\(options\);/,
	);
	assert.match(
		source,
		/type=\{asChild \? undefined : \(type \?\? "button"\)\}/,
	);
});

test("feedback confirmation dialog actions expose stable Korean labels", () => {
	const source = readSource("components/feedback/FeedbackProvider.js");

	assert.match(
		source,
		/const cancelButtonLabel\s*=\s*`\$\{confirmation\.cancelLabel\}하고 확인 창 닫기`/,
	);
	assert.match(
		source,
		/const confirmButtonLabel\s*=\s*`\$\{confirmation\.confirmLabel\} 실행`/,
	);
	assert.match(
		source,
		/<Button[\s\S]*?variant="outline"[\s\S]*?aria-label=\{cancelButtonLabel\}[\s\S]*?title=\{cancelButtonLabel\}[\s\S]*?>/,
	);
	assert.match(
		source,
		/<Button[\s\S]*?onClick=\{\(\) => closeConfirmation\(true\)\}[\s\S]*?aria-label=\{confirmButtonLabel\}[\s\S]*?title=\{confirmButtonLabel\}[\s\S]*?>/,
	);
});
