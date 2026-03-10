export default function TermsPage() {
    return (
      <div style={{ maxWidth: "800px", margin: "0 auto", padding: "40px 20px", fontFamily: "'Noto Sans KR', sans-serif", lineHeight: "1.6", color: "#333" }}>
        <h1 style={{ fontSize: "28px", fontWeight: "800", marginBottom: "20px" }}>이용약관</h1>
        <p style={{ marginBottom: "20px", color: "#666" }}>최종 수정일: 2026년 2월 10일</p>
  
        <section style={{ marginBottom: "30px" }}>
          <h2 style={{ fontSize: "20px", fontWeight: "700", marginBottom: "10px" }}>제1조 (목적)</h2>
          <p>이 약관은 쥬라프(이하 &quot;회사&quot;)가 제공하는 한우 농장 통합 관리 대시보드 및 관련 제반 서비스(이하 &quot;서비스&quot;)의 이용과 관련하여 회사와 회원 간의 권리, 의무 및 책임사항, 기타 필요한 사항을 규정함을 목적으로 합니다.</p>
        </section>
  
        <section style={{ marginBottom: "30px" }}>
          <h2 style={{ fontSize: "20px", fontWeight: "700", marginBottom: "10px" }}>제2조 (용어의 정의)</h2>
          <p>1. &quot;서비스&quot;라 함은 구현되는 단말기(PC, 휴대형단말기 등 각종 유무선 장치를 포함)와 상관없이 &quot;회원&quot;이 이용할 수 있는 쥬라프 및 관련 제반 서비스를 의미합니다.</p>
          <p>2. &quot;회원&quot;이라 함은 회사의 &quot;서비스&quot;에 접속하여 본 약관에 따라 회사와 이용계약을 체결하고 회사가 제공하는 &quot;서비스&quot;를 이용하는 고객을 말합니다.</p>
        </section>
  
        <section style={{ marginBottom: "30px" }}>
          <h2 style={{ fontSize: "20px", fontWeight: "700", marginBottom: "10px" }}>제3조 (회사의 의무)</h2>
          <p>1. 회사는 관련 법령과 이 약관이 금지하거나 미풍양속에 반하는 행위를 하지 않으며, 계속적이고 안정적으로 서비스를 제공하기 위하여 최선을 다하여 노력합니다.</p>
          <p>2. 회사는 회원이 안전하게 서비스를 이용할 수 있도록 개인정보 보호를 위한 보안 시스템을 갖추어야 하며 개인정보처리방침을 공시하고 준수합니다.</p>
        </section>
  
        <section style={{ marginBottom: "30px" }}>
          <h2 style={{ fontSize: "20px", fontWeight: "700", marginBottom: "10px" }}>제4조 (회원의 의무)</h2>
          <p>회원은 다음 행위를 하여서는 안 됩니다.</p>
          <ul style={{ listStyleType: "disc", paddingLeft: "20px" }}>
            <li>신청 또는 변경 시 허위내용의 등록</li>
            <li>타인의 정보 도용</li>
            <li>회사가 게시한 정보의 변경</li>
            <li>기타 불법적이거나 부당한 행위</li>
          </ul>
        </section>
  
        <section style={{ marginBottom: "30px" }}>
          <h2 style={{ fontSize: "20px", fontWeight: "700", marginBottom: "10px" }}>문의처</h2>
          <p>서비스 이용과 관련하여 문의사항이 있으신 경우 아래 연락처로 문의 주시기 바랍니다.</p>
          <ul style={{ listStyleType: "none", padding: 0, marginTop: "10px" }}>
            <li><strong>상호명:</strong> 쥬라프 (Joolife)</li>
            <li><strong>대표자:</strong> 박주호</li>
            <li><strong>전화번호:</strong> 010-3159-3708</li>
            <li><strong>이메일:</strong> joolife@joolife.io.kr</li>
            <li><strong>주소:</strong> 경기 안양시 동안구 관평로212번길 21 공작부영아파트 309동 1312호</li>
            <li><strong>웹사이트:</strong> joolife.io.kr</li>
          </ul>
        </section>
  
        <div style={{ marginTop: "40px", textAlign: "center" }}>
          <a href="/" style={{ padding: "10px 20px", background: "#3E2F1C", color: "white", borderRadius: "8px", textDecoration: "none", fontWeight: "bold" }}>홈으로 돌아가기</a>
        </div>
      </div>
    );
  }
