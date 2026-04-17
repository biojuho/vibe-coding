'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { queueSize } from '@/lib/offlineQueue';
import { syncOfflineQueue } from '@/lib/syncManager';

export function useOfflineSyncQueue(isOnline, notify) {
  const router = useRouter();

  useEffect(() => {
    if (!isOnline || queueSize() === 0) {
      return undefined;
    }

    let cancelled = false;

    void (async () => {
      try {
        const { synced, failed, deadLettered, reused } = await syncOfflineQueue();
        if (cancelled || reused || (synced === 0 && deadLettered === 0)) {
          return;
        }
        notify({
          title: failed > 0 ? '오프라인 작업을 일부 동기화했습니다.' : '오프라인 작업 동기화가 완료되었습니다.',
          description:
            failed > 0
              ? `${synced}건은 반영되었고 ${failed}건은 다시 시도해 주세요.`
              : `${synced}건이 서버에 반영되었습니다.`,
          variant: failed > 0 ? 'warning' : 'success',
        });
        if (synced > 0) {
          router.refresh();
        }
      } catch (error) {
        if (cancelled) {
          return;
        }
        console.error('Offline queue sync failed:', error);
        notify({
          title: '오프라인 작업 동기화에 실패했습니다.',
          description: '잠시 후 다시 시도해주세요.',
          variant: 'warning',
        });
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [isOnline, notify, router]);
}
