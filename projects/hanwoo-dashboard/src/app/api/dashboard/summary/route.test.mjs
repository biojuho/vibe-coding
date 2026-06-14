import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function readSource(relativePath) {
	return readFileSync(path.join(__dirname, relativePath), "utf8");
}

// HW-DSR001: saveDashboardSummarySnapshot이 null 반환 시 freshPayload fallback
test(
	"dashboard summary route uses freshPayload fallback when snapshot save fails (HW-DSR001)",
	() => {
		const source = readSource("route.js");

		// freshPayload는 if 블록 밖에서 선언되어야 함
		assert.match(source, /let freshPayload = null;/);

		// saveDashboardSummarySnapshot 결과가 null이어도 data 참조 안전
		assert.match(source, /snapshot\?\.payload \?\? freshPayload/);

		// snapshot null 시 buildMeta 대신 직접 meta 구성
		assert.match(source, /snapshot\s*\?\s*buildMeta\(snapshot,\s*source\)/);

		// 기존의 snapshot.payload 직접 참조(위험 패턴)가 없어야 함
		assert.doesNotMatch(source, /data:\s*snapshot\.payload/);
	},
);
