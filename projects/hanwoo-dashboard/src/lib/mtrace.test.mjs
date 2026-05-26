import assert from "node:assert/strict";
import test from "node:test";

import { TimeoutError } from "./fetchWithTimeout.js";
import { lookupCattleByTag } from "./mtrace.js";

const ORIGINAL_FETCH = globalThis.fetch;
const ORIGINAL_SERVICE_KEY = process.env.MTRACE_SERVICE_KEY;

function restoreEnvironment() {
	globalThis.fetch = ORIGINAL_FETCH;
	if (ORIGINAL_SERVICE_KEY === undefined) {
		delete process.env.MTRACE_SERVICE_KEY;
	} else {
		process.env.MTRACE_SERVICE_KEY = ORIGINAL_SERVICE_KEY;
	}
}

test.afterEach(restoreEnvironment);

test("lookupCattleByTag returns Korean operator messages for local validation failures", async () => {
	delete process.env.MTRACE_SERVICE_KEY;

	assert.deepEqual(await lookupCattleByTag("002082037849"), {
		success: false,
		message:
			"축산물이력제 조회 키가 설정되지 않았습니다. 관리자에게 문의해 주세요.",
	});

	process.env.MTRACE_SERVICE_KEY = "test-key";

	assert.deepEqual(await lookupCattleByTag("123"), {
		success: false,
		message: "올바른 이력번호를 입력한 뒤 조회해 주세요.",
	});
});

test("lookupCattleByTag returns Korean operator messages for degraded MTRACE responses", async () => {
	process.env.MTRACE_SERVICE_KEY = "test-key";

	globalThis.fetch = async () => ({
		status: 429,
		ok: false,
		headers: new Headers({ "retry-after": "30" }),
		json: async () => ({}),
	});

	assert.deepEqual(await lookupCattleByTag("002082037849"), {
		success: false,
		message:
			"축산물이력제 조회가 일시적으로 제한되었습니다. 30초 후 다시 시도해 주세요.",
	});

	globalThis.fetch = async () => ({
		status: 500,
		ok: false,
		headers: new Headers(),
		json: async () => ({}),
	});

	assert.deepEqual(await lookupCattleByTag("002082037849"), {
		success: false,
		message: "축산물이력제 조회가 실패했습니다. 상태 코드: 500",
	});

	globalThis.fetch = async () => ({
		status: 200,
		ok: true,
		headers: new Headers(),
		json: async () => ({ response: { body: { items: {} } } }),
	});

	assert.deepEqual(await lookupCattleByTag("002082037849"), {
		success: false,
		message: "해당 이력번호로 등록된 개체 정보를 찾지 못했습니다.",
	});
});

test("lookupCattleByTag localizes timeout and default breed fallback", async () => {
	process.env.MTRACE_SERVICE_KEY = "test-key";

	globalThis.fetch = async () => {
		throw new TimeoutError("축산물이력제 조회 시간이 초과되었습니다.", 5000);
	};

	const timeoutResult = await lookupCattleByTag("002082037849");
	assert.deepEqual(timeoutResult, {
		success: false,
		message:
			"축산물이력제 조회 시간이 초과되었습니다. 잠시 후 다시 시도해 주세요.",
	});
	assert.notEqual(
		timeoutResult.message,
		"축산물이력제 조회 시간이 초과되었습니다. 다시 시도해 주세요.",
	);

	globalThis.fetch = async () => ({
		status: 200,
		ok: true,
		headers: new Headers(),
		json: async () => ({
			response: {
				body: {
					items: {
						item: {
							birthYmd: "20250102",
							sexNm: "암",
							farmAddr: "전북 정읍",
						},
					},
				},
			},
		}),
	});

	assert.deepEqual(await lookupCattleByTag("002082037849"), {
		success: true,
		data: {
			birthDate: "20250102",
			gender: "암",
			breed: "한우",
			farmAddr: "전북 정읍",
		},
	});
});

test("lookupCattleByTag keeps internal API diagnostics localized", () => {
	// Source-level guard because this path is intentionally swallowed into a safe user message.
	assert.match(String(lookupCattleByTag), /축산물이력제 API 오류/);
	assert.doesNotMatch(String(lookupCattleByTag), /MTRACE API error/);
});
