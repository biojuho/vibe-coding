import { fetchWithTimeout, isTimeoutError } from "./fetchWithTimeout.js";

const MTRACE_API_BASE = "https://data.mtrace.go.kr/openapi/cattleinfo";

async function readJsonSafely(response) {
	try {
		return await response.json();
	} catch {
		return null;
	}
}

export async function lookupCattleByTag(tagNumber) {
	const apiKey = process.env.MTRACE_SERVICE_KEY;

	if (!apiKey) {
		return {
			success: false,
			message:
				"축산물이력제 조회 키가 설정되지 않았습니다. 관리자에게 문의해 주세요.",
		};
	}

	if (!tagNumber || tagNumber.replace(/[-\s]/g, "").length < 10) {
		return {
			success: false,
			message: "올바른 이력번호를 입력한 뒤 조회해 주세요.",
		};
	}

	const cleanTag = tagNumber.replace(/[-\s]/g, "");

	try {
		const url = new URL(MTRACE_API_BASE);
		url.searchParams.set("serviceKey", apiKey);
		url.searchParams.set("corpNo", cleanTag);
		url.searchParams.set("_type", "json");

		const response = await fetchWithTimeout(
			url.toString(),
			{
				next: { revalidate: 86400 },
			},
			{
				timeoutMs: 5000,
				errorMessage: "축산물이력제 조회 시간이 초과되었습니다.",
			},
		);

		if (response.status === 429) {
			const retryAfter = response.headers.get("retry-after");
			return {
				success: false,
				message: retryAfter
					? `축산물이력제 조회가 일시적으로 제한되었습니다. ${retryAfter}초 후 다시 시도해 주세요.`
					: "축산물이력제 조회가 일시적으로 제한되었습니다. 잠시 후 다시 시도해 주세요.",
			};
		}

		if (!response.ok) {
			return {
				success: false,
				message: `축산물이력제 조회가 실패했습니다. 상태 코드: ${response.status}`,
			};
		}

		const json = await readJsonSafely(response);
		if (!json) {
			return {
				success: false,
				message:
					"축산물이력제 응답을 읽을 수 없습니다. 잠시 후 다시 시도해 주세요.",
			};
		}

		const item = json?.response?.body?.items?.item;
		if (!item) {
			return {
				success: false,
				message: "해당 이력번호로 등록된 개체 정보를 찾지 못했습니다.",
			};
		}

		const cattle = Array.isArray(item) ? item[0] : item;

		return {
			success: true,
			data: {
				birthDate: cattle.birthYmd || null,
				gender: cattle.sexNm || null,
				breed: cattle.lsTypeNm || "한우",
				farmAddr: cattle.farmAddr || null,
			},
		};
	} catch (error) {
		if (isTimeoutError(error)) {
			return {
				success: false,
				message:
					"축산물이력제 조회 시간이 초과되었습니다. 잠시 후 다시 시도해 주세요.",
			};
		}

		console.error("축산물이력제 API 오류:", error);
		return {
			success: false,
			message:
				"이력번호 조회 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
		};
	}
}
