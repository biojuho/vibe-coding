'use server';

import { requireAuthenticatedSession } from '@/lib/auth-guard';
import { fetchMarketPrice } from '../kape';
import {
  getLatestMarketPriceSnapshot,
  saveMarketPriceSnapshot,
} from '../dashboard/read-models';
import {
  buildUnavailableMarketPrice,
  normalizeCachedMarketPrice,
  normalizeLiveMarketPrice,
  shouldPersistLiveMarketPrice,
} from '../market-price-state.mjs';
import { createOutboxEvent, DASHBOARD_EVENT_TOPICS } from './_helpers';

// ============================================================
// Market Actions
// ============================================================

export async function getRealTimeMarketPrice() {
  await requireAuthenticatedSession();
  let cachedMarketPrice = null;

  try {
    const cached = await getLatestMarketPriceSnapshot();
    cachedMarketPrice = normalizeCachedMarketPrice(cached);

    if (cached && !cachedMarketPrice) {
      console.warn('Ignoring non-authoritative market price snapshot.', {
        fetchedAt: cached.fetchedAt,
        isRealtime: cached.isRealtime,
        source: cached.source,
      });
    }

    if (cachedMarketPrice && !cachedMarketPrice.isStale) {
      return cachedMarketPrice;
    }
  } catch (err) {
    console.error('Market price cache read failed (falling back to API):', err);
  }

  const marketPrice = normalizeLiveMarketPrice(await fetchMarketPrice());

  if (shouldPersistLiveMarketPrice(marketPrice)) {
    try {
      await saveMarketPriceSnapshot({
        issueDate: marketPrice.issueDate,
        isRealtime: true,
        bull: marketPrice.bull,
        cow: marketPrice.cow,
        source: 'KAPE',
      });
      await createOutboxEvent({
        topic: DASHBOARD_EVENT_TOPICS.marketPriceRefreshed,
        payload: { issueDate: marketPrice.issueDate, source: marketPrice.source },
      });
    } catch (err) {
      console.error('Market price snapshot save failed:', err);
    }

    return marketPrice;
  }

  if (cachedMarketPrice) {
    return cachedMarketPrice;
  }

  return buildUnavailableMarketPrice();
}
