import DiagnosticsPageClient from "@/components/admin/DiagnosticsPageClient";
import { requireAdminSession } from "@/lib/auth-guard";

export default async function DiagnosticsPage() {
	await requireAdminSession({ redirectToLogin: true, redirectToHome: true });
	return <DiagnosticsPageClient />;
}
