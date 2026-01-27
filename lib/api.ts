export interface StreamEvent {
  type: "classification" | "chunk" | "validation" | "error";
  query_type?: string;
  section?: string;
  content?: string;
  result?: any;
  message?: string;
}

interface StreamChatArgs {
  messages: { role: string; content: string }[];
  mode: "auto" | "pro" | "fast";
  includeThinking: boolean;
}

export async function streamChat(
  { messages, mode, includeThinking }: StreamChatArgs,
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
