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
      background: "var(--color-bg)",
      fontFamily: "var(--font-sans-custom)"
    }}>
      <div style={{
        background: "var(--surface-gradient)",
        padding: "40px",
        borderRadius: "32px",
        boxShadow: "var(--shadow-lg)",
        border: "1px solid var(--color-surface-stroke)",
        width: "100%",
        maxWidth: "400px"
      }}>
        <h1 style={{fontSize:"24px", fontWeight:800, marginBottom:"8px", color:"var(--color-text)", textAlign:"center", letterSpacing:"0.04em", fontFamily:"var(--font-display-custom)"}}>한우 대시보드</h1>
        <p style={{fontSize:"14px", color:"var(--color-text-secondary)", marginBottom:"24px", textAlign:"center"}}>관리자 계정으로 로그인하세요.</p>
        
        <form onSubmit={handleSubmit} style={{display:"flex", flexDirection:"column", gap:"16px"}}>
          <input
            type="text"
            placeholder="아이디"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            style={{
              padding: "16px",
              borderRadius: "18px",
              border: "1px solid var(--color-surface-border)",
              fontSize: "16px",
              outline: "none",
              background: "var(--surface-gradient)",
              color: "var(--color-text)",
              boxShadow: "var(--shadow-inset-soft)"
            }}
          />
          <input
            type="password"
            placeholder="비밀번호"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            style={{
              padding: "16px",
              borderRadius: "18px",
              border: "1px solid var(--color-surface-border)",
              fontSize: "16px",
              outline: "none",
              background: "var(--surface-gradient)",
              color: "var(--color-text)",
              boxShadow: "var(--shadow-inset-soft)"
            }}
          />
          {error && <div style={{color:"var(--color-danger)", fontSize:"13px", textAlign:"center"}}>{error}</div>}
          <button
            type="submit"
            style={{
              padding: "16px",
              borderRadius: "18px",
              background: "var(--surface-gradient-primary)",
              color: "white",
              fontSize: "16px",
              fontWeight: 700,
              border: "1px solid var(--color-surface-stroke)",
              cursor: "pointer",
              transition: "background 0.2s",
              boxShadow: "var(--shadow-button-primary)"
            }}
          >
            로그인
          </button>
        </form>
      </div>
    </div>
  );
}
