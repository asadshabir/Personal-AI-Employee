"use client";
import { useState, useRef, useEffect, FormEvent } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface Message {
  role: "user" | "assistant";
  content: string;
}

function TypingDots() {
  return (
    <div className="chat-bubble chat-ai" style={{ display: "flex", alignItems: "center", gap: 6 }}>
      <div className="typing">
        <span /><span /><span />
      </div>
    </div>
  );
}

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: "Hi! I'm your AI Employee assistant. I can help you manage WhatsApp replies, Gmail drafts, LinkedIn posts, and answer questions about your automation setup. How can I help?",
    },
  ]);
  const [input, setInput]   = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError]   = useState("");
  const bottomRef           = useRef<HTMLDivElement>(null);
  const inputRef            = useRef<HTMLInputElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function send(e: FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || loading) return;

    const history = messages.map(m => ({ role: m.role, content: m.content }));
    const userMsg: Message = { role: "user", content: text };
    setMessages(prev => [...prev, userMsg]);
    setInput("");
    setLoading(true);
    setError("");

    try {
      const res = await fetch(`${API}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, history }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setMessages(prev => [...prev, { role: "assistant", content: data.reply }]);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed";
      setError(msg);
      setMessages(prev => [...prev, {
        role: "assistant",
        content: "⚠ Backend unreachable. Start: `uvicorn api_server:app --reload --port 8000`",
      }]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  }

  function clearChat() {
    setMessages([{
      role: "assistant",
      content: "Chat cleared. How can I help?",
    }]);
    setError("");
  }

  return (
    <div className="page-enter" style={{
      display: "flex",
      flexDirection: "column",
      height: "100vh",
      padding: 32,
      paddingBottom: 0,
      maxWidth: 800,
    }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: "var(--text)", margin: 0 }}>
            AI Chat
          </h1>
          <p style={{ color: "var(--text-dim)", fontSize: 13, marginTop: 4 }}>
            Ask your AI Employee anything · powered by Groq
          </p>
        </div>
        <button
          onClick={clearChat}
          style={{
            background: "transparent",
            border: "1px solid var(--border)",
            color: "var(--text-dim)",
            borderRadius: 6,
            padding: "6px 14px",
            fontSize: 12,
            cursor: "pointer",
          }}
        >
          Clear
        </button>
      </div>

      {error && (
        <div style={{
          background: "rgba(255,68,102,0.1)",
          border: "1px solid rgba(255,68,102,0.3)",
          borderRadius: 8,
          padding: 10,
          color: "var(--danger)",
          fontSize: 12,
          marginBottom: 12,
        }}>
          ⚠ {error}
        </div>
      )}

      {/* Messages */}
      <div style={{
        flex: 1,
        overflowY: "auto",
        display: "flex",
        flexDirection: "column",
        gap: 10,
        paddingBottom: 16,
      }}>
        {messages.map((msg, i) => (
          <div key={i} style={{
            display: "flex",
            justifyContent: msg.role === "user" ? "flex-end" : "flex-start",
          }}>
            <div className={`chat-bubble ${msg.role === "user" ? "chat-user" : "chat-ai"}`}>
              {msg.role === "assistant" && (
                <div style={{ fontSize: 10, color: "var(--accent)", marginBottom: 4, fontWeight: 600 }}>
                  AI Employee
                </div>
              )}
              <div style={{ whiteSpace: "pre-wrap" }}>{msg.content}</div>
            </div>
          </div>
        ))}
        {loading && (
          <div style={{ display: "flex", justifyContent: "flex-start" }}>
            <TypingDots />
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <form
        onSubmit={send}
        style={{
          display: "flex",
          gap: 10,
          padding: "16px 0 24px",
          borderTop: "1px solid var(--border)",
          background: "var(--bg)",
        }}
      >
        <input
          ref={inputRef}
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder="Ask anything — 'How many emails today?', 'Draft a LinkedIn post about AI'…"
          disabled={loading}
          style={{
            flex: 1,
            background: "var(--bg-card)",
            border: "1px solid var(--border)",
            borderRadius: 8,
            padding: "12px 16px",
            color: "var(--text)",
            fontSize: 14,
            outline: "none",
            transition: "border-color 0.15s",
          }}
          onFocus={e => (e.target.style.borderColor = "var(--accent-dim)")}
          onBlur={e => (e.target.style.borderColor = "var(--border)")}
        />
        <button
          type="submit"
          disabled={!input.trim() || loading}
          style={{
            background: input.trim() && !loading ? "var(--accent)" : "rgba(0,255,136,0.15)",
            border: "none",
            borderRadius: 8,
            padding: "0 20px",
            color: input.trim() && !loading ? "#000" : "var(--text-dim)",
            fontWeight: 700,
            fontSize: 14,
            cursor: input.trim() && !loading ? "pointer" : "not-allowed",
            transition: "background 0.15s, color 0.15s",
            minWidth: 80,
          }}
        >
          {loading ? "…" : "Send"}
        </button>
      </form>
    </div>
  );
}
