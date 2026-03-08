"use client";
import { Suspense, useState, FormEvent } from "react";
import { useRouter, useSearchParams } from "next/navigation";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [password, setPassword] = useState("");
  const [loading,  setLoading]  = useState(false);
  const [error,    setError]    = useState("");

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const res = await fetch(`${API}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password }),
      });
      if (!res.ok) {
        setError("Invalid password. Try again.");
        return;
      }
      const { token } = await res.json();
      // Store token in a cookie (readable by Next.js proxy)
      document.cookie = `ai_employee_token=${token}; path=/; max-age=86400; SameSite=Strict`;
      const redirectTo = searchParams.get("from") ?? "/dashboard";
      router.push(redirectTo);
    } catch {
      setError("Backend offline — run: uvicorn api_server:app --reload --port 8000");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="stat-card glass login-form" style={{
      width: "100%",
      maxWidth: 400,
      padding: "48px 40px",
    }}>
      {/* Brand */}
      <div className="login-brand" style={{ textAlign: "center", marginBottom: 40 }}>
        <div className="pulse" style={{
          width: 64, height: 64, borderRadius: "50%",
          background: "var(--glass-bg)",
          border: "2px solid var(--accent)",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 28, margin: "0 auto 20px",
          boxShadow: "0 0 30px rgba(0, 229, 255, 0.2)",
        }}>
          ◈
        </div>
        <div style={{ fontSize: 24, fontWeight: 700, color: "var(--text)", marginBottom: 6 }}>AI Employee</div>
        <div style={{ fontSize: 13, color: "var(--text-dim)", fontWeight: 500 }}>
          Autonomous Agent Dashboard
        </div>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit} style={{ animationDelay: "0.3s" }}>
        <div style={{ marginBottom: 24 }}>
          <label style={{
            display: "block", fontSize: 13, fontWeight: 600,
            color: "var(--text)", marginBottom: 10,
            textTransform: "uppercase", letterSpacing: "0.8px",
            opacity: 0.9
          }}>
            Secure Access
          </label>
          <input
            type="password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            placeholder="Enter your secure password"
            autoFocus
            disabled={loading}
            className="glass"
            style={{
              width: "100%",
              background: "rgba(0, 0, 0, 0.2)",
              border: "1px solid var(--border)",
              borderRadius: 12,
              padding: "14px 18px",
              color: "var(--text)",
              fontSize: 15,
              outline: "none",
              boxSizing: "border-box",
              fontWeight: 500
            }}
          />
        </div>

        {error && (
          <div className="stat-card" style={{
            background: "rgba(255,68,102,0.15)",
            border: "1px solid rgba(255,68,102,0.3)",
            borderRadius: 10, padding: "12px 16px",
            color: "var(--danger)", fontSize: 13,
            marginBottom: 16,
            fontWeight: 500
          }}>
            ⚠ {error}
          </div>
        )}

        <button
          type="submit"
          disabled={!password || loading}
          className={`btn ${password && !loading ? 'btn-send' : ''}`}
          style={{
            width: "100%",
            fontSize: 16,
            fontWeight: 700,
            padding: "14px",
          }}
        >
          {loading ? (
            <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}>
              <div className="typing">
                <span style={{ width: 6, height: 6, background: "var(--send-text)" }}></span>
                <span style={{ width: 6, height: 6, background: "var(--send-text)" }}></span>
                <span style={{ width: 6, height: 6, background: "var(--send-text)" }}></span>
              </div>
              <span>Signing in…</span>
            </div>
          ) : (
            "Secure Sign In →"
          )}
        </button>
      </form>

      <div style={{ textAlign: "center", marginTop: 28, fontSize: 12, color: "var(--text-dim)" }}>
        <code style={{ background: "rgba(0,0,0,0.3)", padding: "2px 6px", borderRadius: 6, fontSize: 11 }}>
          DASHBOARD_PASSWORD
        </code> in <code style={{ background: "rgba(0,0,0,0.3)", padding: "2px 6px", borderRadius: 6, fontSize: 11 }}> .env</code>
      </div>
    </div>
  );
}

export default function Login() {
  return (
    <div className="login-container" style={{
      minHeight: "100vh",
      background: "var(--bg)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
    }}>
      <Suspense fallback={<div style={{ color: "var(--text-dim)" }}>Loading…</div>}>
        <LoginForm />
      </Suspense>
    </div>
  );
}
