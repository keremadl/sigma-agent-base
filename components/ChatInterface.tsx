'use client';

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { MessageBubble, ValidationInfo } from "./MessageBubble";
import {
  StreamEvent,
  streamChat,
  ConversationMessage,
  getConversationMessages,
} from "../lib/api";

type MessageRole = "user" | "assistant";

interface ChatMessage {
  role: MessageRole;
  content: string;
  thinking?: string;
  queryType?: string;
  validation?: ValidationInfo;
}

type Mode = "auto" | "pro" | "fast";

const MODE_OPTIONS: { value: Mode; label: string; description: string }[] = [
  { value: "auto", label: "Auto (Smart)", description: "Optimizes speed & cost" },
  { value: "pro", label: "Pro (Best)", description: "Gemini 3 Pro + Thinking" },
  { value: "fast", label: "Fast (Quick)", description: "Instant responses" },
];

interface ChatInterfaceProps {
  conversationId?: string | null;
  onConversationChange?: (id: string | null) => void;
  onNewChat?: () => void;
  onDeleteConversation?: (id: string) => void;
}

export function ChatInterface({
  conversationId: externalConversationId,
  onConversationChange,
  onNewChat,
  onDeleteConversation,
}: ChatInterfaceProps = {}) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentMode, setCurrentMode] = useState<Mode>("auto");
  const [error, setError] = useState<string | null>(null);
  const [conversationId, setConversationId] = useState<string | null>(
    externalConversationId || null
  );
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);
  const isNavigatingRef = useRef(false); // Track if we're navigating from Sidebar vs. creating via stream

  const scrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages]);

  // Load API keys from localStorage and configure backend on mount
  useEffect(() => {
    const storedKeys = localStorage.getItem("api_keys");
    if (storedKeys) {
      try {
        const keys = JSON.parse(storedKeys);
        Object.entries(keys).forEach(async ([model, key]) => {
          if (key && typeof key === "string") {
            try {
              await fetch("http://127.0.0.1:8765/config/api-key", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ model, key }),
              });
            } catch (err) {
              console.error(`Failed to configure key for ${model}:`, err);
            }
          }
        });
      } catch (err) {
        console.error("Failed to parse stored API keys:", err);
      }
    }
  }, []);


  // Load messages when conversationId changes (only if navigating from Sidebar, not during streaming)
  useEffect(() => {
    // If explicitly navigating from Sidebar, always load (even if streaming)
    if (isNavigatingRef.current) {
      isNavigatingRef.current = false;
      // Continue to load messages below
    } else {
      // Skip loading if:
      // 1. We're currently streaming (conversation was just created via stream)
      // 2. We already have messages displayed (they're being streamed)
      if (isStreaming || messages.length > 0) {
        return;
      }
    }
    
    if (conversationId) {
      const loadMessages = async () => {
        setIsLoadingMessages(true);
        try {
          const dbMessages = await getConversationMessages(conversationId);
          // Map ConversationMessage[] to ChatMessage[]
          const mappedMessages: ChatMessage[] = dbMessages.map((msg) => ({
            role: msg.role as MessageRole,
            content: msg.content,
            thinking: msg.thinking || undefined,
          }));
          setMessages(mappedMessages);
        } catch (err) {
          console.error("Failed to load messages:", err);
          setError(err instanceof Error ? err.message : "Failed to load messages");
        } finally {
          setIsLoadingMessages(false);
        }
      };
      loadMessages();
    } else {
      // New chat - clear messages
      setMessages([]);
    }
  }, [conversationId, isStreaming]);

  // Sync external conversationId prop
  useEffect(() => {
    if (externalConversationId !== undefined) {
      setConversationId(externalConversationId);
    }
  }, [externalConversationId]);

  const handleSelectConversation = (id: string | null) => {
    isNavigatingRef.current = true; // Mark as explicit navigation
    setConversationId(id);
    if (onConversationChange) {
      onConversationChange(id);
    }
  };

  const handleNewChat = () => {
    setConversationId(null);
    setMessages([]);
    if (onNewChat) {
      onNewChat();
    }
  };


  const handleSend = async () => {
    if (!input.trim() || isStreaming) return;

    setError(null);

    const userMessage: ChatMessage = {
      role: "user",
      content: input.trim(),
    };

    // Optimistically add user message and placeholder assistant message
    setMessages((prev) => [
      ...prev,
      userMessage,
      { role: "assistant", content: "", thinking: "" },
    ]);

    const newHistory = [...messages, userMessage];
    setInput("");
    setIsStreaming(true);

    let thinkingBuffer = "";
    let answerBuffer = "";
    let queryType: string | undefined;
    let validation: ValidationInfo | undefined;
    let newConversationId: string | null = conversationId;

    try {
      await streamChat(
        {
          messages: newHistory.map((m) => ({
            role: m.role,
            content: m.content,
          })),
          mode: currentMode,
          includeThinking: true,
          conversationId: conversationId,
        },
        (event: StreamEvent) => {
          if (event.type === "conversation") {
            // Backend returned conversation_id (new or existing)
            newConversationId = event.conversation_id || null;
            if (newConversationId && newConversationId !== conversationId) {
              // Don't set isNavigatingRef - this is a stream-created conversation
              // We don't want to trigger message reload
              setConversationId(newConversationId);
              if (onConversationChange) {
                onConversationChange(newConversationId);
              }
            }
          } else if (event.type === "classification") {
            queryType = event.query_type;
          } else if (event.type === "chunk") {
            if (event.section === "thinking") {
              thinkingBuffer += event.content ?? "";
            } else {
              answerBuffer += event.content ?? "";
            }
          } else if (event.type === "validation") {
            validation = event.result as ValidationInfo;
          } else if (event.type === "error") {
            setError(event.message ?? "Unknown stream error");
          }

          // Update last assistant message
          setMessages((prev) => {
            const updated = [...prev];
            const lastIndex = updated.length - 1;
            if (lastIndex >= 0 && updated[lastIndex].role === "assistant") {
              updated[lastIndex] = {
                ...updated[lastIndex],
                content: answerBuffer,
                thinking: thinkingBuffer,
                queryType,
                validation,
              };
            }
            return updated;
          });
        },
        (err) => {
          setError(err);
        }
      );

      // Refresh conversations list after message is sent (triggered by parent via onConversationChange)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setIsStreaming(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex h-full flex-col bg-slate-950 text-slate-50">
      {/* Header */}
      <header className="flex items-center justify-between border-b border-slate-800 px-4 py-3">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">
            Sigma Agent Chat
          </h1>
          <p className="text-xs text-slate-400">
            Local-first AI agent with reasoning and validation
          </p>
        </div>
        <div className="flex items-center gap-3">
          <label className="text-xs text-slate-400">Mode</label>
          <select
            value={currentMode}
            onChange={(e) => setCurrentMode(e.target.value as Mode)}
            className="rounded-md border border-slate-700 bg-slate-900 px-3 py-1.5 text-sm text-slate-100 focus:border-emerald-500 focus:outline-none"
            disabled={isStreaming}
          >
            {MODE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value} title={opt.description}>
                {opt.label}
              </option>
            ))}
          </select>
          <Link
            href="/settings"
            className="inline-flex items-center gap-1.5 rounded-md border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs text-slate-300 hover:bg-slate-800 hover:text-slate-100 transition-colors"
          >
            <span>⚙️</span>
            <span>Settings</span>
          </Link>
        </div>
      </header>

      {/* Messages */}
      <main className="flex-1 overflow-y-auto px-4 py-4">
        <div className="mx-auto flex max-w-3xl flex-col">
          {isLoadingMessages ? (
            <div className="text-center text-slate-400 text-sm py-8">
              Loading conversation...
            </div>
          ) : (
            <>
              {messages.map((msg, idx) => (
                <MessageBubble
                  key={idx}
                  role={msg.role}
                  content={msg.content}
                  thinking={msg.thinking}
                  queryType={msg.queryType}
                  validation={msg.validation}
                />
              ))}
              <div ref={scrollRef} />
            </>
          )}
        </div>
      </main>

      {/* Error */}
      {error && (
        <div className="border-t border-red-800 bg-red-950/60 px-4 py-2 text-xs text-red-200">
          Error: {error}
        </div>
      )}

      {/* Input */}
      <footer className="border-t border-slate-800 bg-slate-950/90 px-4 py-3 backdrop-blur">
        <div className="mx-auto flex max-w-3xl flex-col gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={3}
            placeholder="Ask anything... (Enter to send, Shift+Enter for newline)"
            className="w-full resize-none rounded-lg border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-slate-50 placeholder:text-slate-500 focus:border-emerald-500 focus:outline-none"
            disabled={isStreaming}
          />
          <div className="flex items-center justify-between">
            <span className="text-[11px] text-slate-500">
              Powered by your API keys. Data stays local.
            </span>
            <button
              type="button"
              onClick={handleSend}
              disabled={isStreaming || !input.trim()}
              className="inline-flex items-center gap-2 rounded-full bg-emerald-500 px-4 py-1.5 text-sm font-semibold text-slate-950 hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isStreaming ? "Thinking..." : "Send"}
            </button>
          </div>
        </div>
      </footer>
    </div>
  );
}
