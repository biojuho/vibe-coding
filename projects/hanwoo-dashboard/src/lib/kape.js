
const KAPE_API_BASE = "https://data.ekape.or.kr/openapi-data/service/user/grade/whslSlaughter/cattleWhslSlaughter";

/**
 * Fetches real-time market price from KAPE (축산물품질평가원) API.
 * Falls back to simulated data if API key is missing or request fails.
 *
 * API 문서: https://data.ekape.or.kr/openapi-data/service/user/grade/whslSlaughter
 * - serviceKey: 공공데이터포털 인증키
 * - issueDate: YYYYMMDD (도축일자)
 * - gradeType: 1 (한우)
 * - _type: json
 */
export async function fetchMarketPrice() {
  const apiKey = process.env.KAPE_SERVICE_KEY;

  if (!apiKey) {
    console.warn("KAPE_SERVICE_KEY not found in .env. Using simulated data.");
    return await getSimulatedData();
  }

  try {
    // Try last 7 days to find available data (weekends/holidays have no data)
    for (let dayOffset = 1; dayOffset <= 7; dayOffset++) {
      const targetDate = new Date();
      targetDate.setDate(targetDate.getDate() - dayOffset);
      const issueDate = targetDate.toISOString().slice(0, 10).replace(/-/g, "");

      const url = new URL(KAPE_API_BASE);
      url.searchParams.set("serviceKey", apiKey);
      url.searchParams.set("issueDate", issueDate);
      url.searchParams.set("gradeType", "1"); // 1 = 한우
      url.searchParams.set("_type", "json");

      const res = await fetch(url.toString(), {
        next: { revalidate: 3600 } // 1시간 ISR 캐시
      });

      if (!res.ok) {
        console.warn(`KAPE API returned ${res.status} for date ${issueDate}`);
        continue;
      }

      const data = await res.json();
      const parsed = parseKapeResponse(data, issueDate);
      if (parsed) return parsed;
    }

    console.warn("No KAPE data found for last 7 days. Falling back to simulated data.");
    return await getSimulatedData();
  } catch (error) {
    console.error("Failed to fetch from KAPE API:", error);
    return await getSimulatedData();
  }
}

/**
 * Parse KAPE API response into our app format.
 *
 * 응답 구조:
 * response.body.items.item[] = { judsgCd, avgAmt, catgCd, ... }
 * - catgCd: "1" 거세우, "2" 암소
 * - judsgCd: "11" 1++, "12" 1+, "13" 1등급
 * - avgAmt: 평균 경매가 (원/kg)
 */
function parseKapeResponse(data, issueDate) {
  try {
    const items = data?.response?.body?.items?.item;
    if (!items || (Array.isArray(items) && items.length === 0)) return null;

    const itemList = Array.isArray(items) ? items : [items];

    const bull = { grade1pp: 0, grade1p: 0, grade1: 0 };
    const cow = { grade1pp: 0, grade1p: 0, grade1: 0 };

    const gradeMap = { "11": "grade1pp", "12": "grade1p", "13": "grade1" };

    itemList.forEach(item => {
      const catg = String(item.catgCd); // "1"=거세우, "2"=암소
      const grade = gradeMap[String(item.judsgCd)];
      const price = Math.round(Number(item.avgAmt) || 0);

      if (!grade || price === 0) return;

      if (catg === "1") bull[grade] = price;
      else if (catg === "2") cow[grade] = price;
    });

    // At least some data must exist
    if (bull.grade1pp === 0 && bull.grade1p === 0 && cow.grade1pp === 0) return null;

    // Determine trend from previous day data (simplified: compare 1++ vs 1+)
    const trend = bull.grade1pp > bull.grade1p ? "up" : "down";

    const dateFormatted = `${issueDate.slice(0, 4)}.${issueDate.slice(4, 6)}.${issueDate.slice(6, 8)}`;

    return {
      isRealtime: true,
      date: dateFormatted,
      bull,
      cow,
      trend
    };
  } catch (e) {
    console.error("Failed to parse KAPE response:", e);
    return null;
  }
}

async function getSimulatedData() {
  await new Promise(resolve => setTimeout(resolve, 300));

  const todayStr = new Date().toLocaleDateString('ko-KR');

  return {
    isRealtime: false,
    date: todayStr,
    bull: {
      grade1pp: 21500 + Math.floor(Math.random() * 1000 - 500),
      grade1p: 19800 + Math.floor(Math.random() * 800 - 400),
      grade1: 18500 + Math.floor(Math.random() * 600 - 300)
    },
    cow: {
      grade1pp: 18500 + Math.floor(Math.random() * 1000 - 500),
      grade1p: 17200 + Math.floor(Math.random() * 800 - 400),
      grade1: 16000 + Math.floor(Math.random() * 600 - 300)
    },
    trend: Math.random() > 0.5 ? 'up' : 'down'
  };
}
