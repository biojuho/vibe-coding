import { NextResponse } from 'next/server';

import { requireAuthenticatedSession, isAuthenticationError } from '@/lib/auth-guard';
import {
  DashboardQueryValidationError,
  getSalesListPage,
  parseSalesListQuery,
} from '@/lib/dashboard/list-queries';

export const dynamic = 'force-dynamic';

export async function GET(request) {
  try {
    await requireAuthenticatedSession();

    const { searchParams } = new URL(request.url);
    const query = parseSalesListQuery(searchParams);
    const data = await getSalesListPage({
      from: query.from,
      to: query.to,
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

    console.error('Dashboard sales route error:', error);
    return NextResponse.json(
      { success: false, message: error.message || 'Failed to load sales list.' },
      { status: 500 },
    );
  }
}
