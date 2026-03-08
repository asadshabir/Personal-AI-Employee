"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const links = [
  { href: "/dashboard",  label: "Dashboard",  icon: "⬡" },
  { href: "/approvals",  label: "Approvals",  icon: "✓" },
  { href: "/chat",       label: "AI Chat",    icon: "◈" },
];

function getCookie(name: string): string {
  return document.cookie
    .split("; ")
    .find(row => row.startsWith(`${name}=`))
    ?.split("=")[1] ?? "";
}

export default function Sidebar() {
  const path = usePathname();
  const router = useRouter();

  async function logout() {
    const token = getCookie("ai_employee_token");
    try {
      await fetch(`${API}/api/auth/logout`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token }),
      });
    } catch { /* ignore — still clear cookie */ }
    // Clear cookie
    document.cookie = "ai_employee_token=; path=/; max-age=0";
    router.push("/login");
  }

  return (
    <aside style={{
      width: 200,
      minHeight: "100vh",
      background: "var(--bg-card)",
      borderRight: "1px solid var(--border)",
      display: "flex",
      flexDirection: "column",
      padding: "24px 12px",
      gap: 4,
      flexShrink: 0,
    }}>
      {/* Brand */}
      <div style={{ padding: "0 6px 20px", borderBottom: "1px solid var(--border)" }}>
        <div style={{ fontSize: 18, fontWeight: 700, color: "var(--accent)", letterSpacing: "-0.5px" }}>
          AI Employee
        </div>
        <div style={{ fontSize: 11, color: "var(--text-dim)", marginTop: 2 }}>
          Autonomous Agent
        </div>
      </div>

      {/* Nav */}
      <nav style={{ marginTop: 16, display: "flex", flexDirection: "column", gap: 2 }}>
        {links.map(l => (
          <Link
            key={l.href}
            href={l.href}
            className={`nav-link ${path === l.href ? "active" : ""}`}
          >
            <span style={{ fontSize: 16 }}>{l.icon}</span>
            {l.label}
          </Link>
        ))}
      </nav>

      {/* Footer + Logout */}
      <div style={{ marginTop: "auto", display: "flex", flexDirection: "column", gap: 8 }}>
        <button
          onClick={logout}
          style={{
            background: "transparent",
            border: "1px solid var(--border)",
            borderRadius: 7,
            padding: "7px 10px",
            color: "var(--text-dim)",
            fontSize: 12,
            cursor: "pointer",
            textAlign: "left",
            width: "100%",
            transition: "border-color 0.15s, color 0.15s",
          }}
          onMouseEnter={e => {
            (e.currentTarget as HTMLButtonElement).style.borderColor = "var(--danger)";
            (e.currentTarget as HTMLButtonElement).style.color = "var(--danger)";
          }}
          onMouseLeave={e => {
            (e.currentTarget as HTMLButtonElement).style.borderColor = "var(--border)";
            (e.currentTarget as HTMLButtonElement).style.color = "var(--text-dim)";
          }}
        >
          ⎋ Logout
        </button>
        <div style={{ padding: "0 2px", fontSize: 11, color: "var(--text-dim)" }}>
          v1.0 · Hackathon
        </div>
      </div>
    </aside>
  );
}
