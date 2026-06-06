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
		/const \{\s+className,\s+variant,\s+size,\s+asChild = false,\s+type = "button",\s+glow: _glow,\s+\.\.\.props\s+\} = normalizePremiumButtonOptions\(options\);/,
	);
	assert.match(source, /type = "button"/);
	assert.match(source, /type=\{asChild \? undefined : type\}/);
});

test("PremiumButton consumes visual-only glow without leaking it to the DOM", () => {
	assert.match(source, /glow: _glow,\s+\.\.\.props/);
	assert.doesNotMatch(source, /\{\.\.\.props\}[\s\S]*?glow=/);
});

test("PremiumButton still allows explicit submit buttons", () => {
	assert.doesNotMatch(source, /type=\{?"button"?\}\s*\{\.\.\.props\}/);
	assert.match(source, /\{\.\.\.props\}/);
});
