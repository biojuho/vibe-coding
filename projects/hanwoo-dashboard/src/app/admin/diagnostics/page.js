import DiagnosticsPageClient from '@/components/admin/DiagnosticsPageClient';
import { requireAuthenticatedSession } from '@/lib/auth-guard';


export default async function DiagnosticsPage() {
  await requireAuthenticatedSession({ redirectToLogin: true });
  return <DiagnosticsPageClient />;
}
