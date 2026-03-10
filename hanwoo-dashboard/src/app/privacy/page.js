export default function PrivacyPage() {
    return (
      <div style={{ maxWidth: "800px", margin: "0 auto", padding: "40px 20px", fontFamily: "'Noto Sans KR', sans-serif", lineHeight: "1.6", color: "#333" }}>
        <h1 style={{ fontSize: "28px", fontWeight: "800", marginBottom: "20px" }}>개인정보처리방침</h1>
        <p style={{ marginBottom: "20px", color: "#666" }}>시행일: 2026년 2월 10일</p>
  
        <section style={{ marginBottom: "30px" }}>
          <h2 style={{ fontSize: "20px", fontWeight: "700", marginBottom: "10px" }}>1. 개인정보의 처리 목적</h2>
          <p>쥬라프(이하 &quot;회사&quot;)는 다음의 목적을 위하여 개인정보를 처리합니다. 처리하고 있는 개인정보는 다음의 목적 이외의 용도로는 이용되지 않으며 이용 목적이 변경되는 경우에는 「개인정보 보호법」 제18조에 따라 별도의 동의를 받는 등 필요한 조치를 이행할 예정입니다.</p>
          <ul style={{ listStyleType: "disc", paddingLeft: "20px", marginTop: "10px" }}>
            <li>회원 가입 및 관리</li>
            <li>서비스 제공 (농장 데이터 분석, 알림 서비스 등)</li>
            <li>민원 처리 및 고지 사항 전달</li>
          </ul>
        </section>
  
        <section style={{ marginBottom: "30px" }}>
          <h2 style={{ fontSize: "20px", fontWeight: "700", marginBottom: "10px" }}>2. 처리하는 개인정보의 항목</h2>
          <p>회사는 서비스 제공을 위해 필요한 최소한의 개인정보를 수집하고 있습니다.</p>
          <ul style={{ listStyleType: "disc", paddingLeft: "20px", marginTop: "10px" }}>
            <li>필수항목: 이름, 전화번호, 이메일, 아이디, 비밀번호</li>
            <li>선택항목: 농장 주소, 사육 두수</li>
          </ul>
        </section>
  
        <section style={{ marginBottom: "30px" }}>
          <h2 style={{ fontSize: "20px", fontWeight: "700", marginBottom: "10px" }}>3. 개인정보의 보유 및 이용 기간</h2>
          <p>회사는 법령에 따른 개인정보 보유·이용기간 또는 정보주체로부터 개인정보를 수집 시에 동의받은 개인정보 보유·이용기간 내에서 개인정보를 처리·보유합니다.</p>
          <ul style={{ listStyleType: "disc", paddingLeft: "20px", marginTop: "10px" }}>
            <li>회원 탈퇴 시까지 (단, 관계 법령 위반에 따른 수사·조사 등이 진행 중인 경우에는 해당 수사·조사 종료 시까지)</li>
          </ul>
        </section>
  
        <section style={{ marginBottom: "30px" }}>
          <h2 style={{ fontSize: "20px", fontWeight: "700", marginBottom: "10px" }}>4. 개인정보 보호책임자</h2>
          <p>회사는 개인정보 처리에 관한 업무를 총괄해서 책임지고, 개인정보 처리와 관련한 정보주체의 불만처리 및 피해구제 등을 위하여 아래와 같이 개인정보 보호책임자를 지정하고 있습니다.</p>
          <ul style={{ listStyleType: "none", padding: 0, marginTop: "10px" }}>
            <li><strong>성명:</strong> 박주호</li>
            <li><strong>직책:</strong> 대표 (CEO)</li>
            <li><strong>연락처:</strong> 010-3159-3708, joolife@joolife.io.kr</li>
            <li><strong>주소:</strong> 경기 안양시 동안구 관평로212번길 21 공작부영아파트 309동 1312호</li>
          </ul>
        </section>
  
        <div style={{ marginTop: "40px", textAlign: "center" }}>
          <a href="/" style={{ padding: "10px 20px", background: "#3E2F1C", color: "white", borderRadius: "8px", textDecoration: "none", fontWeight: "bold" }}>홈으로 돌아가기</a>
        </div>
      </div>
    );
  }
