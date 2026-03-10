'use client';
import { signIn } from "next-auth/react";
import { useState } from "react";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    const res = await signIn("credentials", {
      username,
      password,
      redirect: false,
    });

    if (res?.error) {
      setError("로그인 실패: 아이디 또는 비밀번호를 확인하세요.");
    } else {
      router.push("/");
    }
  };

  return (
    <div style={{
      minHeight: "100vh",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      background: "#F7F6F4",
      fontFamily: "'Noto Sans KR', sans-serif"
    }}>
      <div style={{
        background: "white",
        padding: "40px",
        borderRadius: "24px",
        boxShadow: "0 10px 30px rgba(0,0,0,0.05)",
        width: "100%",
        maxWidth: "400px"
      }}>
        <h1 style={{fontSize:"24px", fontWeight:800, marginBottom:"8px", color:"#3E2F1C", textAlign:"center"}}>한우 대시보드</h1>
        <p style={{fontSize:"14px", color:"#8B7D6B", marginBottom:"24px", textAlign:"center"}}>관리자 계정으로 로그인하세요.</p>
        
        <form onSubmit={handleSubmit} style={{display:"flex", flexDirection:"column", gap:"16px"}}>
          <input
            type="text"
            placeholder="아이디"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            style={{
              padding: "16px",
              borderRadius: "12px",
              border: "1px solid #E0E0E0",
              fontSize: "16px",
              outline: "none"
            }}
          />
          <input
            type="password"
            placeholder="비밀번호"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            style={{
              padding: "16px",
              borderRadius: "12px",
              border: "1px solid #E0E0E0",
              fontSize: "16px",
              outline: "none"
            }}
          />
          {error && <div style={{color:"red", fontSize:"13px", textAlign:"center"}}>{error}</div>}
          <button
            type="submit"
            style={{
              padding: "16px",
              borderRadius: "12px",
              background: "#3E2F1C",
              color: "white",
              fontSize: "16px",
              fontWeight: 700,
              border: "none",
              cursor: "pointer",
              transition: "background 0.2s"
            }}
          >
            로그인
          </button>
        </form>
      </div>
    </div>
  );
}
