'use client';

import { ThinkingPanel } from "./ThinkingPanel";

export interface ValidationInfo {
  is_valid: boolean;
  warnings: string[];
  errors: string[];
}

interface MessageBubbleProps {
  role: "user" | "assistant";
  content: string;
  thinking?: string;
  queryType?: string;
  validation?: ValidationInfo;
  isStreaming?: boolean;
}

export function MessageBubble({
  role,
  content,
  thinking,
  queryType,
  validation,
  isStreaming,
}: MessageBubbleProps) {
  const isUser = role === "user";

  return (
    <div
      className={`mb-4 flex ${isUser ? "justify-end" : "justify-start"}`}
    >
      <div
        className={`max-w-[80%] rounded-lg px-4 py-2 ${
          isUser
            ? "bg-emerald-500 text-slate-950"
            : "bg-slate-800 text-slate-50"
        }`}
      >
        {queryType && !isUser && (
          <div className="mb-1">
            <span className="text-xs px-2 py-0.5 rounded bg-slate-700 text-slate-300">
              {queryType}
            </span>
          </div>
        )}

        {thinking && !isUser && (
          <ThinkingPanel thinking={thinking} isThinking={isStreaming} />
        )}

        <div className="whitespace-pre-wrap">{content}</div>

        {validation && !isUser && (
          <div className="mt-2 text-xs">
            {validation.errors.length > 0 && (
              <div className="text-red-400">
                Errors: {validation.errors.join(", ")}
              </div>
            )}
            {validation.warnings.length > 0 && (
              <div className="text-amber-400">
                Warnings: {validation.warnings.join(", ")}
              </div>
            )}
            {validation.is_valid && validation.errors.length === 0 && (
              <div className="text-emerald-400">✓ Validated</div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
