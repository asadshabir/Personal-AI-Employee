"use client";
import { useEffect, useState, useCallback } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface ServiceStatus { active: boolean; messages_today?: number; emails_today?: number; posts_today?: number; }
interface StatusRes {
  whatsapp: ServiceStatus;
  gmail:    ServiceStatus;
  linkedin: ServiceStatus;
  pending_approvals: number;
  timestamp: string;
}
interface StatsRes {
  whatsapp_sent:  { date: string; count: number }[];
  gmail_sent:     { date: string; count: number }[];
  linkedin_posts: { date: string; count: number }[];
  total_done: number;
  total_pending: number;
}
interface LogEntry { timestamp: string; event: string; detail: string; service: string; }

/* ─── Mini bar chart (pure CSS) ─── */
function BarChart({ data, color }: { data: { count: number }[]; color: string }) {
  if (!data.length)
    return <div style={{ height: 40, fontSize: 12, color: "var(--text-dim)", display: "flex", alignItems: "center" }}>No data</div>;
  const max = Math.max(...data.map(d => d.count), 1);
  return (
    <div className="bar-chart">
      {data.map((d, i) => (
        <div key={i} className="bar" style={{ height: `${Math.max((d.count / max) * 100, 6)}%`, background: color }} />
      ))}
    </div>
  );
}

/* ─── Status dot ─── */
function Dot({ on }: { on: boolean }) {
  return (
    <span className="pulse" style={{
      display: "inline-block", width: 8, height: 8, borderRadius: "50%",
      background: on ? "var(--accent)" : "var(--danger)", marginRight: 6, flexShrink: 0,
    }} />
  );
}

/* ─── CSS 3D Globe ─── */
function Globe() {
  const dots: [number, number][] = [[22, 35], [68, 118], [138, 62], [98, 138], [52, 88]];
  return (
    <div className="globe-container">
      <div className="globe-sphere" />
      <div className="globe-ring globe-ring-1" />
      <div className="globe-ring globe-ring-2" />
      <div className="globe-ring globe-ring-3" />
      {dots.map(([t, l], i) => (
        <div key={i} className="globe-dot pulse" style={{ top: t, left: l, animationDelay: `${i * 0.45}s` }} />
      ))}
    </div>
  );
}

/* ─── Service card ─── */
function ServiceCard({ name, icon, active, count, label, data, color }: {
  name: string; icon: string; active: boolean; count: number;
  label: string; data: { count: number }[]; color: string;
}) {
  return (
    <div className="stat-card" style={{ flex: 1, minWidth: 160 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 10 }}>
        <div>
          <div style={{ fontSize: 22, lineHeight: 1, marginBottom: 4 }}>{icon}</div>
          <div style={{ fontSize: 13, color: "var(--text-dim)" }}>{name}</div>
        </div>
        <div style={{ textAlign: "right" }}>
          <div style={{ fontSize: 26, fontWeight: 700, color, lineHeight: 1 }}>{count}</div>
          <div style={{ fontSize: 11, color: "var(--text-dim)", marginTop: 2 }}>{label}</div>
        </div>
      </div>
      <div style={{ display: "flex", alignItems: "center", marginBottom: 10, fontSize: 12 }}>
        <Dot on={active} />
        <span style={{ color: active ? "var(--accent)" : "var(--danger)" }}>{active ? "Active" : "Offline"}</span>
      </div>
      <BarChart data={data} color={color} />
    </div>
  );
}

const SVC_COLOR: Record<string, string> = { whatsapp: "#25d366", gmail: "#ea4335", linkedin: "#0077b5" };

