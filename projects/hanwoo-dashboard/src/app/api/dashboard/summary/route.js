import { NextResponse } from 'next/server';

import { requireAuthenticatedSession, isAuthenticationError } from '@/lib/auth-guard';
import { DASHBOARD_CACHE_TTLS } from '@/lib/dashboard/cache';
import { getDashboardSummarySnapshot, saveDashboardSummarySnapshot } from '@/lib/dashboard/read-models';
import { buildDashboardSummaryPayload } from '@/lib/dashboard/summary-service';
import prisma from '@/lib/db';

export const dynamic = 'force-dynamic';

function buildMeta(snapshot, source) {
  const generatedAt = new Date(snapshot.generatedAt);
  const staleAt = new Date(snapshot.staleAt);

  return {
    source,
    generatedAt: generatedAt.toISOString(),
    staleAt: staleAt.toISOString(),
    isStale: staleAt <= new Date(),
    ageSeconds: Math.max(0, Math.floor((Date.now() - generatedAt.getTime()) / 1000)),
  };
}

export async function GET(request) {
  try {
    await requireAuthenticatedSession();

    const { searchParams } = new URL(request.url);
    const forceFresh = searchParams.get('fresh') === '1';

    let snapshot = forceFresh
      ? null
      : await getDashboardSummarySnapshot('default');
    let source = 'snapshot';

    if (!snapshot || new Date(snapshot.staleAt) <= new Date()) {
      const payload = await buildDashboardSummaryPayload({ client: prisma });
      snapshot = await saveDashboardSummarySnapshot({
        farmId: 'default',
        payload,
        staleAt: new Date(Date.now() + DASHBOARD_CACHE_TTLS.summary * 1000),
      });
      source = snapshot ? 'rebuilt' : 'live';
    }

    return NextResponse.json({
      success: true,
      data: snapshot.payload,
      meta: buildMeta(snapshot, source),
    });
  } catch (error) {
    if (isAuthenticationError(error)) {
      return NextResponse.json({ success: false, message: error.message }, { status: 401 });
    }

    console.error('Dashboard summary route error:', error);
    return NextResponse.json(
      { success: false, message: error.message || 'Failed to load dashboard summary.' },
      { status: 500 },
    );
  }
}
