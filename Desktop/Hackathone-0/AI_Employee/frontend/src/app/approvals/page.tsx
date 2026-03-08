"use client";
import { useEffect, useState, useCallback } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface PendingItem {
  filename: string;
  title: string;
  from: string;
  subject: string;
  preview: string;
  created: string;
  type: "whatsapp" | "gmail" | "linkedin";
}

interface Toast { msg: string; ok: boolean }

const TYPE_COLOR: Record<string, string> = {
  whatsapp: "#25d366",
  gmail:    "#ea4335",
  linkedin: "#0077b5",
};

const TYPE_ICON: Record<string, string> = {
  whatsapp: "💬",
  gmail:    "✉",
  linkedin: "in",
};

export default function Approvals() {
  const [items,  setItems]  = useState<PendingItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy,   setBusy]   = useState<string | null>(null);
  const [toast,  setToast]  = useState<Toast | null>(null);
  const [err,    setErr]    = useState("");

  const showToast = (msg: string, ok: boolean) => {
    setToast({ msg, ok });
    setTimeout(() => setToast(null), 3000);
  };

  const load = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/pending`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      // API returns { items: [...], total: N }
      const data: PendingItem[] = Array.isArray(json) ? json : (json.items ?? []);
      setItems(data);
      setErr("");
    } catch {
      setErr("Backend offline — run: uvicorn api_server:app --reload --port 8000");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(load, 10_000);
    return () => clearInterval(t);
  }, [load]);

  async function approve(filename: string) {
    setBusy(filename);
    try {
      const res = await fetch(`${API}/api/approve/${encodeURIComponent(filename)}`, { method: "POST" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setItems(prev => prev.filter(i => i.filename !== filename));
      showToast(`✓ Approved: ${filename}`, true);
    } catch {
      showToast(`✗ Failed to approve`, false);
    } finally {
      setBusy(null);
    }
  }

  async function reject(filename: string) {
    setBusy(filename);
    try {
      const res = await fetch(`${API}/api/pending/${encodeURIComponent(filename)}`, { method: "DELETE" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setItems(prev => prev.filter(i => i.filename !== filename));
      showToast(`✗ Rejected: ${filename}`, false);
    } catch {
      showToast(`✗ Failed to reject`, false);
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="page-enter" style={{ padding: "28px 32px", maxWidth: 900 }}>
      {/* Toast */}
      {toast && (
        <div style={{
          position: "fixed", top: 24, right: 24, zIndex: 999,
          background: toast.ok ? "rgba(0,255,136,0.15)" : "rgba(255,68,102,0.15)",
          border: `1px solid ${toast.ok ? "var(--accent)" : "var(--danger)"}`,
          color: toast.ok ? "var(--accent)" : "var(--danger)",
          borderRadius: 8, padding: "10px 18px", fontSize: 13, fontWeight: 600,
          boxShadow: "0 4px 20px rgba(0,0,0,0.4)",
          animation: "fadeUp 0.2s ease",
        }}>
          {toast.msg}
        </div>
      )}

      {/* Header */}
      <div style={{ marginBottom: 28 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <h1 style={{ margin: 0, fontSize: 22, fontWeight: 700, color: "var(--text)" }}>
            Pending Approvals
          </h1>
          {items.length > 0 && (
            <span style={{
              background: "rgba(255,170,0,0.15)", border: "1px solid rgba(255,170,0,0.4)",
              color: "var(--warn)", borderRadius: 12, padding: "2px 10px", fontSize: 12, fontWeight: 700,
            }}>
              {items.length}
            </span>
          )}
        </div>
        <p style={{ margin: "4px 0 0", fontSize: 13, color: "var(--text-dim)" }}>
          Review AI-drafted messages · refreshes every 10 s
        </p>
      </div>

      {/* Error */}
      {err && (
        <div style={{
          background: "rgba(255,68,102,0.08)", border: "1px solid rgba(255,68,102,0.28)",
          borderRadius: 8, padding: "12px 16px", color: "var(--danger)", fontSize: 13, marginBottom: 22,
        }}>
          ⚠ {err}
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div style={{ color: "var(--text-dim)", fontSize: 13 }}>Loading…</div>
      )}

      {/* Empty state */}
      {!loading && !err && items.length === 0 && (
        <div className="stat-card" style={{ textAlign: "center", padding: "48px 24px" }}>
          <div style={{ fontSize: 40, marginBottom: 12 }}>✓</div>
          <div style={{ fontSize: 16, fontWeight: 600, color: "var(--accent)", marginBottom: 6 }}>
            All clear
          </div>
          <div style={{ fontSize: 13, color: "var(--text-dim)" }}>
            No pending approvals. The AI is running smoothly.
          </div>
        </div>
      )}

      {/* Items */}
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        {items.map(item => (
          <div key={item.filename}
               className={`approval-card service-${item.type} ${busy === item.filename ? 'bounce' : ''}`}
               style={{ opacity: busy === item.filename ? 0.7 : 1 }}>
            {/* Card header */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <span style={{
                  fontSize: 15,
                  background: `linear-gradient(135deg, ${TYPE_COLOR[item.type]}22, ${TYPE_COLOR[item.type]}44)`,
                  border: `1px solid ${TYPE_COLOR[item.type]}66`,
                  color: TYPE_COLOR[item.type],
                  borderRadius: 8,
                  padding: "4px 10px",
                  fontWeight: 700,
                  boxShadow: `0 0 10px ${TYPE_COLOR[item.type]}22`
                }}>
                  {TYPE_ICON[item.type]} {item.type}
                </span>
                <span style={{ fontSize: 13, color: "var(--text-dim)", fontWeight: 500 }}>
                  {item.created}
                </span>
              </div>
            </div>

            {/* Title / subject */}
            <div style={{
              fontSize: 16,
              fontWeight: 600,
              color: "var(--text)",
              marginBottom: 6,
              lineHeight: 1.4
            }}>
              {item.subject || item.title}
            </div>
            {item.from && (
              <div style={{ fontSize: 13, color: "var(--text)", marginBottom: 10, fontWeight: 500 }}>
                📧 From: <span style={{ color: TYPE_COLOR[item.type] }}>{item.from}</span>
              </div>
            )}

            {/* Preview */}
            {item.preview && (
              <div style={{
                background: "rgba(255,255,255,0.05)",
                border: "1px solid var(--border)",
                borderRadius: 10,
                padding: "14px",
                fontSize: 14,
                color: "var(--text)",
                marginBottom: 16,
                maxHeight: 140,
                overflowY: "auto",
                lineHeight: 1.5,
                fontWeight: 400
              }}>
                {item.preview}
              </div>
            )}

            {/* Filename */}
            <div style={{
              fontSize: 12,
              color: "var(--text-dim)",
              marginBottom: 16,
              fontFamily: "monospace",
              background: "rgba(0,0,0,0.2)",
              padding: "6px 10px",
              borderRadius: 6
            }}>
              📄 {item.filename}
            </div>

            {/* Actions */}
            <div style={{ display: "flex", gap: 12 }}>
              <button
                onClick={() => approve(item.filename)}
                disabled={!!busy}
                className="btn btn-approve"
                style={{
                  flex: 1,
                  fontWeight: 600,
                  fontSize: 14
                }}
              >
                {busy === item.filename ? (
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 6 }}>
                    <div className="typing">
                      <span style={{ width: 5, height: 5, background: "var(--accent)" }}></span>
                      <span style={{ width: 5, height: 5, background: "var(--accent)" }}></span>
                      <span style={{ width: 5, height: 5, background: "var(--accent)" }}></span>
                    </div>
                    <span>Processing</span>
                  </div>
                ) : (
                  "✓ Approve"
                )}
              </button>
              <button
                onClick={() => reject(item.filename)}
                disabled={!!busy}
                className="btn btn-reject"
                style={{
                  flex: 1,
                  fontWeight: 600,
                  fontSize: 14
                }}
              >
                {busy === item.filename ? (
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 6 }}>
                    <div className="typing">
                      <span style={{ width: 5, height: 5, background: "var(--danger)" }}></span>
                      <span style={{ width: 5, height: 5, background: "var(--danger)" }}></span>
                      <span style={{ width: 5, height: 5, background: "var(--danger)" }}></span>
                    </div>
                    <span>Processing</span>
                  </div>
                ) : (
                  "✗ Reject"
                )}
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
