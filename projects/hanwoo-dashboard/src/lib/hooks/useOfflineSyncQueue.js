"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { queueSize } from "@/lib/offlineQueue";
import { syncOfflineQueue } from "@/lib/syncManager";

const OFFLINE_SYNC_REFRESH_ERROR_MESSAGE =
	"동기화 결과를 보려면 화면을 새로고침해 주세요.";

export function useOfflineSyncQueue(isOnline, notify) {
	const router = useRouter();

	useEffect(() => {
		if (!isOnline || queueSize() === 0) {
			return undefined;
		}

		let cancelled = false;

		void (async () => {
			try {
				const { synced, failed, deadLettered, reused } =
					await syncOfflineQueue();
				if (cancelled || reused || (synced === 0 && deadLettered === 0 && failed === 0)) {
					return;
				}
				notify({
					title:
						failed > 0
							? "오프라인 작업을 일부 동기화했습니다."
							: "오프라인 작업 동기화가 완료되었습니다.",
					description:
						failed > 0
							? `${synced}건은 반영되었고 ${failed}건은 다시 시도해 주세요.`
							: `${synced}건이 서버에 반영되었습니다.`,
					variant: failed > 0 ? "warning" : "success",
				});
				if (synced > 0) {
					try {
						router.refresh();
					} catch (refreshError) {
						console.error("Offline queue refresh failed:", refreshError);
						notify({
							title: "동기화 후 화면 새로고침에 실패했습니다.",
							description: OFFLINE_SYNC_REFRESH_ERROR_MESSAGE,
							variant: "warning",
						});
					}
				}
			} catch (error) {
				if (cancelled) {
					return;
				}
				console.error("Offline queue sync failed:", error);
				notify({
					title: "오프라인 작업 동기화에 실패했습니다.",
					description: "잠시 후 다시 시도해 주세요.",
					variant: "warning",
				});
			}
		})();

		return () => {
			cancelled = true;
		};
	}, [isOnline, notify, router]);
}
