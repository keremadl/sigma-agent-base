'use client';

import { useState, useEffect } from "react";
import { ChatInterface } from "../components/ChatInterface";
import { Sidebar } from "../components/Sidebar";
import {
  Conversation,
  getConversations,
  deleteConversation,
} from "../lib/api";

export default function ChatPage() {
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [isLoadingConversations, setIsLoadingConversations] = useState(false);

  // Load conversations on mount
  useEffect(() => {
    const loadConversations = async () => {
      setIsLoadingConversations(true);
      try {
        const convs = await getConversations();
        setConversations(convs);
      } catch (err) {
        console.error("Failed to load conversations:", err);
      } finally {
        setIsLoadingConversations(false);
      }
    };
    loadConversations();
  }, []);

  const handleSelectConversation = (id: string | null) => {
    setConversationId(id);
  };

  const handleNewChat = () => {
    setConversationId(null);
  };

  const handleDeleteConversation = async (id: string) => {
    try {
      await deleteConversation(id);
      // Refresh conversations list
      const convs = await getConversations();
      setConversations(convs);
      // If deleted conversation was active, clear it
      if (conversationId === id) {
        setConversationId(null);
      }
    } catch (err) {
      console.error("Failed to delete conversation:", err);
    }
  };

  const handleConversationChange = (id: string | null) => {
    setConversationId(id);
    // Refresh conversations list when conversation changes (e.g., new conversation created)
    getConversations()
      .then((convs) => setConversations(convs))
      .catch((err) => console.error("Failed to refresh conversations:", err));
  };

  return (
    <div className="flex h-screen bg-slate-950 text-slate-50">
      <Sidebar
        conversations={conversations}
        activeConversationId={conversationId}
        onSelectConversation={handleSelectConversation}
        onDeleteConversation={handleDeleteConversation}
        onNewChat={handleNewChat}
        isLoading={isLoadingConversations}
      />
      <div className="flex-1 flex flex-col min-w-0">
        <ChatInterface
          conversationId={conversationId}
          onConversationChange={handleConversationChange}
          onNewChat={handleNewChat}
          onDeleteConversation={handleDeleteConversation}
        />
      </div>
    </div>
  );
}
