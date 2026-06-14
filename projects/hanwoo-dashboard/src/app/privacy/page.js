import LegalDocumentLayout from "@/components/layout/LegalDocumentLayout";

export const metadata = {
	title: "개인정보처리방침 · Joolife 한우",
	description: "주라이프 한우 농장 관리 서비스가 수집·이용·보관하는 개인정보 항목과 처리 기준을 안내합니다.",
};

const sections = [
	{
		title: "1. 개인정보의 처리 목적",
		body: [
			'주라이프(이하 "회사")는 회원 가입 및 관리, 서비스 제공, 결제 처리, 고객 문의 대응을 위해 필요한 최소한의 개인정보를 처리합니다.',
			"수집한 정보는 서비스 제공 목적 범위 안에서만 사용하며, 목적이 변경되는 경우 관련 법령에 따라 별도의 동의를 받습니다.",
			"비밀번호는 단방향 암호화(bcrypt)로 저장하며, 회사도 원문을 확인할 수 없습니다.",
		],
	},
	{
		title: "2. 처리하는 개인정보 항목",
		list: [
			"필수 항목: 아이디(사용자명), 비밀번호(해시 저장), 서비스 이용 기록",
			"선택 항목: 농장명, 농장 위치(지역), 사육 개체 정보, 결제 관련 정보(결제 식별자, 결제 금액)",
			"자동 수집: 접속 IP, 서비스 이용 일시 (로그 한정)",
		],
	},
	{
		title: "3. 개인정보 보유 및 이용 기간",
		body: [
			"회사는 법령에 따른 보관 의무가 있는 경우를 제외하고, 개인정보 수집 및 이용 목적이 달성된 후 지체 없이 해당 정보를 파기합니다.",
			"회원 탈퇴 요청이 있는 경우에도 관련 분쟁 또는 법적 의무가 있는 기간 동안은 필요한 범위에서 보관할 수 있습니다.",
		],
	},
	{
		title: "4. 개인정보 보호책임자",
		list: [
			"담당: Joolife 운영팀",
			"이메일: joolife@joolife.io.kr",
			"문의 채널: 서비스 운영 문의",
		],
	},
];

export default function PrivacyPage() {
	return (
		<LegalDocumentLayout
			eyebrow="개인정보 보호 안내"
			title="개인정보처리방침"
			subtitle="회원 정보의 수집, 이용, 보관 및 보호 기준을 투명하게 안내합니다."
			lastUpdated="시행일 2026년 2월 10일"
		>
			{sections.map((section) => (
				<section key={section.title} className="clay-page-section p-5 md:p-6">
					<h2 className="mb-3 text-xl font-bold text-[color:var(--color-text)]">
						{section.title}
					</h2>
					{section.body?.map((paragraph) => (
						<p
							key={paragraph}
							className="mb-3 text-sm leading-7 text-[color:var(--color-text-secondary)] last:mb-0"
						>
							{paragraph}
						</p>
					))}
					{section.list?.length ? (
						<ul className="m-0 grid gap-2 pl-5 text-sm leading-7 text-[color:var(--color-text-secondary)]">
							{section.list.map((item) => (
								<li key={item}>{item}</li>
							))}
						</ul>
					) : null}
				</section>
			))}
		</LegalDocumentLayout>
	);
}
