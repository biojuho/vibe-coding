import { NextResponse } from "next/server";
import { requireAuthenticatedSession } from "@/lib/auth-guard";
import { validateChangePasswordPayload } from "@/lib/auth-validation.mjs";
import { checkRateLimit } from "@/lib/rate-limit.mjs";

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
		const rateResult = checkRateLimit(`change-password:${session.user.id}`, {
			maxRequests: 5,
			windowMs: 3600000,
		});
		if (!rateResult.allowed) {
			return NextResponse.json(
				{ error: "요청이 너무 많습니다. 잠시 후 다시 시도해 주세요." },
				{
					status: 429,
					headers: {
						"Retry-After": String(rateResult.retryAfterSeconds ?? 3600),
					},
				},
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

		const isCurrentPasswordValid = await bcrypt.compare(
			currentPassword,
			user.password,
		);
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
			{
				error:
					"비밀번호 변경 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
			},
			{ status: 500 },
		);
	}
}
