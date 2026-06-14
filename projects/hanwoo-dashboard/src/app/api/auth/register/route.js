import { NextResponse } from "next/server";

const MIN_USERNAME_LENGTH = 3;
const MAX_USERNAME_LENGTH = 30;
const MIN_PASSWORD_LENGTH = 8;
const USERNAME_PATTERN = /^[a-z0-9_]+$/;

function validateRegistrationPayload(body) {
	const username =
		typeof body?.username === "string" ? body.username.trim() : "";
	const password =
		typeof body?.password === "string" ? body.password : "";

	if (username.length < MIN_USERNAME_LENGTH || username.length > MAX_USERNAME_LENGTH) {
		return {
			error: `아이디는 ${MIN_USERNAME_LENGTH}~${MAX_USERNAME_LENGTH}자여야 합니다.`,
		};
	}
	if (!USERNAME_PATTERN.test(username)) {
		return { error: "아이디는 영문 소문자, 숫자, 밑줄(_)만 사용할 수 있습니다." };
	}
	if (password.length < MIN_PASSWORD_LENGTH) {
		return { error: `비밀번호는 최소 ${MIN_PASSWORD_LENGTH}자 이상이어야 합니다.` };
	}

	return { username, password };
}

export async function POST(request) {
	let body;
	try {
		body = await request.json();
	} catch {
		return NextResponse.json(
			{ error: "요청 형식이 올바르지 않습니다." },
			{ status: 400 },
		);
	}

	const validated = validateRegistrationPayload(body);
	if (validated.error) {
		return NextResponse.json({ error: validated.error }, { status: 400 });
	}

	const { username, password } = validated;

	try {
		const { default: prisma } = await import("@/lib/db");
		const { default: bcrypt } = await import("bcrypt");

		const existing = await prisma.user.findUnique({ where: { username } });
		if (existing) {
			return NextResponse.json(
				{ error: "이미 사용 중인 아이디입니다." },
				{ status: 409 },
			);
		}

		const { buildCustomerKey, addDays, TRIAL_DAYS } = await import("@/lib/subscription.js");

		const hashedPassword = await bcrypt.hash(password, 12);
		const user = await prisma.user.create({
			data: { username, password: hashedPassword },
		});

		// Auto-create a 14-day free trial for the new user
		try {
			await prisma.subscription.create({
				data: {
					userId: user.id,
					customerKey: buildCustomerKey(user.id),
					status: "TRIAL",
					trialEndDate: addDays(new Date(), TRIAL_DAYS),
				},
			});
		} catch {
			// Trial creation failure must not block registration
		}

		return NextResponse.json({ ok: true }, { status: 201 });
	} catch {
		return NextResponse.json(
			{ error: "회원가입 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요." },
			{ status: 500 },
		);
	}
}
