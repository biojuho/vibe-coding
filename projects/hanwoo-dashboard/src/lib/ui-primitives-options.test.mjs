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

test("shared Badge normalizes malformed top-level props before rendering", () => {
	const source = readSource("components/ui/badge.js");

	assert.match(source, /function normalizeBadgeOptions\(options\) \{/);
	assert.match(
		source,
		/return options && typeof options === "object" && !Array\.isArray\(options\)\s+\? options\s+:\s+\{\};/,
	);
	assert.match(source, /function Badge\(options = \{\}\) \{/);
	assert.match(
		source,
		/const \{ className, variant, \.\.\.props \} = normalizeBadgeOptions\(options\);/,
	);
	assert.match(
		source,
		/<div className=\{cn\(badgeVariants\(\{ variant \}\), className\)\} \{\.\.\.props\} \/>/,
	);
});

test("shared Card primitives normalize malformed top-level props before rendering", () => {
	const source = readSource("components/ui/card.js");

	assert.match(source, /function normalizeCardOptions\(options\) \{/);
	assert.match(
		source,
		/return options && typeof options === "object" && !Array\.isArray\(options\)\s+\? options\s+:\s+\{\};/,
	);
	for (const componentName of [
		"Card",
		"CardHeader",
		"CardTitle",
		"CardDescription",
		"CardContent",
		"CardFooter",
	]) {
		assert.match(
			source,
			new RegExp(
				`const ${componentName} = React\\.forwardRef\\(\\(options, ref\\) => \\{[\\s\\S]*?const \\{ className, \\.\\.\\.props \\} = normalizeCardOptions\\(options\\);`,
			),
		);
	}
	assert.match(source, /Card\.displayName = "Card";/);
	assert.match(source, /CardHeader\.displayName = "CardHeader";/);
	assert.match(source, /CardTitle\.displayName = "CardTitle";/);
	assert.match(source, /CardDescription\.displayName = "CardDescription";/);
	assert.match(source, /CardContent\.displayName = "CardContent";/);
	assert.match(source, /CardFooter\.displayName = "CardFooter";/);
});

test("premium Card primitives normalize malformed top-level props before rendering", () => {
	const source = readSource("components/ui/premium-card.js");

	assert.match(source, /function normalizePremiumCardOptions\(options\) \{/);
	assert.match(
		source,
		/return options && typeof options === "object" && !Array\.isArray\(options\)\s+\? options\s+:\s+\{\};/,
	);
	for (const componentName of [
		"PremiumCard",
		"PremiumCardTitle",
		"PremiumCardDescription",
		"PremiumCardContent",
		"PremiumCardFooter",
	]) {
		assert.match(
			source,
			new RegExp(
				`const ${componentName} = React\\.forwardRef\\(\\(options, ref\\) => \\{[\\s\\S]*?const \\{ className, \\.\\.\\.props \\} = normalizePremiumCardOptions\\(options\\);`,
			),
		);
	}
	assert.match(
		source,
		/const PremiumCardHeader = React\.forwardRef\(\(options, ref\) => \{[\s\S]*?const \{ className, title, icon, description, children, \.\.\.props \} =\s+normalizePremiumCardOptions\(options\);/,
	);
	assert.match(
		source,
		/const PremiumInfoCard = \(options = \{\}\) => \{[\s\S]*?const \{ title, value, change, changeType = "positive" \} =\s+normalizePremiumCardOptions\(options\);/,
	);
	assert.match(source, /PremiumCard\.displayName = "PremiumCard";/);
	assert.match(source, /PremiumCardHeader\.displayName = "PremiumCardHeader";/);
	assert.match(source, /PremiumCardTitle\.displayName = "PremiumCardTitle";/);
	assert.match(
		source,
		/PremiumCardDescription\.displayName = "PremiumCardDescription";/,
	);
	assert.match(source, /PremiumCardContent\.displayName = "PremiumCardContent";/);
	assert.match(source, /PremiumCardFooter\.displayName = "PremiumCardFooter";/);
});

test("form primitives normalize malformed top-level props before rendering", () => {
	const inputSource = readSource("components/ui/input.js");
	const labelSource = readSource("components/ui/label.js");

	assert.match(inputSource, /function normalizeInputOptions\(options\) \{/);
	assert.match(
		inputSource,
		/return options && typeof options === "object" && !Array\.isArray\(options\)\s+\? options\s+:\s+\{\};/,
	);
	assert.match(inputSource, /const Input = React\.forwardRef\(\(options, ref\) => \{/);
	assert.match(
		inputSource,
		/const \{ className, type, \.\.\.props \} = normalizeInputOptions\(options\);/,
	);
	assert.match(inputSource, /Input\.displayName = "Input";/);

	assert.match(labelSource, /function normalizeLabelOptions\(options\) \{/);
	assert.match(
		labelSource,
		/return options && typeof options === "object" && !Array\.isArray\(options\)\s+\? options\s+:\s+\{\};/,
	);
	assert.match(labelSource, /const Label = React\.forwardRef\(\(options, ref\) => \{/);
	assert.match(
		labelSource,
		/const \{ className, \.\.\.props \} = normalizeLabelOptions\(options\);/,
	);
	assert.match(labelSource, /Label\.displayName = LabelPrimitive\.Root\.displayName;/);
});

test("Progress normalizes malformed props and non-finite values before rendering", () => {
	const source = readSource("components/ui/progress.js");

	assert.match(source, /function normalizeProgressOptions\(options\) \{/);
	assert.match(
		source,
		/return options && typeof options === "object" && !Array\.isArray\(options\)\s+\? options\s+:\s+\{\};/,
	);
	assert.match(source, /function normalizeProgressValue\(value\) \{/);
	assert.match(source, /const numericValue = Number\(value\);/);
	assert.match(source, /if \(!Number\.isFinite\(numericValue\)\) \{\s+return 0;\s+\}/);
	assert.match(source, /return Math\.min\(100, Math\.max\(0, numericValue\)\);/);
	assert.match(
		source,
		/const \{ className, value, \.\.\.props \} = normalizeProgressOptions\(options\);/,
	);
	assert.match(source, /const safeValue = normalizeProgressValue\(value\);/);
	assert.match(source, /translateX\(-\$\{100 - safeValue\}%\)/);
	assert.doesNotMatch(source, /100 - \(value \|\| 0\)/);
	assert.match(source, /Progress\.displayName = ProgressPrimitive\.Root\.displayName;/);
});

test("Avatar primitives normalize malformed top-level props before rendering", () => {
	const source = readSource("components/ui/avatar.js");

	assert.match(source, /function normalizeAvatarOptions\(options\) \{/);
	assert.match(
		source,
		/return options && typeof options === "object" && !Array\.isArray\(options\)\s+\? options\s+:\s+\{\};/,
	);
	for (const componentName of ["Avatar", "AvatarImage", "AvatarFallback"]) {
		assert.match(
			source,
			new RegExp(
				`const ${componentName} = React\\.forwardRef\\(\\(options, ref\\) => \\{[\\s\\S]*?const \\{ className, \\.\\.\\.props \\} = normalizeAvatarOptions\\(options\\);`,
			),
		);
	}
	assert.match(source, /Avatar\.displayName = AvatarPrimitive\.Root\.displayName;/);
	assert.match(
		source,
		/AvatarImage\.displayName = AvatarPrimitive\.Image\.displayName;/,
	);
	assert.match(
		source,
		/AvatarFallback\.displayName = AvatarPrimitive\.Fallback\.displayName;/,
	);
});

test("Skeleton normalizes malformed top-level props before rendering", () => {
	const source = readSource("components/ui/skeleton.js");

	assert.match(source, /function normalizeSkeletonOptions\(options\) \{/);
	assert.match(
		source,
		/return options && typeof options === "object" && !Array\.isArray\(options\)\s+\? options\s+:\s+\{\};/,
	);
	assert.match(source, /function Skeleton\(options = \{\}\) \{/);
	assert.match(
		source,
		/const \{ className, \.\.\.props \} = normalizeSkeletonOptions\(options\);/,
	);
	assert.match(source, /export \{ Skeleton \};/);
});

test("Tabs primitives normalize malformed top-level props before rendering", () => {
	const source = readSource("components/ui/tabs.js");

	assert.match(source, /function normalizeTabsOptions\(options\) \{/);
	assert.match(
		source,
		/return options && typeof options === "object" && !Array\.isArray\(options\)\s+\? options\s+:\s+\{\};/,
	);
	for (const componentName of ["TabsList", "TabsTrigger", "TabsContent"]) {
		assert.match(
			source,
			new RegExp(
				`const ${componentName} = React\\.forwardRef\\(\\(options, ref\\) => \\{[\\s\\S]*?const \\{ className, \\.\\.\\.props \\} = normalizeTabsOptions\\(options\\);`,
			),
		);
	}
	assert.match(source, /TabsList\.displayName = TabsPrimitive\.List\.displayName;/);
	assert.match(
		source,
		/TabsTrigger\.displayName = TabsPrimitive\.Trigger\.displayName;/,
	);
	assert.match(
		source,
		/TabsContent\.displayName = TabsPrimitive\.Content\.displayName;/,
	);
});

test("Select primitives normalize malformed top-level props before rendering", () => {
	const source = readSource("components/ui/select.js");

	assert.match(source, /function normalizeSelectOptions\(options\) \{/);
	assert.match(
		source,
		/return options && typeof options === "object" && !Array\.isArray\(options\)\s+\? options\s+:\s+\{\};/,
	);
	assert.match(
		source,
		/const \{ className, children, \.\.\.props \} = normalizeSelectOptions\(options\);/,
	);
	assert.match(
		source,
		/const \{ className, children, position = "popper", \.\.\.props \} =\s+normalizeSelectOptions\(options\);/,
	);
	for (const componentName of [
		"SelectItem",
		"SelectSeparator",
		"SelectLabel",
	]) {
		assert.match(
			source,
			new RegExp(
				`const ${componentName} = React\\.forwardRef\\(\\(options, ref\\) => \\{[\\s\\S]*?const \\{ className, (?:children, )?\\.\\.\\.props \\} = normalizeSelectOptions\\(options\\);`,
			),
		);
	}
	assert.match(
		source,
		/SelectTrigger\.displayName = SelectPrimitive\.Trigger\.displayName;/,
	);
	assert.match(
		source,
		/SelectContent\.displayName = SelectPrimitive\.Content\.displayName;/,
	);
	assert.match(source, /SelectItem\.displayName = SelectPrimitive\.Item\.displayName;/);
	assert.match(
		source,
		/SelectSeparator\.displayName = SelectPrimitive\.Separator\.displayName;/,
	);
	assert.match(
		source,
		/SelectLabel\.displayName = SelectPrimitive\.Label\.displayName;/,
	);
});

test("Dialog primitives normalize malformed top-level props before rendering", () => {
	const source = readSource("components/ui/dialog.js");

	assert.match(source, /function normalizeDialogOptions\(options\) \{/);
	assert.match(
		source,
		/return options && typeof options === "object" && !Array\.isArray\(options\)\s+\? options\s+:\s+\{\};/,
	);
	for (const componentName of [
		"DialogOverlay",
		"DialogTitle",
		"DialogDescription",
	]) {
		assert.match(
			source,
			new RegExp(
				`const ${componentName} = React\\.forwardRef\\(\\(options, ref\\) => \\{[\\s\\S]*?const \\{ className, \\.\\.\\.props \\} = normalizeDialogOptions\\(options\\);`,
			),
		);
	}
	assert.match(
		source,
		/const DialogContent = React\.forwardRef\(\(options, ref\) => \{[\s\S]*?closeLabel = "대화상자 닫기",[\s\S]*?\} = normalizeDialogOptions\(options\);/,
	);
	for (const componentName of ["DialogHeader", "DialogFooter"]) {
		assert.match(
			source,
			new RegExp(
				`const ${componentName} = \\(options = \\{\\}\\) => \\{[\\s\\S]*?const \\{ className, \\.\\.\\.props \\} = normalizeDialogOptions\\(options\\);`,
			),
		);
	}
	assert.match(
		source,
		/DialogOverlay\.displayName = DialogPrimitive\.Overlay\.displayName;/,
	);
	assert.match(
		source,
		/DialogContent\.displayName = DialogPrimitive\.Content\.displayName;/,
	);
	assert.match(source, /DialogHeader\.displayName = "DialogHeader";/);
	assert.match(source, /DialogFooter\.displayName = "DialogFooter";/);
	assert.match(
		source,
		/DialogTitle\.displayName = DialogPrimitive\.Title\.displayName;/,
	);
	assert.match(
		source,
		/DialogDescription\.displayName = DialogPrimitive\.Description\.displayName;/,
	);
});

test("Premium input primitives normalize malformed top-level props before rendering", () => {
	const source = readSource("components/ui/premium-input.js");

	assert.match(source, /function normalizePremiumInputOptions\(options\) \{/);
	assert.match(
		source,
		/return options && typeof options === "object" && !Array\.isArray\(options\)\s+\? options\s+:\s+\{\};/,
	);
	assert.match(
		source,
		/const \{ className, type = "text", hasError, \.\.\.props \} =\s+normalizePremiumInputOptions\(options\);/,
	);
	assert.match(
		source,
		/const \{ className, hasError, children, \.\.\.props \} =\s+normalizePremiumInputOptions\(options\);/,
	);
	for (const componentName of ["PremiumTextarea", "PremiumLabel"]) {
		assert.match(
			source,
			new RegExp(
				`const ${componentName} = forwardRef\\(\\(options, ref\\) => \\{[\\s\\S]*?const \\{ className, (?:children, )?\\.\\.\\.props \\} =\\s+normalizePremiumInputOptions\\(options\\);`,
			),
		);
	}
	assert.match(source, /PremiumInput\.displayName = "PremiumInput";/);
	assert.match(source, /PremiumTextarea\.displayName = "PremiumTextarea";/);
	assert.match(source, /PremiumSelect\.displayName = "PremiumSelect";/);
	assert.match(source, /PremiumLabel\.displayName = "PremiumLabel";/);
});
