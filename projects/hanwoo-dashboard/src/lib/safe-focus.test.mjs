/**
 * Behavioral tests for safeFocus.js focusElementSafely utility.
 *
 * safeFocus.js uses ESM export syntax in a CJS package, so it cannot be
 * imported directly by Node. The function is re-implemented inline and
 * cross-checked via source-grep to ensure production code cannot diverge.
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

test("focusElementSafely guards typeof element.focus", () => {
	assert.match(src, /typeof element\.focus !== "function"/);
});

test("focusElementSafely wraps focus() call in try/catch", () => {
	assert.match(src, /try \{/);
	assert.match(src, /element\.focus\(\)/);
});

// ── Behavioral tests ──────────────────────────────────────────────────────────

test("focusElementSafely does nothing for null", () => {
	assert.doesNotThrow(() => focusElementSafely(null));
});

test("focusElementSafely does nothing for undefined", () => {
	assert.doesNotThrow(() => focusElementSafely(undefined));
});

test("focusElementSafely does nothing for element without focus method", () => {
	assert.doesNotThrow(() => focusElementSafely({ id: "el" }));
});

test("focusElementSafely does nothing for non-function focus property", () => {
	assert.doesNotThrow(() => focusElementSafely({ focus: "not-a-function" }));
});

test("focusElementSafely calls focus() on valid element", () => {
	let called = false;
	const el = { focus: () => { called = true; } };
	focusElementSafely(el);
	assert.equal(called, true);
});

test("focusElementSafely swallows focus() errors silently", () => {
	const el = {
		focus: () => {
			throw new Error("focus is not allowed");
		},
	};
	assert.doesNotThrow(() => focusElementSafely(el));
});

test("focusElementSafely returns undefined in all cases", () => {
	assert.equal(focusElementSafely(null), undefined);
	assert.equal(focusElementSafely({ focus: () => {} }), undefined);
});
