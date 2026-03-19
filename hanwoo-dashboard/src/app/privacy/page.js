import LegalDocumentLayout from '@/components/layout/LegalDocumentLayout';

const sections = [
  {
    title: '1. 개인정보의 처리 목적',
    body: [
      '주라이프(이하 "회사")는 회원 가입 및 관리, 서비스 제공, 고객 문의 대응을 위해 필요한 최소한의 개인정보를 처리합니다.',
      '수집한 정보는 서비스 제공 목적 범위 안에서만 사용하며, 목적이 변경되는 경우 관련 법령에 따라 별도의 동의를 받습니다.',
    ],
  },
  {
    title: '2. 처리하는 개인정보 항목',
    list: [
      '필수 항목: 이름, 연락처, 이메일 주소, 로그인 정보',
      '선택 항목: 농장 주소, 사육 두수, 서비스 이용 기록',
    ],
  },
  {
    title: '3. 개인정보 보유 및 이용 기간',
    body: [
      '회사는 법령에 따른 보관 의무가 있는 경우를 제외하고, 개인정보 수집 및 이용 목적이 달성된 후 지체 없이 해당 정보를 파기합니다.',
      '회원 탈퇴 요청이 있는 경우에도 관련 분쟁 또는 법적 의무가 있는 기간 동안은 필요한 범위에서 보관할 수 있습니다.',
    ],
  },
  {
    title: '4. 개인정보 보호책임자',
    list: [
      '성명: 박주호',
      '직책: 대표',
      '연락처: 010-3159-3708 / joolife@joolife.io.kr',
      '주소: 경기도 안양시 동안구 관평로212번길 21 공작부영아파트 309동 1312호',
    ],
  },
];

export default function PrivacyPage() {
  return (
    <LegalDocumentLayout
      eyebrow="Privacy Policy"
      title="개인정보처리방침"
      subtitle="회원 정보의 수집, 이용, 보관 및 보호 기준을 투명하게 안내합니다."
      lastUpdated="시행일 2026년 2월 10일"
    >
      {sections.map((section) => (
        <section key={section.title} className="clay-page-section p-5 md:p-6">
          <h2 className="mb-3 text-xl font-bold text-[color:var(--color-text)]">{section.title}</h2>
          {section.body?.map((paragraph) => (
            <p key={paragraph} className="mb-3 text-sm leading-7 text-[color:var(--color-text-secondary)] last:mb-0">
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
