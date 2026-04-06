import DiagnosticsPageClient from '@/components/admin/DiagnosticsPageClient';
import { requireAuthenticatedSession } from '@/lib/auth-guard';

export const dynamic = 'force-dynamic';

export default async function DiagnosticsPage() {
  await requireAuthenticatedSession({ redirectToLogin: true });
  return <DiagnosticsPageClient />;
}
