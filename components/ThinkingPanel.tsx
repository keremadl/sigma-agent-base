'use client';

import { useState } from "react";

interface ThinkingPanelProps {
  thinking: string;
}

export function ThinkingPanel({ thinking }: ThinkingPanelProps) {
  const [isOpen, setIsOpen] = useState(false);

  if (!thinking || !thinking.trim()) {
    return null;
  }

  return (
    <div className="mt-2 rounded-lg border border-slate-700 bg-slate-900/40">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-3 py-2 text-xs text-slate-400 hover:text-slate-200 transition-colors"
      >
        <span className="font-medium">
          {isOpen ? "▼" : "▶"} Thinking Process
        </span>
        <span className="text-slate-500">
          {isOpen ? "Hide" : "Show"} reasoning
        </span>
      </button>
      {isOpen && (
        <div className="px-3 pb-3 max-h-64 overflow-y-auto">
          <pre className="text-xs text-slate-300 whitespace-pre-wrap font-mono">
            {thinking}
          </pre>
        </div>
      )}
    </div>
  );
}
