'use client';

import { useState, useEffect } from "react";

interface ThinkingPanelProps {
  thinking: string;
  isThinking?: boolean;
}

export function ThinkingPanel({ thinking, isThinking = false }: ThinkingPanelProps) {
  const [isOpen, setIsOpen] = useState(false);
  
  // Auto-open if it's the first time and actively thinking? 
  // Maybe better to keep it closed by default to reduce noise, 
  // but show a clear indicator that work is happening.

  if (!thinking && !isThinking) {
    return null;
  }

  return (
    <div className="mt-2 mb-2 rounded-lg border border-slate-800 bg-slate-900/50 overflow-hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center gap-2 px-3 py-2 text-xs text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 transition-all duration-200"
      >
        <span className={`transform transition-transform duration-200 ${isOpen ? "rotate-90" : ""}`}>
          ▶
        </span>
        <span className="font-medium flex-1 text-left flex items-center gap-2">
          Thinking Process
          {isThinking && (
            <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 text-[10px] animate-pulse">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-bounce" />
              Generating...
            </span>
          )}
        </span>
        <span className="text-slate-600 text-[10px] uppercase tracking-wider font-semibold">
          {isOpen ? "Hide" : "Show"}
        </span>
      </button>
      
      <div 
        className={`transition-[max-height,opacity] duration-300 ease-in-out overflow-hidden ${
          isOpen ? "max-h-96 opacity-100" : "max-h-0 opacity-0"
        }`}
      >
        <div className="px-3 pb-3 pt-0 border-t border-slate-800/50 bg-slate-950/30">
          <div className="pt-2">
            <pre className="text-xs text-slate-300 whitespace-pre-wrap font-mono leading-relaxed opacity-90">
              {thinking}
              {isThinking && <span className="inline-block w-1.5 h-3 ml-1 bg-emerald-500/50 animate-pulse" />}
            </pre>
          </div>
        </div>
      </div>
    </div>
  );
}
