import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

const source = readFileSync(
	new URL("../components/ui/premium-button.js", import.meta.url),
	"utf8",
);

test("PremiumButton defaults to non-submit button semantics", () => {
	assert.match(source, /function normalizePremiumButtonOptions\(options\) \{/);
	assert.match(
		source,
		/return options && typeof options === "object" && !Array\.isArray\(options\)\s+\? options\s+:\s+\{\};/,
	);
	assert.match(
		source,
		/const PremiumButton = React\.forwardRef\(\(options, ref\) => \{/,
	);
	assert.match(
		source,
		/const \{ className, variant, size, asChild = false, type = "button", \.\.\.props \} =\s+normalizePremiumButtonOptions\(options\);/,
	);
	assert.match(source, /type = "button"/);
	assert.match(source, /type=\{asChild \? undefined : type\}/);
});

test("PremiumButton still allows explicit submit buttons", () => {
	assert.doesNotMatch(source, /type=\{?"button"?\}\s*\{\.\.\.props\}/);
	assert.match(source, /\{\.\.\.props\}/);
});
