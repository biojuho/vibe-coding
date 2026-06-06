import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";
import { NextResponse } from "next/server";
import { authorizeCredentials } from "@/lib/auth-credentials.mjs";

function firstHeaderValue(value) {
	return value?.split(",")[0]?.trim();
}

function getRequestOrigin(request) {
	const protocol =
		firstHeaderValue(request.headers.get("x-forwarded-proto")) ??
		request.nextUrl.protocol.replace(/:$/, "");
	const host =
		firstHeaderValue(request.headers.get("x-forwarded-host")) ??
		firstHeaderValue(request.headers.get("host"));

	if (!host) {
		return request.nextUrl.origin;
	}

	return `${protocol}://${host}`;
}

function getRequestHref(request, origin) {
	return new URL(`${request.nextUrl.pathname}${request.nextUrl.search}`, origin)
		.href;
}

export const { handlers, signIn, signOut, auth } = NextAuth({
	providers: [
		Credentials({
			credentials: {
				username: { label: "Username", type: "text" },
				password: { label: "Password", type: "password" },
			},
			authorize: authorizeCredentials,
		}),
	],
	session: { strategy: "jwt" },
	pages: {
		signIn: "/login",
	},
	callbacks: {
		session({ session, token }) {
			if (token?.sub) {
				session.user.id = token.sub;
			}
			return session;
		},
		authorized({ auth, request }) {
			if (auth?.user) {
				return true;
			}
			const requestOrigin = getRequestOrigin(request);
			const loginUrl = new URL("/login", requestOrigin);
			loginUrl.searchParams.set(
				"callbackUrl",
				getRequestHref(request, requestOrigin),
			);
			return NextResponse.redirect(loginUrl);
		},
	},
});
