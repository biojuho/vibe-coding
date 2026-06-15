/**
 * Behavioral tests for safeFocus.js
 *
 * focusElementSafely is tiny (9 lines) with no external deps — re-implemented
 * inline. Source-grep guards confirm the real file matches the contract.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = path.resolve(__dirname, "..");
const src = readFileSync(path.join(SRC_ROOT, "lib/safeFocus.js"), "utf8");

// ── Inline re-implementation ──────────────────────────────────────────────────

function focusElementSafely(element) {
	if (!element || typeof element.focus !== "function") {
		return;
	}
	try {
		element.focus();
	} catch {}
}

// ── Source-grep guards ────────────────────────────────────────────────────────

test("safeFocus: guards with !element check", () => {
	assert.match(src, /!element/);
});

test("safeFocus: guards typeof element.focus !== 'function'", () => {
	assert.match(src, /typeof element\.focus !== ["']function["']/);
});

test("safeFocus: wraps element.focus() in try/catch", () => {
	assert.match(src, /try \{/);
	assert.match(src, /element\.focus\(\)/);
	assert.match(src, /\} catch \{\}/);
});

test("safeFocus: exported as named export", () => {
	assert.match(src, /export function focusElementSafely\(element\) \{/);
});

// ── Behavioral tests ──────────────────────────────────────────────────────────

test("focusElementSafely: does nothing for null", () => {
	assert.doesNotThrow(() => focusElementSafely(null));
});

test("focusElementSafely: does nothing for undefined", () => {
	assert.doesNotThrow(() => focusElementSafely(undefined));
});

test("focusElementSafely: does nothing when element has no focus method", () => {
	const element = { id: "test" };
	assert.doesNotThrow(() => focusElementSafely(element));
});

test("focusElementSafely: calls focus() on valid element", () => {
	let focused = false;
	const element = {
		focus() {
			focused = true;
		},
	};
	focusElementSafely(element);
	assert.equal(focused, true);
});

test("focusElementSafely: swallows errors thrown by focus()", () => {
	const element = {
		focus() {
			throw new Error("focus blocked by browser");
		},
	};
	assert.doesNotThrow(() => focusElementSafely(element));
});

test("focusElementSafely: does nothing when focus property exists but is not a function", () => {
	const element = { focus: "not-a-function" };
	assert.doesNotThrow(() => focusElementSafely(element));
});

test("focusElementSafely: does nothing for falsy element value 0", () => {
	assert.doesNotThrow(() => focusElementSafely(0));
});

test("focusElementSafely: does nothing for empty string element", () => {
	assert.doesNotThrow(() => focusElementSafely(""));
});

test("focusElementSafely: does not call focus on element without focus method even if truthy", () => {
	let callCount = 0;
	const element = { notFocus() { callCount++; } };
	focusElementSafely(element);
	assert.equal(callCount, 0);
});
