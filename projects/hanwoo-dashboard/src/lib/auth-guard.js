import { redirect } from "next/navigation";
import { auth } from "@/auth";

export const AUTHENTICATION_REQUIRED_MESSAGE = "로그인이 필요합니다.";

export class AuthenticationError extends Error {
	constructor(message = AUTHENTICATION_REQUIRED_MESSAGE) {
		super(message);
		this.name = "AuthenticationError";
	}
}

function normalizeObject(value) {
	return value && typeof value === "object" && !Array.isArray(value)
		? value
		: {};
}

export async function requireAuthenticatedSession(options = {}) {
	const { redirectToLogin = false } = normalizeObject(options);

	let session;
	try {
		session = await auth();
	} catch (infraError) {
		// When the backing store (DB) is unreachable, treat as unauthenticated
		// rather than surfacing an infrastructure error to the caller.
		throw new AuthenticationError();
	}

	if (!session?.user?.id) {
		if (redirectToLogin) {
			redirect("/login");
		}
		throw new AuthenticationError();
	}

	return session;
}

export function isAuthenticationError(error) {
	return (
		error instanceof AuthenticationError ||
		error?.name === "AuthenticationError"
	);
}

export class AdminAuthorizationError extends Error {
	constructor(message = "관리자 권한이 필요합니다.") {
		super(message);
		this.name = "AdminAuthorizationError";
	}
}

function normalizeAdminOptions(value) {
	return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

export async function requireAdminSession(options = {}) {
	const { redirectToLogin = false, redirectToHome = false } = normalizeAdminOptions(options);

	const session = await requireAuthenticatedSession({ redirectToLogin });

	const isDev = process.env.NODE_ENV === "development";
	if (!isDev) {
		const adminUsernames = (process.env.ADMIN_USERNAMES ?? "")
			.split(",")
			.map((s) => s.trim())
			.filter(Boolean);
		const username = session.user?.name ?? "";
		if (!adminUsernames.includes(username)) {
			if (redirectToHome) {
				const { redirect } = await import("next/navigation");
				redirect("/");
			}
			throw new AdminAuthorizationError();
		}
	}

	return session;
}
