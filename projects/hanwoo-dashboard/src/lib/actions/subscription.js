"use server";

import { requireAuthenticatedSession } from "@/lib/auth-guard";
import { redirect } from "next/navigation";
import { prisma } from "./_helpers";

export async function cancelSubscription() {
	const session = await requireAuthenticatedSession({ redirectToLogin: true });
	const userId = session.user.id;

	let sub;
	try {
		sub = await prisma.subscription.findFirst({
			where: { userId, status: "ACTIVE" },
			orderBy: { createdAt: "desc" },
		});
	} catch (err) {
		console.error("cancelSubscription: subscription lookup failed:", err);
		return { ok: false, message: "구독 정보를 조회할 수 없습니다. 잠시 후 다시 시도해 주세요." };
	}

	if (!sub) {
		redirect("/subscription?cancel=not_found");
	}

	try {
		await prisma.subscription.update({
			where: { id: sub.id },
			data: { status: "INACTIVE" },
		});
	} catch (err) {
		console.error("cancelSubscription: subscription update failed:", err);
		return { ok: false, message: "구독 해지 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요." };
	}

	redirect("/subscription?cancel=success");
}
