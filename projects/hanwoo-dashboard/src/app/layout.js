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
	metadataBase: new URL(
		process.env.NEXTAUTH_URL || process.env.AUTH_URL || "https://hanwoo.joolife.com",
	),
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
		images: [{ url: "/icon-512x512.png", width: 512, height: 512, alt: "Joolife 한우 농장 관리" }],
	},
	twitter: {
		card: "summary",
		title: "Joolife 한우 | 한우 농장 관리 SaaS",
		description: "개체 관리, AI 인사이트, 수익성 분석, KAPE 시세 연동",
		images: ["/icon-512x512.png"],
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

const SCHEMA_ORG_APP = {
	"@context": "https://schema.org",
	"@type": "SoftwareApplication",
	name: "Joolife 한우 농장 관리",
	applicationCategory: "BusinessApplication",
	operatingSystem: "Web Browser",
	inLanguage: "ko-KR",
	url: "https://hanwoo.joolife.com",
	description:
		"한우 농장의 개체, 번식, 출하, 재고, 일정을 한곳에서 관리하는 운영 대시보드",
	offers: [
		{
			"@type": "Offer",
			price: "0",
			priceCurrency: "KRW",
			description: "14일 무료 체험 (카드 등록 불필요)",
			eligibleCustomerType: "NewCustomer",
		},
		{
			"@type": "Offer",
			price: "9900",
			priceCurrency: "KRW",
			description: "프리미엄 월 구독 — AI 인사이트, 수익성 분석, 엑셀 내보내기",
			billingIncrement: "P1M",
		},
	],
};

export default function RootLayout(options = {}) {
	const { children } = normalizeRootLayoutOptions(options);

	return (
		<html lang="ko" data-scroll-behavior="smooth" suppressHydrationWarning>
			<head>
				<script
					type="application/ld+json"
					dangerouslySetInnerHTML={{ __html: JSON.stringify(SCHEMA_ORG_APP) }}
				/>
			</head>
			<body
				className={`${notoSansKr.variable} ${notoSerifKr.variable} ${cormorantGaramond.variable}`}
			>
				<noscript>
					<div
						style={{
							padding: "40px 20px",
							textAlign: "center",
							fontFamily: "sans-serif",
							color: "#666",
						}}
					>
						<strong>JavaScript가 필요합니다.</strong> 이 서비스를 이용하려면 브라우저에서 JavaScript를 활성화해 주세요.
					</div>
				</noscript>
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
