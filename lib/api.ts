export interface StreamEvent {
  type: "conversation" | "classification" | "chunk" | "validation" | "error";
  conversation_id?: string;
  query_type?: string;
  section?: string;
  content?: string;
  result?: any;
  message?: string;
}

export interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ConversationMessage {
  id: string;
  conversation_id: string;
  role: "user" | "assistant";
  content: string;
  thinking?: string | null;
  created_at: string;
}

interface StreamChatArgs {
  messages: { role: string; content: string }[];
  mode: "auto" | "pro" | "fast";
  includeThinking: boolean;
  conversationId?: string | null;
}

export async function streamChat(
  { messages, mode, includeThinking, conversationId }: StreamChatArgs,
  onEvent: (event: StreamEvent) => void,
  onError?: (error: string) => void
): Promise<void> {
  try {
    const response = await fetch("http://127.0.0.1:8765/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        messages,
        mode,
        stream: true,
        include_thinking: includeThinking,
        conversation_id: conversationId || null,
      }),
    });

    if (!response.body) {
      throw new Error("No response body from /chat");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const data = line.slice(6).trim();
        if (!data) continue;
        if (data === "[DONE]") return;

        try {
          const parsed = JSON.parse(data) as StreamEvent;
          onEvent(parsed);
        } catch (err) {
          console.error("Failed to parse SSE payload:", err, "line:", data);
        }
      }
    }
  } catch (error) {
    console.error("Stream error:", error);
    if (onError) {
      onError(error instanceof Error ? error.message : String(error));
    }
  }
}

export async function saveApiKeyToBackend(
  model: string,
  key: string
): Promise<boolean> {
  try {
    const response = await fetch("http://127.0.0.1:8765/config/api-key", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ model, key }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(
        `Failed to save API key for ${model}: ${response.status} ${errorText}`
      );
      return false;
    }

    return true;
  } catch (error) {
    console.error(`Error saving API key for ${model}:`, error);
    return false;
  }
}

export async function getConversations(): Promise<Conversation[]> {
  try {
    const response = await fetch("http://127.0.0.1:8765/conversations");
    
    if (!response.ok) {
      throw new Error(`Failed to fetch conversations: ${response.status}`);
    }

    const data = await response.json();
    return data.conversations || [];
  } catch (error) {
    console.error("Error fetching conversations:", error);
    throw error;
  }
}

export async function getConversationMessages(
  conversationId: string
): Promise<ConversationMessage[]> {
  try {
    const response = await fetch(
      `http://127.0.0.1:8765/conversations/${conversationId}`
    );

    if (!response.ok) {
      if (response.status === 404) {
        throw new Error("Conversation not found");
      }
      throw new Error(`Failed to fetch messages: ${response.status}`);
    }

    const data = await response.json();
    return data.messages || [];
  } catch (error) {
    console.error("Error fetching conversation messages:", error);
    throw error;
  }
}

export async function deleteConversation(
  conversationId: string
): Promise<boolean> {
  try {
    const response = await fetch(
      `http://127.0.0.1:8765/conversations/${conversationId}`,
      {
        method: "DELETE",
      }
    );

    if (!response.ok) {
      if (response.status === 404) {
        throw new Error("Conversation not found");
      }
      throw new Error(`Failed to delete conversation: ${response.status}`);
    }

    return true;
  } catch (error) {
    console.error("Error deleting conversation:", error);
    throw error;
  }
}
