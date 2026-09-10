/**
 * Live streaming chat hook for Document Copilot.
 *
 * Communicates directly with FastAPI `POST /chat/stream` using the
 * AI SDK data-stream protocol (`0:` text deltas, `2:` citations, `3:` error, `e:` finish).
 */

import { useCallback, useEffect, useRef, useState } from "react";

import { api, type ChatMessage, type Citation } from "@/lib/api";
import { env } from "@/lib/env";
import { getAccessToken } from "@/lib/supabase";

export interface PipelineStatus {
  stage: "searching" | "analyzing" | "validating" | "complete" | null;
  message: string | null;
}

interface UseChatStreamOptions {
  threadId?: string | null;
  onThreadCreated?: (threadId: string) => void;
}

export function useChatStream({
  threadId,
  onThreadCreated,
}: UseChatStreamOptions = {}) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(Boolean(threadId));
  const [pipelineStatus, setPipelineStatus] = useState<PipelineStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  const streamAbortControllerRef = useRef<AbortController | null>(null);
  const creatingThreadIdRef = useRef<string | null>(null);

  // Load message history whenever threadId changes
  useEffect(() => {
    // If this threadId transition is from a newly created thread that is actively streaming,
    // do not abort the stream or overwrite in-memory streaming messages.
    if (threadId && creatingThreadIdRef.current === threadId) {
      creatingThreadIdRef.current = null;
      return;
    }

    // Navigating away: abort any active streaming request
    if (streamAbortControllerRef.current) {
      streamAbortControllerRef.current.abort();
      streamAbortControllerRef.current = null;
      setIsStreaming(false);
      setPipelineStatus(null);
    }

    if (!threadId) {
      setMessages([]);
      setIsLoadingHistory(false);
      setError(null);
      return;
    }

    let isMounted = true;
    setIsLoadingHistory(true);
    setMessages([]);
    setError(null);

    api
      .getThreadMessages(threadId)
      .then((loadedMessages) => {
        if (isMounted) {
          setMessages(loadedMessages);
          setIsLoadingHistory(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err.message || "Failed to load thread history");
          setIsLoadingHistory(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [threadId]);


  const sendMessage = useCallback(
    async (content: string) => {
      const trimmed = content.trim();
      if (!trimmed || isStreaming) return;

      setError(null);

      let targetThreadId = threadId;

      // 1. If no active thread, create one first
      if (!targetThreadId) {
        try {
          const title = trimmed.length > 50 ? `${trimmed.slice(0, 47)}...` : trimmed;
          const newThread = await api.createThread(title);
          targetThreadId = newThread.id;
          creatingThreadIdRef.current = newThread.id;
          if (onThreadCreated) {
            onThreadCreated(newThread.id);
          }
        } catch (err: unknown) {
          const message = err instanceof Error ? err.message : "Failed to create conversation";
          setError(message);
          return;
        }
      }

      const tempUserMsgId = `temp-user-${Date.now()}`;
      const tempAssistantMsgId = `temp-asst-${Date.now()}`;

      const userMsg: ChatMessage = {
        id: tempUserMsgId,
        thread_id: targetThreadId,
        role: "user",
        content: trimmed,
        created_at: new Date().toISOString(),
      };

      const assistantMsg: ChatMessage = {
        id: tempAssistantMsgId,
        thread_id: targetThreadId,
        role: "assistant",
        content: "",
        citations: [],
        created_at: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setIsStreaming(true);
      setPipelineStatus({
        stage: "searching",
        message: "Searching SEC filings (pgvector + FTS)...",
      });

      const controller = new AbortController();
      streamAbortControllerRef.current = controller;

      try {
        const token = await getAccessToken();
        const headers: Record<string, string> = {
          "Content-Type": "application/json",
        };
        if (token) {
          headers.Authorization = `Bearer ${token}`;
        }

        let response: Response;
        try {
          response = await fetch(`${env.API_BASE_URL}/chat/stream`, {
            method: "POST",
            headers,
            body: JSON.stringify({
              thread_id: targetThreadId,
              message: trimmed,
            }),
            signal: controller.signal,
          });
        } catch (fetchErr: unknown) {
          if (fetchErr instanceof DOMException && fetchErr.name === "AbortError") {
            throw fetchErr;
          }
          throw new Error(
            "Cannot connect to Document Copilot backend. Ensure the backend service is running on " +
              env.API_BASE_URL,
            { cause: fetchErr }
          );
        }

        if (!response.ok) {
          if (response.status === 401) {
            throw new Error("Your session has expired or is invalid. Please sign in again.");
          }
          let errorDetail = `Server error (${response.status})`;
          try {
            const json = await response.json();
            errorDetail = json.detail || json.message || errorDetail;
          } catch {
            // keep status error
          }
          throw new Error(errorDetail);
        }

        if (!response.body) {
          throw new Error("No response body received from server");
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          // Keep the last incomplete line in buffer
          buffer = lines.pop() ?? "";

          for (const line of lines) {
            const trimmedLine = line.trim();
            if (!trimmedLine) continue;

            // AI SDK data stream protocol parsing:
            // 0: "text delta"
            // 2: [citations / status data]
            // 3: "error message"
            // e: { finishReason, usage }
            if (trimmedLine.startsWith("0:")) {
              try {
                const textChunk = JSON.parse(trimmedLine.slice(2));
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === tempAssistantMsgId
                      ? { ...msg, content: msg.content + textChunk }
                      : msg
                  )
                );
              } catch {
                // Ignore parse errors on partial chunks
              }
            } else if (trimmedLine.startsWith("2:")) {
              try {
                const parsed = JSON.parse(trimmedLine.slice(2));
                if (Array.isArray(parsed) && parsed.length > 0) {
                  const firstItem = parsed[0];
                  if (firstItem && typeof firstItem === "object" && firstItem.type === "status") {
                    setPipelineStatus({
                      stage: firstItem.stage,
                      message: firstItem.message,
                    });
                  } else {
                    const citationsData = parsed as Citation[];
                    setMessages((prev) =>
                      prev.map((msg) =>
                        msg.id === tempAssistantMsgId
                          ? {
                              ...msg,
                              citations: [...(msg.citations || []), ...citationsData],
                            }
                          : msg
                      )
                    );
                  }
                }
              } catch {
                // Ignore parse errors
              }
            } else if (trimmedLine.startsWith("3:")) {
              try {
                const errMessage = JSON.parse(trimmedLine.slice(2));
                setError(errMessage);
              } catch {
                setError(trimmedLine.slice(2));
              }
            }
          }
        }
      } catch (err: unknown) {
        if (err instanceof DOMException && err.name === "AbortError") {
          // Manually cancelled by user
        } else {
          const errorMsg = err instanceof Error ? err.message : "Error receiving stream";
          setError(errorMsg);
        }
      } finally {
        setIsStreaming(false);
        setPipelineStatus(null);
        streamAbortControllerRef.current = null;
      }
    },
    [threadId, isStreaming, onThreadCreated]
  );

  const stop = useCallback(() => {
    if (streamAbortControllerRef.current) {
      streamAbortControllerRef.current.abort();
      streamAbortControllerRef.current = null;
      setIsStreaming(false);
      setPipelineStatus(null);
    }
  }, []);

  return {
    messages,
    isStreaming,
    isLoadingHistory,
    pipelineStatus,
    error,
    sendMessage,
    stop,
    setMessages,
  };
}
