"use client";

import { useState, useCallback } from "react";
import { api, type ChatEvent, type CapeExecution } from "@/lib/api";

// ============================================================
// Types
// ============================================================

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  status: "pending" | "streaming" | "complete" | "error";
  execution?: CapeExecution;
}

export interface UseChatOptions {
  onError?: (error: Error) => void;
}

export interface UseChatReturn {
  messages: Message[];
  isStreaming: boolean;
  currentCape: { id: string; name: string } | null;
  sendMessage: (
    content: string,
    model: string,
    enabledCapes?: string[]
  ) => Promise<void>;
  clearMessages: () => void;
}

// ============================================================
// Hook
// ============================================================

export function useChat(options: UseChatOptions = {}): UseChatReturn {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentCape, setCurrentCape] = useState<{
    id: string;
    name: string;
  } | null>(null);

  const sendMessage = useCallback(
    async (content: string, model: string, enabledCapes?: string[]) => {
      // 1. Add user message
      const userMessage: Message = {
        id: `user-${Date.now()}`,
        role: "user",
        content,
        timestamp: new Date(),
        status: "complete",
      };

      setMessages((prev) => [...prev, userMessage]);

      // 2. Create assistant message placeholder
      const assistantId = `assistant-${Date.now()}`;
      const assistantMessage: Message = {
        id: assistantId,
        role: "assistant",
        content: "",
        timestamp: new Date(),
        status: "streaming",
      };

      setMessages((prev) => [...prev, assistantMessage]);
      setIsStreaming(true);
      setCurrentCape(null);

      // 3. Stream response
      try {
        for await (const event of api.chat(content, model, enabledCapes)) {
          switch (event.type) {
            case "cape_match":
              // Cape matched - could show indicator
              setCurrentCape({ id: event.cape_id, name: event.cape_name });
              break;

            case "cape_start":
              // Update message with cape execution status
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? {
                        ...m,
                        execution: {
                          cape_id: event.cape_id,
                          cape_name: event.cape_name,
                          status: "running" as const,
                        },
                      }
                    : m
                )
              );
              break;

            case "content":
              // Append content chunk
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? { ...m, content: m.content + event.text }
                    : m
                )
              );
              break;

            case "cape_end":
              // Update execution status
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? {
                        ...m,
                        execution: m.execution
                          ? {
                              ...m.execution,
                              status: "completed" as const,
                              duration_ms: event.duration_ms,
                              tokens_used: event.tokens_used,
                              cost_usd: event.cost_usd,
                            }
                          : undefined,
                      }
                    : m
                )
              );
              setCurrentCape(null);
              break;

            case "error":
              // Handle error
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? {
                        ...m,
                        status: "error" as const,
                        content:
                          m.content || `Error: ${event.message}`,
                        execution: m.execution
                          ? { ...m.execution, status: "failed" as const }
                          : undefined,
                      }
                    : m
                )
              );
              options.onError?.(new Error(event.message));
              break;

            case "done":
              // Mark message complete
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? { ...m, status: "complete" as const }
                    : m
                )
              );
              break;
          }
        }
      } catch (error) {
        // Handle network/parse errors
        const errorMessage =
          error instanceof Error ? error.message : "Unknown error occurred";

        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? {
                  ...m,
                  status: "error" as const,
                  content: m.content || `Error: ${errorMessage}`,
                }
              : m
          )
        );

        options.onError?.(
          error instanceof Error ? error : new Error(errorMessage)
        );
      } finally {
        setIsStreaming(false);
        setCurrentCape(null);
      }
    },
    [options]
  );

  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  return {
    messages,
    isStreaming,
    currentCape,
    sendMessage,
    clearMessages,
  };
}
