import { NextResponse } from "next/server";

import {
	AUTHENTICATION_REQUIRED_MESSAGE,
	isAuthenticationError,
	requireAuthenticatedSession,
} from "@/lib/auth-guard";
import { DASHBOARD_CACHE_TTLS } from "@/lib/dashboard/cache";
import {
	getDashboardSummarySnapshot,
	saveDashboardSummarySnapshot,
} from "@/lib/dashboard/read-models";
import { buildDashboardSummaryPayload } from "@/lib/dashboard/summary-service";
import prisma from "@/lib/db";

const DASHBOARD_SUMMARY_ERROR_MESSAGE = "대시보드 요약을 불러오지 못했습니다.";

function toMetaDate(value, fallback = new Date()) {
	const date =
		value instanceof Date ? new Date(value.getTime()) : new Date(value);
	return Number.isNaN(date.getTime()) ? fallback : date;
}

function buildMeta(snapshot, source) {
	const fallback = new Date();
	const generatedAt = toMetaDate(snapshot.generatedAt, fallback);
	const staleAt = toMetaDate(snapshot.staleAt, fallback);

	return {
		source,
		generatedAt: generatedAt.toISOString(),
		staleAt: staleAt.toISOString(),
		isStale: staleAt <= new Date(),
		ageSeconds: Math.max(
			0,
			Math.floor((Date.now() - generatedAt.getTime()) / 1000),
		),
	};
}

export async function GET(request) {
	try {
		await requireAuthenticatedSession();

		const { searchParams } = new URL(request.url);
		const forceFresh = searchParams.get("fresh") === "1";

		let snapshot = forceFresh
			? null
			: await getDashboardSummarySnapshot("default");
		let source = "snapshot";
		let freshPayload = null;

		if (!snapshot || toMetaDate(snapshot.staleAt) <= new Date()) {
			freshPayload = await buildDashboardSummaryPayload({ client: prisma });
			snapshot = await saveDashboardSummarySnapshot({
				farmId: "default",
				payload: freshPayload,
				staleAt: new Date(Date.now() + DASHBOARD_CACHE_TTLS.summary * 1000),
			});
			source = snapshot ? "rebuilt" : "live";
		}

		// HW-DSR001: saveDashboardSummarySnapshot이 null 반환 시 freshPayload로 fallback
		const data = snapshot?.payload ?? freshPayload;
		const meta = snapshot
			? buildMeta(snapshot, source)
			: {
					source,
					generatedAt: new Date().toISOString(),
					staleAt: new Date().toISOString(),
					isStale: true,
					ageSeconds: 0,
				};

		return NextResponse.json(
			{ success: true, data, meta },
			{ headers: { "Cache-Control": "private, no-store" } },
		);
	} catch (error) {
		if (isAuthenticationError(error)) {
			return NextResponse.json(
				{ success: false, message: AUTHENTICATION_REQUIRED_MESSAGE },
				{ status: 401 },
			);
		}

		console.error("Dashboard summary route error:", error);
		return NextResponse.json(
			{ success: false, message: DASHBOARD_SUMMARY_ERROR_MESSAGE },
			{ status: 500 },
		);
	}
}
