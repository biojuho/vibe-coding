import { NextResponse } from 'next/server';

import { requireAuthenticatedSession, isAuthenticationError } from '@/lib/auth-guard';
import {
  DashboardQueryValidationError,
  getCattleListPage,
  parseCattleListQuery,
} from '@/lib/dashboard/list-queries';

export const dynamic = 'force-dynamic';

export async function GET(request) {
  try {
    await requireAuthenticatedSession();

    const { searchParams } = new URL(request.url);
    const query = parseCattleListQuery(searchParams);
    const data = await getCattleListPage({
      buildingId: query.buildingId,
      penNumber: query.penNumber,
      status: query.status,
      cursor: query.cursor,
      limit: query.limit,
      bypassCache: query.fresh,
    });

    return NextResponse.json({
      success: true,
      data,
    });
  } catch (error) {
    if (isAuthenticationError(error)) {
      return NextResponse.json({ success: false, message: error.message }, { status: 401 });
    }

    if (error instanceof DashboardQueryValidationError) {
      return NextResponse.json({ success: false, message: error.message }, { status: 400 });
    }

    console.error('Dashboard cattle route error:', error);
    return NextResponse.json(
      { success: false, message: error.message || 'Failed to load cattle list.' },
      { status: 500 },
    );
  }
}