/* ─── Dashboard page ─── */
export default function Dashboard() {
  const [status, setStatus] = useState<StatusRes | null>(null);
  const [stats,  setStats]  = useState<StatsRes | null>(null);
  const [logs,   setLogs]   = useState<LogEntry[]>([]);
  const [err,    setErr]    = useState("");

  const load = useCallback(async () => {
    try {
      const [s, st, l] = await Promise.all([
        fetch(`${API}/api/status`).then(r => { if (!r.ok) throw new Error(); return r.json(); }),
        fetch(`${API}/api/stats`).then(r => r.json()),
        fetch(`${API}/api/logs/all?limit=15`).then(r => r.json()),
      ]);
      setStatus(s); setStats(st); setLogs(Array.isArray(l) ? l : []);
      setErr("");
    } catch {
      setErr("Backend offline — run: uvicorn api_server:app --reload --port 8000");
    }
  }, []);

  useEffect(() => { load(); const t = setInterval(load, 10_000); return () => clearInterval(t); }, [load]);

  const wa = status?.whatsapp.messages_today ?? 0;
  const gm = status?.gmail.emails_today ?? 0;
  const li = status?.linkedin.posts_today ?? 0;

  return (
    <div className="page-enter" style={{ padding: "28px 32px", maxWidth: 1140 }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 28 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 22, fontWeight: 700, color: "var(--text)" }}>Dashboard</h1>
          <p style={{ margin: "4px 0 0", fontSize: 13, color: "var(--text-dim)" }}>
            Live status · refreshes every 10 s
          </p>
        </div>
        {status && (
          <div style={{
            background: "var(--bg-card)", border: "1px solid var(--border)",
            borderRadius: 8, padding: "7px 14px", fontSize: 12, color: "var(--text-dim)",
          }}>
            ⏱ {new Date(status.timestamp).toLocaleTimeString()}
          </div>
        )}
      </div>

      {/* Error banner */}
      {err && (
        <div style={{
          background: "rgba(255,68,102,0.08)", border: "1px solid rgba(255,68,102,0.28)",
          borderRadius: 8, padding: "12px 16px", color: "var(--danger)", fontSize: 13, marginBottom: 22,
        }}>
          ⚠ {err}
        </div>
      )}

      {/* Row 1: service cards + globe */}
      <div style={{ display: "flex", gap: 20, marginBottom: 20, flexWrap: "wrap" }}>
        <div style={{ display: "flex", gap: 16, flex: 3, minWidth: 0, flexWrap: "wrap" }}>
          <ServiceCard name="WhatsApp" icon="💬" active={status?.whatsapp.active ?? false}
            count={wa} label="msgs today" data={stats?.whatsapp_sent ?? []} color="#25d366" />
          <ServiceCard name="Gmail" icon="✉" active={status?.gmail.active ?? false}
            count={gm} label="emails today" data={stats?.gmail_sent ?? []} color="#ea4335" />
          <ServiceCard name="LinkedIn" icon="in" active={status?.linkedin.active ?? false}
            count={li} label="posts today" data={stats?.linkedin_posts ?? []} color="#0077b5" />
        </div>

        {/* Globe */}
        <div className="stat-card shine" style={{
          flex: 1, minWidth: 230,
          display: "flex", flexDirection: "column",
          alignItems: "center", justifyContent: "center", gap: 16, textAlign: "center",
          background: "var(--glass-bg)",
          backdropFilter: "blur(12px)",
          border: "1px solid var(--glass-border)"
        }}>
          <Globe />
          <div style={{ marginTop: 10 }}>
            <div style={{ fontSize: 36, fontWeight: 800, color: "var(--accent)", textShadow: "0 0 20px rgba(0, 229, 255, 0.5)" }}>{wa + gm + li}</div>
            <div style={{ fontSize: 13, color: "var(--text-dim)", fontWeight: 500, marginTop: 4 }}>actions today</div>
          </div>
        </div>
      </div>

      {/* Row 2: summary stats */}
      <div style={{ display: "flex", gap: 14, marginBottom: 18, flexWrap: "wrap" }}>
        {[
          { label: "Pending Approvals", value: status?.pending_approvals ?? 0, color: "var(--warn)",   icon: "⏳" },
          { label: "Total Done",        value: stats?.total_done ?? 0,         color: "var(--accent)", icon: "✓" },
          { label: "In Queue",          value: stats?.total_pending ?? 0,      color: "#7b2fff",       icon: "◷" },
        ].map((s, i) => (
          <div key={i} className="stat-card" style={{ flex: 1, minWidth: 140, display: "flex", alignItems: "center", gap: 14 }}>
            <div style={{ fontSize: 28 }}>{s.icon}</div>
            <div>
              <div style={{ fontSize: 26, fontWeight: 700, color: s.color, lineHeight: 1 }}>{s.value}</div>
              <div style={{ fontSize: 12, color: "var(--text-dim)", marginTop: 3 }}>{s.label}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Row 3: activity feed */}
      <div className="stat-card">
        <div style={{ fontSize: 14, fontWeight: 600, color: "var(--text)", marginBottom: 14 }}>Recent Activity</div>
        {logs.length === 0 ? (
          <div style={{ color: "var(--text-dim)", fontSize: 13 }}>
            {err ? "Backend offline — no logs available." : "No activity yet."}
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column" }}>
            {logs.map((l, i) => (
              <div key={i} className="activity-item" style={{
                display: "flex", gap: 10, alignItems: "flex-start", fontSize: 13,
                padding: "7px 0",
                borderBottom: i < logs.length - 1 ? "1px solid var(--border)" : undefined,
              }}>
                <span style={{
                  width: 8, height: 8, borderRadius: "50%", flexShrink: 0, marginTop: 4,
                  background: SVC_COLOR[l.service] ?? "var(--text-dim)", display: "inline-block",
                }} />
                <span style={{ color: "var(--text-dim)", fontSize: 11, minWidth: 132, flexShrink: 0 }}>{l.timestamp}</span>
                <span style={{ color: "var(--text)", flex: 1, minWidth: 0 }}>
                  <strong style={{ color: SVC_COLOR[l.service] ?? "var(--text)" }}>[{l.service}]</strong>
                  {" "}{l.event}
                  {l.detail && <span style={{ color: "var(--text-dim)" }}> — {l.detail}</span>}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
