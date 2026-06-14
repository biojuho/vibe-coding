import "server-only";
import prisma from "@/lib/db";

export async function getSubscriptionStatus(userId) {
	if (!userId) return { status: "INACTIVE", daysLeft: null };

	const sub = await prisma.subscription.findFirst({
		where: { userId },
		orderBy: { createdAt: "desc" },
	});

	if (!sub) return { status: "INACTIVE", daysLeft: null };

	if (sub.status === "ACTIVE") {
		const daysLeft = sub.nextPaymentDate
			? Math.max(0, Math.ceil((new Date(sub.nextPaymentDate) - new Date()) / 86400000))
			: null;
		return { status: "ACTIVE", daysLeft, nextPaymentDate: sub.nextPaymentDate };
	}

	if (sub.status === "TRIAL" && sub.trialEndDate) {
		const daysLeft = Math.ceil((new Date(sub.trialEndDate) - new Date()) / 86400000);
		if (daysLeft > 0) {
			return { status: "TRIAL", daysLeft, trialEndDate: sub.trialEndDate };
		}
		return { status: "INACTIVE", daysLeft: 0 };
	}

	return { status: "INACTIVE", daysLeft: null };
}
