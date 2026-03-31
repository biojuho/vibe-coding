
/**
 * MTRACE (축산물이력제) API Client
 *
 * API 문서: https://data.mtrace.go.kr/openapi/cattleinfo
 * - serviceKey: 공공데이터포털 발급키
 * - corpNo: 이력번호 (12자리)
 *
 * .env에 MTRACE_SERVICE_KEY 추가 필요 (data.go.kr에서 발급)
 */

const MTRACE_API_BASE = "https://data.mtrace.go.kr/openapi/cattleinfo";

/**
 * Lookup cattle info by tag number (이력번호).
 * @param {string} tagNumber - e.g. "002082037849"
 * @returns {{ success: boolean, data?: { birthDate, gender, breed, farmAddr }, message?: string }}
 */
export async function lookupCattleByTag(tagNumber) {
  const apiKey = process.env.MTRACE_SERVICE_KEY;

  if (!apiKey) {
    return { success: false, message: "MTRACE API 키가 설정되지 않았습니다. .env에 MTRACE_SERVICE_KEY를 추가하세요." };
  }

  if (!tagNumber || tagNumber.replace(/[-\s]/g, "").length < 10) {
    return { success: false, message: "올바른 이력번호를 입력하세요." };
  }

  // Strip dashes/spaces for API call
  const cleanTag = tagNumber.replace(/[-\s]/g, "");

  try {
    const url = new URL(MTRACE_API_BASE);
    url.searchParams.set("serviceKey", apiKey);
    url.searchParams.set("corpNo", cleanTag);
    url.searchParams.set("_type", "json");

    const res = await fetch(url.toString(), {
      next: { revalidate: 86400 } // Cache for 24h (cattle info doesn't change)
    });

    if (!res.ok) {
      return { success: false, message: `API 응답 오류 (${res.status})` };
    }

    const json = await res.json();
    const item = json?.response?.body?.items?.item;

    if (!item) {
      return { success: false, message: "해당 이력번호의 정보를 찾을 수 없습니다." };
    }

    // item can be array or single object
    const cattle = Array.isArray(item) ? item[0] : item;

    return {
      success: true,
      data: {
        birthDate: cattle.birthYmd || null, // "20220315" format
        gender: cattle.sexNm === "암" ? "암" : cattle.sexNm === "수" ? "수" : cattle.sexNm || null,
        breed: cattle.lsTypeNm || "한우",
        farmAddr: cattle.farmAddr || null,
      }
    };
  } catch (error) {
    console.error("MTRACE API error:", error);
    return { success: false, message: "이력제 조회 중 오류가 발생했습니다." };
  }
}
