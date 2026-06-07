import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

const css = readFileSync(path.join(process.cwd(), "src", "style.css"), "utf8");

describe("mobile touch targets", () => {
	it("keeps active game controls large enough after container scaling", () => {
		expect(css).toMatch(/\.icon-btn\s*{[^}]*min-width:\s*72px;/s);
		expect(css).toMatch(/\.icon-btn\s*{[^}]*min-height:\s*72px;/s);
		expect(css).toMatch(/\.difficulty-btn\s*{[^}]*min-width:\s*72px;/s);
		expect(css).toMatch(/\.difficulty-btn\s*{[^}]*min-height:\s*72px;/s);
	});

	it("keeps overlay mode and dialog buttons mobile safe", () => {
		expect(css).toMatch(/\.btn\s*{[^}]*min-height:\s*72px;/s);
		expect(css).toMatch(/\.mode-btn\s*{[^}]*min-height:\s*72px;/s);
		expect(css).toMatch(/\.btn-compact\s*{[^}]*min-height:\s*72px;/s);
	});
});
