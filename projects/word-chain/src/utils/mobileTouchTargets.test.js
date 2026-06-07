import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const SRC_DIR = path.resolve(
	path.dirname(fileURLToPath(import.meta.url)),
	"..",
);

const buttonSource = readFileSync(
	path.join(SRC_DIR, "components", "ui", "button.jsx"),
	"utf8",
);

describe("mobile touch targets", () => {
	it("keeps primary and icon buttons at least 44px tall", () => {
		expect(buttonSource).toContain('default: "min-h-11 px-6 py-2"');
		expect(buttonSource).toContain('icon: "h-11 w-11"');
		expect(buttonSource).not.toContain('default: "h-10 px-6 py-2"');
		expect(buttonSource).not.toContain('icon: "h-10 w-10"');
	});
});
