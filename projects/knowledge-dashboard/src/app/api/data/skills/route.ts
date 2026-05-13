import { readFile } from "node:fs/promises";
import path from "node:path";

import { NextResponse, type NextRequest } from "next/server";

import { isDashboardRequestAuthorized } from "@/lib/dashboard-auth";


export const dynamic = "force-dynamic";


export async function GET(request: NextRequest) {
  const auth = isDashboardRequestAuthorized(request);
  if (!auth.ok) {
    if (auth.status === 503) {
      console.error("DASHBOARD_API_KEY is not configured.");
    }
    return NextResponse.json({ error: auth.message }, { status: auth.status });
  }

  try {
    const dataPath = path.join(process.cwd(), "data", "skill_lint.json");
    const fileContents = await readFile(dataPath, "utf8");
    return NextResponse.json(JSON.parse(fileContents));
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") {
      return NextResponse.json({ error: "Skill lint data not found" }, { status: 404 });
    }

    console.error("Error reading skill lint data:", error);
    return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
  }
}
