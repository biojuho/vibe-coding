import { NextResponse } from "next/server";
import { requireAuthenticatedSession } from "@/lib/auth-guard";
import { checkRateLimit } from "@/lib/rate-limit.mjs";

const MIN_PASSWORD_LENGTH = 8;

function validateChangePasswordPayload(body) {
	const currentPassword =
		typeof body?.currentPassword === "string" ? body.currentPassword : "";
	const newPassword =
		typeof body?.newPassword === "string" ? body.newPassword : "";

	if (!currentPassword) {
		return { error: "현재 비밀번호를 입력해 주세요." };
	}
	if (newPassword.length < MIN_PASSWORD_LENGTH) {
		return { error: `새 비밀번호는 최소 ${MIN_PASSWORD_LENGTH}자 이상이어야 합니다.` };
	}
	if (currentPassword === newPassword) {
		return { error: "새 비밀번호는 현재 비밀번호와 달라야 합니다." };
	}

	return { currentPassword, newPassword };
}

export async function POST(request) {
	let session;
	try {
		session = await requireAuthenticatedSession();
	} catch {
		return NextResponse.json(
			{ error: "로그인이 필요합니다." },
			{ status: 401 },
		);
	}

	if (session.user?.id) {
		const rateResult = checkRateLimit(`change-password:${session.user.id}`, { maxRequests: 5, windowMs: 3600000 });
		if (!rateResult.allowed) {
			return NextResponse.json(
				{ error: "요청이 너무 많습니다. 잠시 후 다시 시도해 주세요." },
				{ status: 429, headers: { "Retry-After": String(rateResult.retryAfterSeconds ?? 3600) } },
			);
		}
	}

	let body;
	try {
		body = await request.json();
	} catch {
		return NextResponse.json(
			{ error: "요청 형식이 올바르지 않습니다." },
			{ status: 400 },
		);
	}

	const validated = validateChangePasswordPayload(body);
	if (validated.error) {
		return NextResponse.json({ error: validated.error }, { status: 400 });
	}

	const { currentPassword, newPassword } = validated;

	try {
		const { default: prisma } = await import("@/lib/db");
		const { default: bcrypt } = await import("bcrypt");

		const user = await prisma.user.findUnique({
			where: { id: session.user.id },
		});
		if (!user) {
			return NextResponse.json(
				{ error: "사용자를 찾을 수 없습니다." },
				{ status: 404 },
			);
		}

		const isCurrentPasswordValid = await bcrypt.compare(currentPassword, user.password);
		if (!isCurrentPasswordValid) {
			return NextResponse.json(
				{ error: "현재 비밀번호가 올바르지 않습니다." },
				{ status: 400 },
			);
		}

		const hashedNewPassword = await bcrypt.hash(newPassword, 12);
		await prisma.user.update({
			where: { id: session.user.id },
			data: { password: hashedNewPassword },
		});

		return NextResponse.json({ ok: true });
	} catch {
		return NextResponse.json(
			{ error: "비밀번호 변경 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요." },
			{ status: 500 },
		);
	}
}
