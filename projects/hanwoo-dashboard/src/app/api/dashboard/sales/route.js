import { NextResponse } from 'next/server';

import {
  AUTHENTICATION_REQUIRED_MESSAGE,
  requireAuthenticatedSession,
  isAuthenticationError,
} from '@/lib/auth-guard';
import {
  DashboardQueryValidationError,
  getSalesListPage,
  parseSalesListQuery,
} from '@/lib/dashboard/list-queries';

const SALES_LIST_ERROR_MESSAGE = '판매 기록을 불러오지 못했습니다.';
const SALES_LIST_VALIDATION_ERROR_MESSAGE = '판매 기록 조회 조건을 확인해 주세요.';

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
      return NextResponse.json({ success: false, message: AUTHENTICATION_REQUIRED_MESSAGE }, { status: 401 });
    }

    if (error instanceof DashboardQueryValidationError) {
      return NextResponse.json({ success: false, message: SALES_LIST_VALIDATION_ERROR_MESSAGE }, { status: 400 });
    }

    console.error('Dashboard sales route error:', error);
    return NextResponse.json(
      { success: false, message: SALES_LIST_ERROR_MESSAGE },
      { status: 500 },
    );
  }
}
