'use client';

import { Conversation } from "../lib/api";

interface SidebarProps {
  conversations: Conversation[];
  activeConversationId: string | null;
  onSelectConversation: (id: string | null) => void;
  onDeleteConversation: (id: string) => void;
  onNewChat: () => void;
  isLoading?: boolean;
}

function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  
  return date.toLocaleDateString();
}

export function Sidebar({
  conversations,
  activeConversationId,
  onSelectConversation,
  onDeleteConversation,
  onNewChat,
  isLoading = false,
}: SidebarProps) {
  const handleDelete = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (confirm("Delete this conversation?")) {
      onDeleteConversation(id);
    }
  };

  return (
    <div className="w-64 flex-shrink-0 bg-slate-900 border-r border-slate-800 flex flex-col h-screen">
      {/* Header */}
      <div className="p-4 border-b border-slate-800">
        <button
          onClick={onNewChat}
          className="w-full rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-semibold px-4 py-2 text-sm transition-colors"
        >
          + New Chat
        </button>
      </div>

      {/* Conversations List */}
      <div className="flex-1 overflow-y-auto">
        {isLoading ? (
          <div className="p-4 text-center text-slate-400 text-sm">
            Loading...
          </div>
        ) : conversations.length === 0 ? (
          <div className="p-4 text-center text-slate-500 text-sm">
            No conversations yet
          </div>
        ) : (
          <div className="p-2">
            {conversations.map((conv) => {
              const isActive = conv.id === activeConversationId;
              return (
                <div
                  key={conv.id}
                  onClick={() => onSelectConversation(conv.id)}
                  className={`
                    group relative mb-1 p-3 rounded-lg cursor-pointer transition-colors
                    ${
                      isActive
                        ? "bg-slate-800 border border-emerald-500/50"
                        : "bg-slate-900/50 hover:bg-slate-800/50"
                    }
                  `}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <div
                        className={`text-sm font-medium truncate ${
                          isActive ? "text-slate-50" : "text-slate-200"
                        }`}
                        title={conv.title}
                      >
                        {conv.title}
                      </div>
                      <div className="text-xs text-slate-500 mt-1">
                        {formatRelativeTime(conv.updated_at)}
                      </div>
                    </div>
                    <button
                      onClick={(e) => handleDelete(e, conv.id)}
                      className="opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:bg-slate-700 rounded text-slate-400 hover:text-red-400"
                      title="Delete conversation"
                    >
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        className="h-4 w-4"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                        />
                      </svg>
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
