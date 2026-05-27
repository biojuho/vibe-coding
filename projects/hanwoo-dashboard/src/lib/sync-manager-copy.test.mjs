import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

function readSource(relativePath) {
	return readFileSync(path.join(__dirname, "..", relativePath), "utf8");
}

test("offline sync thrown errors use stable Korean retry copy", () => {
	const source = readSource("lib/syncManager.js");
	const queueHookSource = readSource("lib/hooks/useOfflineSyncQueue.js");

	assert.match(
		source,
		/const OFFLINE_SYNC_RETRY_ERROR_MESSAGE\s*=\s*["']오프라인 요청을 동기화하지 못했습니다\. 잠시 후 다시 시도해 주세요\.["'];?/,
	);
	assert.match(
		source,
		/const OFFLINE_SYNC_UNSUPPORTED_ACTION_MESSAGE\s*=\s*["']지원하지 않는 오프라인 작업입니다\. 작업을 다시 등록해 주세요\.["'];?/,
	);
	assert.match(
		source,
		/const OFFLINE_SYNC_UNSUCCESSFUL_RESULT_MESSAGE\s*=\s*["']오프라인 작업을 서버에 반영하지 못했습니다\. 잠시 후 다시 시도해 주세요\.["'];?/,
	);
	assert.match(
		queueHookSource,
		/const OFFLINE_SYNC_REFRESH_ERROR_MESSAGE\s*=\s*["']동기화 결과를 보려면 화면을 새로고침해 주세요\.["'];?/,
	);
	assert.match(queueHookSource, /description: ["']잠시 후 다시 시도해 주세요\.["']/);
	assert.match(
		queueHookSource,
		/try \{\s+router\.refresh\(\);\s+\} catch \(refreshError\) \{/,
	);
	assert.match(
		queueHookSource,
		/console\.error\(["']Offline queue refresh failed:/,
	);
	assert.match(
		queueHookSource,
		/title: ["']동기화 후 화면 새로고침에 실패했습니다\.["'][\s\S]*?description: OFFLINE_SYNC_REFRESH_ERROR_MESSAGE/,
	);
	assert.match(
		source,
		/const errorMessage = OFFLINE_SYNC_RETRY_ERROR_MESSAGE;/,
	);
	assert.match(source, /errorMessage: OFFLINE_SYNC_UNSUPPORTED_ACTION_MESSAGE,/);
	assert.match(source, /: OFFLINE_SYNC_UNSUCCESSFUL_RESULT_MESSAGE;/);
	assert.doesNotMatch(source, /error instanceof Error && error\.message/);
	assert.doesNotMatch(source, /threw an unknown error/);
	assert.doesNotMatch(source, /No offline sync handler is registered/);
	assert.doesNotMatch(source, /returned an unsuccessful result/);
	assert.doesNotMatch(queueHookSource, /시도해주세요/);
});
