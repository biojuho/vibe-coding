import DiagnosticsPageClient from "@/components/admin/DiagnosticsPageClient";
import { requireAdminSession } from "@/lib/auth-guard";

export const metadata = {
	title: "진단 · Joolife 한우 관리자",
	description: "Joolife 한우 대시보드 시스템 진단 및 관리자 도구",
};

export default async function DiagnosticsPage() {
	await requireAdminSession({ redirectToLogin: true, redirectToHome: true });
	return <DiagnosticsPageClient />;
}
