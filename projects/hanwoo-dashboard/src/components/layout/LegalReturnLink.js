"use client";

import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { getSafeLoginRedirectTarget } from "@/lib/login-redirect.mjs";

const LEGAL_RETURN_TARGETS = {
	dashboard: {
		href: "/",
		requiresDocumentNavigation: true,
		label: "대시보드로 돌아가기",
	},
	login: {
		href: "/login",
		label: "로그인 화면으로 돌아가기",
	},
};

function buildLoginReturnHref(callbackTarget = "") {
	if (
		typeof callbackTarget !== "string" ||
		callbackTarget.length === 0 ||
		callbackTarget === "/"
	) {
		return LEGAL_RETURN_TARGETS.login.href;
	}

	const params = new URLSearchParams();
	params.set("callbackUrl", callbackTarget);
	return `${LEGAL_RETURN_TARGETS.login.href}?${params.toString()}#login`;
}

function resolveLegalLoginReturnTarget(searchParams, locationHref = "") {
	const callbackUrl = searchParams?.get("callbackUrl");
	if (!callbackUrl) {
		return LEGAL_RETURN_TARGETS.login;
	}

	try {
		const currentUrl = new URL(locationHref || "http://localhost");
		const loginUrl = new URL(LEGAL_RETURN_TARGETS.login.href, currentUrl.origin);
		loginUrl.searchParams.set("callbackUrl", callbackUrl);
		const redirectTarget = getSafeLoginRedirectTarget(loginUrl.href);
		if (!redirectTarget || redirectTarget === "/") {
			return LEGAL_RETURN_TARGETS.login;
		}

		return {
			...LEGAL_RETURN_TARGETS.login,
			href: buildLoginReturnHref(redirectTarget),
		};
	} catch {
		return LEGAL_RETURN_TARGETS.login;
	}
}

function resolveLegalReturnTarget(searchParams, locationHref = "") {
	const returnTo = searchParams?.get("returnTo");
	return returnTo === "dashboard"
		? LEGAL_RETURN_TARGETS.dashboard
		: resolveLegalLoginReturnTarget(searchParams, locationHref);
}

function LegalReturnAnchor({ href, label, requiresDocumentNavigation = false }) {
	if (requiresDocumentNavigation) {
		// Dashboard legal return must use document navigation so auth proxy redirect fragments are preserved.
		return (
			<a
				href={href}
				aria-label={label}
				title={label}
				className="clay-pressable inline-flex items-center gap-2 rounded-full px-5 py-3 text-sm font-semibold text-[color:var(--color-text)] no-underline"
			>
				<ArrowLeft className="h-4 w-4" aria-hidden="true" />
				{label}
			</a>
		);
	}

	return (
		<Link
			href={href}
			aria-label={label}
			title={label}
			className="clay-pressable inline-flex items-center gap-2 rounded-full px-5 py-3 text-sm font-semibold text-[color:var(--color-text)] no-underline"
		>
			<ArrowLeft className="h-4 w-4" aria-hidden="true" />
			{label}
		</Link>
	);
}

export function LegalReturnLinkFallback() {
	return <LegalReturnAnchor {...LEGAL_RETURN_TARGETS.login} />;
}

export { resolveLegalReturnTarget };

export default function LegalReturnLink() {
	const searchParams = useSearchParams();
	const locationHref = typeof window === "undefined" ? "" : window.location.href;
	return (
		<LegalReturnAnchor
			{...resolveLegalReturnTarget(searchParams, locationHref)}
		/>
	);
}
