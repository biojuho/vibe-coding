import path from "node:path";

import { type NextRequest, NextResponse } from "next/server";

import { isDashboardRequestAuthorized } from "@/lib/dashboard-auth";
import { readJsonFileResult } from "@/lib/dashboard-data";

export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
	const auth = isDashboardRequestAuthorized(request);
	if (!auth.ok) {
		if (auth.status === 503) {
			console.error("DASHBOARD_API_KEY is not configured.");
		}
		return NextResponse.json({ error: auth.message }, { status: auth.status });
	}

	const result = await readJsonFileResult(
		path.join(process.cwd(), "data", "skill_lint.json"),
		"Skill lint data not found",
	);

	if (result.status === 200) {
		return NextResponse.json(result.data);
	}
	return NextResponse.json({ error: result.error }, { status: result.status });
}
