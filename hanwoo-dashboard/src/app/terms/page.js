import LegalDocumentLayout from '@/components/layout/LegalDocumentLayout';

const sections = [
  {
    title: '제1조 목적',
    body: [
      '이 약관은 주라이프(이하 "회사")가 제공하는 한우 농장 통합 관리 서비스의 이용과 관련하여 회사와 회원 간의 권리, 의무 및 책임사항을 규정하는 것을 목적으로 합니다.',
    ],
  },
  {
    title: '제2조 정의',
    body: [
      '"서비스"란 회사가 제공하는 사양 관리, 번식 관리, 재고 관리, 판매 관리, 일정 관리 및 이에 부수하는 제반 기능을 의미합니다.',
      '"회원"이란 본 약관에 동의하고 회사가 제공하는 서비스를 이용하는 개인 또는 사업자를 의미합니다.',
    ],
  },
  {
    title: '제3조 회사의 의무',
    body: [
      '회사는 관련 법령과 본 약관이 금지하는 행위를 하지 않으며, 안정적으로 서비스를 제공하기 위해 지속적으로 노력합니다.',
      '회사는 회원이 안전하게 서비스를 이용할 수 있도록 개인정보 보호 및 보안 체계를 유지합니다.',
    ],
  },
  {
    title: '제4조 회원의 의무',
    list: [
      '허위 정보로 가입하거나 타인의 정보를 도용해서는 안 됩니다.',
      '서비스 운영을 방해하거나 회사가 제공하는 정보를 무단으로 변경해서는 안 됩니다.',
      '관계 법령 및 본 약관을 위반하는 행위를 해서는 안 됩니다.',
    ],
  },
  {
    title: '문의처',
    list: [
      '상호명: 주라이프 (Joolife)',
      '대표자: 박주호',
      '전화번호: 010-3159-3708',
      '이메일: joolife@joolife.io.kr',
      '주소: 경기도 안양시 동안구 관평로212번길 21 공작부영아파트 309동 1312호',
      '웹사이트: joolife.io.kr',
    ],
  },
];

export default function TermsPage() {
  return (
    <LegalDocumentLayout
      eyebrow="Terms of Service"
      title="이용약관"
      subtitle="주라이프 서비스 이용에 필요한 기본 원칙과 운영 기준을 안내합니다."
      lastUpdated="최종 수정일 2026년 2월 10일"
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
