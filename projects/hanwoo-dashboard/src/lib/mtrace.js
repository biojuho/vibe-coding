import { fetchWithTimeout, isTimeoutError } from './fetchWithTimeout';

const MTRACE_API_BASE = 'https://data.mtrace.go.kr/openapi/cattleinfo';

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
      message: 'MTRACE API key is missing. Set MTRACE_SERVICE_KEY in the environment.',
    };
  }

  if (!tagNumber || tagNumber.replace(/[-\s]/g, '').length < 10) {
    return {
      success: false,
      message: 'Enter a valid cattle tag number before running the lookup.',
    };
  }

  const cleanTag = tagNumber.replace(/[-\s]/g, '');

  try {
    const url = new URL(MTRACE_API_BASE);
    url.searchParams.set('serviceKey', apiKey);
    url.searchParams.set('corpNo', cleanTag);
    url.searchParams.set('_type', 'json');

    const response = await fetchWithTimeout(
      url.toString(),
      {
        next: { revalidate: 86400 },
      },
      {
        timeoutMs: 5000,
        errorMessage: 'MTRACE lookup timed out after 5000ms.',
      },
    );

    if (response.status === 429) {
      const retryAfter = response.headers.get('retry-after');
      return {
        success: false,
        message: retryAfter
          ? `MTRACE lookup is rate-limited. Retry after ${retryAfter} seconds.`
          : 'MTRACE lookup is temporarily rate-limited. Please retry shortly.',
      };
    }

    if (!response.ok) {
      return {
        success: false,
        message: `MTRACE API returned ${response.status}.`,
      };
    }

    const json = await readJsonSafely(response);
    if (!json) {
      return {
        success: false,
        message: 'MTRACE returned an unreadable response.',
      };
    }

    const item = json?.response?.body?.items?.item;
    if (!item) {
      return {
        success: false,
        message: 'No cattle information was found for that tag number.',
      };
    }

    const cattle = Array.isArray(item) ? item[0] : item;

    return {
      success: true,
      data: {
        birthDate: cattle.birthYmd || null,
        gender: cattle.sexNm || null,
        breed: cattle.lsTypeNm || 'Hanwoo',
        farmAddr: cattle.farmAddr || null,
      },
    };
  } catch (error) {
    if (isTimeoutError(error)) {
      return {
        success: false,
        message: 'MTRACE lookup timed out. Please try again.',
      };
    }

    console.error('MTRACE API error:', error);
    return {
      success: false,
      message: 'An error occurred while looking up the cattle tag.',
    };
  }
}
