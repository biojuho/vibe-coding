import { NextResponse } from "next/server";

import {
  applyDashboardSession,
  clearDashboardSession,
  getDashboardApiKey,
  isDashboardRequestAuthorized,
} from "@/lib/dashboard-auth";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  const validKey = getDashboardApiKey();
  if (!validKey) {
    return NextResponse.json({ error: "Dashboard API key is not configured" }, { status: 503 });
  }

  const payload = await request.json().catch(() => null);
  const apiKey = typeof payload?.apiKey === "string" ? payload.apiKey.trim() : "";

  if (apiKey !== validKey) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  return applyDashboardSession(NextResponse.json({ ok: true }), validKey);
}

export async function DELETE() {
  return clearDashboardSession(NextResponse.json({ ok: true }));
}

export async function GET(request: import("next/server").NextRequest) {
  const auth = isDashboardRequestAuthorized(request);
  if (!auth.ok) {
    return NextResponse.json({ authenticated: false }, { status: auth.status });
  }

  return NextResponse.json({ authenticated: true });
}
