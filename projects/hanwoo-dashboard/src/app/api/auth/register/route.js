import bcrypt from "bcrypt";
import { NextResponse } from "next/server";
import { validateRegistrationPayload } from "@/lib/auth-validation.mjs";
import prisma from "@/lib/db";
import { checkRateLimit } from "@/lib/rate-limit.mjs";
import { addDays, buildCustomerKey, TRIAL_DAYS } from "@/lib/subscription.js";

export async function POST(request) {
	const ip =
		request.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ??
		request.headers.get("x-real-ip") ??
		"unknown";
	const rateLimitResult = checkRateLimit(`register:${ip}`, {
		maxRequests: 5,
		windowMs: 3600000,
	});
	if (!rateLimitResult.allowed) {
		return NextResponse.json(
			{ error: "너무 많은 요청이 발생했습니다. 잠시 후 다시 시도해 주세요." },
			{
				status: 429,
				headers: {
					"Retry-After": String(rateLimitResult.retryAfterSeconds ?? 3600),
				},
			},
		);
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

	const validated = validateRegistrationPayload(body);
	if (validated.error) {
		return NextResponse.json({ error: validated.error }, { status: 400 });
	}

	const { username, password } = validated;

	try {
		const existing = await prisma.user.findUnique({ where: { username } });
		if (existing) {
			return NextResponse.json(
				{ error: "이미 사용 중인 아이디입니다." },
				{ status: 409 },
			);
		}

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
		} catch (trialErr) {
			console.error(
				"register: trial subscription creation failed for user",
				user.id,
				trialErr,
			);
		}

		return NextResponse.json({ ok: true }, { status: 201 });
	} catch (err) {
		console.error("register: unexpected error during registration", err);
		return NextResponse.json(
			{
				error:
					"회원가입 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
			},
			{ status: 500 },
		);
	}
}
