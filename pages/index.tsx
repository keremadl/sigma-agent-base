import { useState } from "react";

export default function HomePage() {
  const [status, setStatus] = useState<string>("Checking...");

  const checkBackend = async () => {
    try {
      const response = await fetch("http://127.0.0.1:8765/health");
      const data = await response.json();
      setStatus(`Backend: ${data.status} | Memory: ${data.memory_initialized ? "✓" : "✗"} | Embedder: ${data.embedder_loaded ? "✓" : "✗"}`);
    } catch (error) {
      setStatus(`Backend Error: ${error instanceof Error ? error.message : String(error)}`);
    }
  };

  return (
    <div style={{ padding: "2rem", fontFamily: "system-ui" }}>
      <h1>Sigma Agent - Ready</h1>
      <p>Status: {status}</p>
      <button onClick={checkBackend} style={{ padding: "0.5rem 1rem", marginTop: "1rem" }}>
        Test Backend Connection
      </button>
      <div style={{ marginTop: "2rem" }}>
        <a href="/chat" style={{ color: "blue", textDecoration: "underline" }}>
          Go to Chat →
        </a>
      </div>
    </div>
  );
}
