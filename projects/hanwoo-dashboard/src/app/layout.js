import "./globals.css";
import {
	Cormorant_Garamond,
	Noto_Sans_KR,
	Noto_Serif_KR,
} from "next/font/google";
import { Suspense } from "react";
import Providers from "@/components/Providers";

const notoSansKr = Noto_Sans_KR({
	weight: ["400", "500", "700"],
	variable: "--font-noto-sans-kr",
	display: "swap",
	preload: false,
});

const notoSerifKr = Noto_Serif_KR({
	weight: ["600", "700"],
	variable: "--font-noto-serif-kr",
	display: "swap",
	preload: false,
});

const cormorantGaramond = Cormorant_Garamond({
	subsets: ["latin"],
	weight: ["600", "700"],
	variable: "--font-cormorant-garamond",
	display: "swap",
});

export const metadata = {
	title: "Joolife 한우 농장 관리",
	description:
		"한우 농장의 개체, 번식, 출하, 재고, 일정을 한곳에서 관리하는 운영 대시보드",
	keywords: ["한우", "농장 관리", "축산", "개체 관리", "수익성 분석", "AI 인사이트"],
	manifest: "/manifest.json",
	openGraph: {
		type: "website",
		locale: "ko_KR",
		title: "Joolife 한우 | 한우 농장 관리 SaaS",
		description: "개체 관리, AI 인사이트, 수익성 분석, KAPE 시세 연동 — 한우 농장을 스마트하게 관리하세요.",
		siteName: "Joolife 한우",
	},
	twitter: {
		card: "summary",
		title: "Joolife 한우 | 한우 농장 관리 SaaS",
		description: "개체 관리, AI 인사이트, 수익성 분석, KAPE 시세 연동",
	},
	appleWebApp: {
		capable: true,
		statusBarStyle: "black-translucent",
		title: "Joolife 한우",
	},
};

export const viewport = {
	width: "device-width",
	initialScale: 1,
	maximumScale: 5,
	themeColor: [
		{ media: "(prefers-color-scheme: light)", color: "#3E2F1C" },
		{ media: "(prefers-color-scheme: dark)", color: "#1a1814" },
	],
};

function normalizeRootLayoutOptions(options) {
	return options && typeof options === "object" && !Array.isArray(options)
		? options
		: {};
}

export default function RootLayout(options = {}) {
	const { children } = normalizeRootLayoutOptions(options);

	return (
		<html lang="ko" data-scroll-behavior="smooth" suppressHydrationWarning>
			<body
				className={`${notoSansKr.variable} ${notoSerifKr.variable} ${cormorantGaramond.variable}`}
			>
				<a href="#main-content" className="skip-to-main">
					본문으로 건너뛰기
				</a>
				<Providers>
					<Suspense>{children}</Suspense>
				</Providers>
			</body>
		</html>
	);
}
