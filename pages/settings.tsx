'use client';

import { useEffect, useState } from "react";
import Link from "next/link";
import { saveApiKeyToBackend } from "../lib/api";
import { MemoryPanel } from "../components/MemoryPanel";

const MODEL_TIERS = {
  pro: "gemini-3-pro-preview",
  auto: "gemini-2.5-flash",
  fast: "gemini-2.0-flash",
};

const MODEL_DISPLAY_NAMES = {
  "gemini-3-pro-preview": "Gemini 3 Pro Preview",
  "gemini-2.5-flash": "Gemini 2.5 Flash",
  "gemini-2.0-flash": "Gemini 2.0 Flash",
};

type ModelKey = keyof typeof MODEL_TIERS;
type SavedStatus = "saved" | "not_configured" | "saving" | "error";
type TabType = "keys" | "memory";

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<TabType>("keys");
  const [keys, setKeys] = useState<Record<string, string>>({});
  const [showKeys, setShowKeys] = useState<Record<string, boolean>>({});
  const [savedStatus, setSavedStatus] = useState<Record<string, SavedStatus>>(
    {}
  );

  // Load keys from localStorage on mount
  useEffect(() => {
    const storedKeys = localStorage.getItem("api_keys");
    if (storedKeys) {
      try {
        const parsed = JSON.parse(storedKeys);
        setKeys(parsed);
        // Initialize saved status based on stored keys
        const status: Record<string, SavedStatus> = {};
        Object.values(MODEL_TIERS).forEach((model) => {
          status[model] = parsed[model] ? "saved" : "not_configured";
        });
        setSavedStatus(status);
      } catch (err) {
        console.error("Failed to parse stored API keys:", err);
      }
    } else {
      // Initialize all as not_configured
      const status: Record<string, SavedStatus> = {};
      Object.values(MODEL_TIERS).forEach((model) => {
        status[model] = "not_configured";
      });
      setSavedStatus(status);
    }
  }, []);

  const toggleVisibility = (model: string) => {
    setShowKeys((prev) => ({ ...prev, [model]: !prev[model] }));
  };

  const handleSave = async (model: string) => {
    const key = keys[model]?.trim();
    if (!key) {
      alert("Please enter an API key");
      return;
    }

    setSavedStatus((prev) => ({ ...prev, [model]: "saving" }));

    try {
      // Save to backend
      const success = await saveApiKeyToBackend(model, key);
      if (!success) {
        setSavedStatus((prev) => ({ ...prev, [model]: "error" }));
        setTimeout(() => {
          setSavedStatus((prev) => ({ ...prev, [model]: "not_configured" }));
        }, 3000);
        return;
      }

      // Save to localStorage
      const updatedKeys = { ...keys, [model]: key };
      localStorage.setItem("api_keys", JSON.stringify(updatedKeys));
      setKeys(updatedKeys);
      setSavedStatus((prev) => ({ ...prev, [model]: "saved" }));

      // Reset status after 2 seconds
      setTimeout(() => {
        setSavedStatus((prev) => {
          if (prev[model] === "saved") {
            return { ...prev, [model]: "saved" }; // Keep saved state
          }
          return prev;
        });
      }, 2000);
    } catch (error) {
      console.error(`Error saving key for ${model}:`, error);
      setSavedStatus((prev) => ({ ...prev, [model]: "error" }));
      setTimeout(() => {
        setSavedStatus((prev) => ({ ...prev, [model]: "not_configured" }));
      }, 3000);
    }
  };

  const getStatusIndicator = (status: SavedStatus) => {
    switch (status) {
      case "saved":
        return (
          <span className="text-emerald-400 text-xs font-medium">✓ Saved</span>
        );
      case "saving":
        return (
          <span className="text-amber-400 text-xs font-medium">
            Saving...
          </span>
        );
      case "error":
        return (
          <span className="text-red-400 text-xs font-medium">✗ Error</span>
        );
      default:
        return (
          <span className="text-slate-500 text-xs font-medium">
            ✗ Not configured
          </span>
        );
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-50">
      {/* Header */}
      <header className="border-b border-slate-800 px-4 py-3">
        <div className="mx-auto flex max-w-3xl items-center gap-4">
          <Link
            href="/chat"
            className="inline-flex items-center gap-1 text-sm text-slate-400 hover:text-slate-200 transition-colors"
          >
            ← Back to Chat
          </Link>
          <h1 className="text-xl font-semibold tracking-tight">Settings</h1>
        </div>
      </header>

      {/* Main Content */}
      <main className="mx-auto max-w-3xl px-4 py-6">
        {/* Tab Navigation */}
        <div className="flex border-b border-slate-800 mb-6">
          <button
            onClick={() => setActiveTab("keys")}
            className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${activeTab === "keys"
                ? "border-emerald-500 text-emerald-400"
                : "border-transparent text-slate-400 hover:text-slate-200"
              }`}
          >
            🔑 API Keys
          </button>
          <button
            onClick={() => setActiveTab("memory")}
            className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${activeTab === "memory"
                ? "border-emerald-500 text-emerald-400"
                : "border-transparent text-slate-400 hover:text-slate-200"
              }`}
          >
            💾 Memory
          </button>
        </div>

        {/* Tab Content */}
        {activeTab === "keys" && (
          <>
            <div className="mb-6">
              <h2 className="text-lg font-medium mb-2">API Key Management</h2>
              <p className="text-sm text-slate-400">
                Enter your Gemini API keys for each model tier. Keys are stored
                locally and never leave your computer.
              </p>
            </div>

            <div className="space-y-4">
              {(Object.keys(MODEL_TIERS) as ModelKey[]).map((tier) => {
                const model = MODEL_TIERS[tier];
                const displayName = MODEL_DISPLAY_NAMES[model];
                const keyValue = keys[model] || "";
                const isVisible = showKeys[model] || false;
                const status = savedStatus[model] || "not_configured";

                return (
                  <div
                    key={model}
                    className="rounded-lg border border-slate-800 bg-slate-900/60 p-4"
                  >
                    <div className="mb-3">
                      <label
                        htmlFor={`key-${model}`}
                        className="block text-sm font-medium text-slate-200 mb-1"
                      >
                        {displayName}
                      </label>
                      <p className="text-xs text-slate-500 font-mono">{model}</p>
                    </div>

                    <div className="flex gap-2 mb-2">
                      <div className="flex-1 relative">
                        <input
                          id={`key-${model}`}
                          type={isVisible ? "text" : "password"}
                          value={keyValue}
                          onChange={(e) =>
                            setKeys((prev) => ({ ...prev, [model]: e.target.value }))
                          }
                          placeholder="Enter API key..."
                          className="w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-50 placeholder:text-slate-500 focus:border-emerald-500 focus:outline-none"
                        />
                      </div>
                      <button
                        type="button"
                        onClick={() => toggleVisibility(model)}
                        className="px-3 py-2 rounded-md border border-slate-700 bg-slate-800 text-xs text-slate-300 hover:bg-slate-700 transition-colors"
                      >
                        {isVisible ? "Hide" : "Show"}
                      </button>
                      <button
                        type="button"
                        onClick={() => handleSave(model)}
                        disabled={status === "saving" || !keyValue.trim()}
                        className="px-4 py-2 rounded-md bg-emerald-500 text-sm font-semibold text-slate-950 hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-60 transition-colors"
                      >
                        {status === "saving" ? "Saving..." : "Save"}
                      </button>
                    </div>

                    <div className="mt-2">{getStatusIndicator(status)}</div>
                  </div>
                );
              })}
            </div>

            <div className="mt-8 rounded-lg border border-slate-800 bg-slate-900/40 p-4">
              <h3 className="text-sm font-medium text-slate-200 mb-2">
                How to get API keys
              </h3>
              <ul className="text-xs text-slate-400 space-y-1 list-disc list-inside">
                <li>
                  Visit{" "}
                  <a
                    href="https://aistudio.google.com/apikey"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-emerald-400 hover:underline"
                  >
                    Google AI Studio
                  </a>{" "}
                  to create your API keys
                </li>
                <li>Keys are stored in your browser's localStorage</li>
                <li>Keys are automatically sent to the backend on app start</li>
                <li>Each model tier can use the same or different keys</li>
              </ul>
            </div>
          </>
        )}

        {activeTab === "memory" && <MemoryPanel />}
      </main>
    </div>
  );
}
