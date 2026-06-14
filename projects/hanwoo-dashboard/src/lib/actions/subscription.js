"use server";

import { requireAuthenticatedSession } from "@/lib/auth-guard";
import { redirect } from "next/navigation";
import { prisma } from "./_helpers";

export async function cancelSubscription() {
	const session = await requireAuthenticatedSession({ redirectToLogin: true });
	const userId = session.user.id;

	const sub = await prisma.subscription.findFirst({
		where: { userId, status: "ACTIVE" },
		orderBy: { createdAt: "desc" },
	});

	if (!sub) {
		redirect("/subscription?cancel=not_found");
	}

	await prisma.subscription.update({
		where: { id: sub.id },
		data: { status: "INACTIVE" },
	});

	redirect("/subscription?cancel=success");
}
