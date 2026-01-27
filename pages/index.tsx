'use client';

import { useState } from "react";

type HealthStatus =
  | { state: "idle" }
  | { state: "loading" }
  | { state: "ok"; data: unknown }
  | { state: "error"; error: string };

export default function HomePage() {
  const [health, setHealth] = useState<HealthStatus>({ state: "idle" });

  const checkBackend = async () => {
    try {
      setHealth({ state: "loading" });
      const res = await fetch("http://127.0.0.1:8765/health");
      if (!res.ok) {
        throw new Error(`HTTP ${res.status} ${res.statusText}`);
      }
      const data = await res.json();
      setHealth({ state: "ok", data });
    } catch (err) {
      setHealth({
        state: "error",
        error: err instanceof Error ? err.message : String(err),
      });
    }
  };

  return (
    <main style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "#020617", color: "#f9fafb" }}>
      <div style={{ width: "100%", maxWidth: 640, borderRadius: 16, border: "1px solid #1f2937", background: "rgba(15,23,42,0.9)", padding: 24 }}>
        <h1 style={{ fontSize: 28, fontWeight: 700, marginBottom: 8 }}>
          Sigma Agent - Ready
        </h1>
        <p style={{ fontSize: 14, color: "#9ca3af", marginBottom: 20 }}>
          Frontend is running. Use the button below to test connection to the
          Python backend at{" "}
          <span style={{ fontFamily: "monospace", fontSize: 12 }}>
            http://127.0.0.1:8765/health
          </span>
          .
        </p>

        <button
          type="button"
          onClick={checkBackend}
          disabled={health.state === "loading"}
          style={{
            padding: "8px 16px",
            borderRadius: 999,
            border: "none",
            background: "#22c55e",
            color: "#020617",
            fontSize: 14,
            fontWeight: 600,
            cursor: health.state === "loading" ? "default" : "pointer",
            opacity: health.state === "loading" ? 0.7 : 1,
          }}
        >
          {health.state === "loading" ? "Checking..." : "Test Backend Health"}
        </button>

        <div
          style={{
            marginTop: 24,
            borderRadius: 8,
            border: "1px solid #1f2937",
            background: "rgba(2,6,23,0.9)",
            padding: 12,
            fontFamily: "monospace",
            fontSize: 12,
          }}
        >
          <div
            style={{
              marginBottom: 8,
              fontSize: 10,
              textTransform: "uppercase",
              letterSpacing: 1,
              color: "#9ca3af",
            }}
          >
            Connection status
          </div>
          {health.state === "idle" && (
            <div style={{ color: "#6b7280" }}>
              Idle. Click the button to test.
            </div>
          )}
          {health.state === "loading" && (
            <div style={{ color: "#fcd34d" }}>Checking backend health…</div>
          )}
          {health.state === "ok" && (
            <pre style={{ whiteSpace: "pre-wrap", wordBreak: "break-word", color: "#6ee7b7" }}>
              {JSON.stringify(health.data, null, 2)}
            </pre>
          )}
          {health.state === "error" && (
            <div style={{ color: "#f87171" }}>
              Error talking to backend:
              <br />
              <span style={{ fontSize: 11, wordBreak: "break-word" }}>
                {health.error}
              </span>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}

