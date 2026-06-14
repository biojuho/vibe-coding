import { NextResponse } from "next/server";

import {
	AUTHENTICATION_REQUIRED_MESSAGE,
	isAuthenticationError,
	requireAuthenticatedSession,
} from "@/lib/auth-guard";
import {
	DashboardQueryValidationError,
	getSalesListPage,
	parseSalesListQuery,
} from "@/lib/dashboard/list-queries";
import { checkRateLimit } from "@/lib/rate-limit.mjs";

const SALES_LIST_ERROR_MESSAGE = "판매 기록을 불러오지 못했습니다.";
const SALES_LIST_VALIDATION_ERROR_MESSAGE =
	"판매 기록 조회 조건을 확인해 주세요.";

export async function GET(request) {
	try {
		const session = await requireAuthenticatedSession();

		if (session?.user?.id) {
			const rl = checkRateLimit(`dashboard-sales:${session.user.id}`, { maxRequests: 300, windowMs: 300000 });
			if (!rl.allowed) {
				return NextResponse.json(
					{ success: false, message: "요청이 너무 많습니다. 잠시 후 다시 시도해 주세요." },
					{ status: 429, headers: { "Retry-After": String(rl.retryAfterSeconds ?? 300) } },
				);
			}
		}

		const { searchParams } = new URL(request.url);
		const query = parseSalesListQuery(searchParams);
		const data = await getSalesListPage({
			from: query.from,
			to: query.to,
			cursor: query.cursor,
			limit: query.limit,
			bypassCache: query.fresh,
		});

		return NextResponse.json(
			{ success: true, data },
			{ headers: { "Cache-Control": "private, no-store" } },
		);
	} catch (error) {
		if (isAuthenticationError(error)) {
			return NextResponse.json(
				{ success: false, message: AUTHENTICATION_REQUIRED_MESSAGE },
				{ status: 401 },
			);
		}

		if (error instanceof DashboardQueryValidationError) {
			return NextResponse.json(
				{ success: false, message: SALES_LIST_VALIDATION_ERROR_MESSAGE },
				{ status: 400 },
			);
		}

		console.error("Dashboard sales route error:", error);
		return NextResponse.json(
			{ success: false, message: SALES_LIST_ERROR_MESSAGE },
			{ status: 500 },
		);
	}
}
