import { fetchWithTimeout, isTimeoutError } from './fetchWithTimeout';

const KAPE_API_BASE =
  'https://data.ekape.or.kr/openapi-data/service/user/grade/whslSlaughter/cattleWhslSlaughter';
const KAPE_REQUEST_TIMEOUT_MS = 4000;
const KAPE_TOTAL_DEADLINE_MS = 12000;

/**
 * Fetches real-time market price from KAPE.
 */
export async function fetchMarketPrice() {
  const apiKey = process.env.KAPE_SERVICE_KEY;

  if (!apiKey) {
    console.warn('KAPE_SERVICE_KEY not found in .env. Skipping live market price lookup.');
    return null;
  }

  try {
    const startedAt = Date.now();

    // Try the last 7 days because weekends and holidays often have no auction data.
    for (let dayOffset = 1; dayOffset <= 7; dayOffset++) {
      const elapsedMs = Date.now() - startedAt;
      if (elapsedMs >= KAPE_TOTAL_DEADLINE_MS) {
        throw new Error(`KAPE lookup exceeded ${KAPE_TOTAL_DEADLINE_MS}ms overall deadline.`);
      }

      const targetDate = new Date();
      targetDate.setDate(targetDate.getDate() - dayOffset);
      const issueDate = targetDate.toISOString().slice(0, 10).replace(/-/g, '');

      const url = new URL(KAPE_API_BASE);
      url.searchParams.set('serviceKey', apiKey);
      url.searchParams.set('issueDate', issueDate);
      url.searchParams.set('gradeType', '1');
      url.searchParams.set('_type', 'json');

      const remainingMs = Math.max(1000, KAPE_TOTAL_DEADLINE_MS - elapsedMs);
      const res = await fetchWithTimeout(
        url.toString(),
        {
          next: { revalidate: 3600 },
        },
        {
          timeoutMs: Math.min(KAPE_REQUEST_TIMEOUT_MS, remainingMs),
          errorMessage: `KAPE request timed out for date ${issueDate}.`,
        },
      );

      if (!res.ok) {
        console.warn(`KAPE API returned ${res.status} for date ${issueDate}`);
        continue;
      }

      const bodyText = await res.text();
      if (!bodyText.trim()) {
        console.warn(`KAPE API returned an empty body for date ${issueDate}`);
        continue;
      }

      let data;
      try {
        data = JSON.parse(bodyText);
      } catch (error) {
        console.warn(`KAPE API returned unreadable JSON for date ${issueDate}:`, error);
        continue;
      }

      const parsed = parseKapeResponse(data, issueDate);
      if (parsed) {
        return parsed;
      }
    }

    console.warn('No KAPE data found for the last 7 days.');
    return null;
  } catch (error) {
    if (isTimeoutError(error)) {
      console.warn('KAPE API timed out.');
    }

    console.error('Failed to fetch from KAPE API:', error);
    return null;
  }
}

/**
 * Parse KAPE API response into our app format.
 */
function parseKapeResponse(data, issueDate) {
  try {
    const items = data?.response?.body?.items?.item;
    if (!items || (Array.isArray(items) && items.length === 0)) return null;

    const itemList = Array.isArray(items) ? items : [items];

    const bull = { grade1pp: 0, grade1p: 0, grade1: 0 };
    const cow = { grade1pp: 0, grade1p: 0, grade1: 0 };
    const gradeMap = { '11': 'grade1pp', '12': 'grade1p', '13': 'grade1' };

    itemList.forEach((item) => {
      const category = String(item.catgCd);
      const grade = gradeMap[String(item.judsgCd)];
      const price = Math.round(Number(item.avgAmt) || 0);

      if (!grade || price === 0) {
        return;
      }

      if (category === '1') {
        bull[grade] = price;
      } else if (category === '2') {
        cow[grade] = price;
      }
    });

    if (bull.grade1pp === 0 && bull.grade1p === 0 && cow.grade1pp === 0) {
      return null;
    }

    const trend = bull.grade1pp > bull.grade1p ? 'up' : 'down';
    const dateFormatted = `${issueDate.slice(0, 4)}.${issueDate.slice(4, 6)}.${issueDate.slice(6, 8)}`;

    return {
      isRealtime: true,
      source: 'KAPE',
      issueDate: `${issueDate.slice(0, 4)}-${issueDate.slice(4, 6)}-${issueDate.slice(6, 8)}`,
      date: dateFormatted,
      bull,
      cow,
      trend,
    };
  } catch (error) {
    console.error('Failed to parse KAPE response:', error);
    return null;
  }
}
