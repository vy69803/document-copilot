/**
 * Product-level API client built on top of http.ts.
 *
 * Exposes typed methods for each backend resource. All components should
 * use `api.*` instead of calling `http()` directly.
 */

import { http } from "@/lib/http";

// ─── Types ───────────────────────────────────────────────────────────

export interface Citation {
  id?: string;
  citation_index: number;
  ticker?: string;
  company_name?: string;
  filing_type?: string;
  fiscal_year?: number;
  section?: string | null;
  page?: number | null;
  excerpt: string;
  chunk_id?: string;
  document_id?: string;
}

export interface ChatThread {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  id: string;
  thread_id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  created_at: string;
}

// ─── API methods ─────────────────────────────────────────────────────

export const api = {
  // --- Threads ---

  listThreads(): Promise<ChatThread[]> {
    return http<ChatThread[]>("/chat/threads");
  },

  createThread(title: string = "New Research Chat"): Promise<ChatThread> {
    return http<ChatThread>("/chat/threads", {
      method: "POST",
      body: { title },
    });
  },

  getThreadMessages(threadId: string): Promise<ChatMessage[]> {
    return http<ChatMessage[]>(`/chat/threads/${threadId}/messages`);
  },

  deleteThread(threadId: string): Promise<void> {
    return http<void>(`/chat/threads/${threadId}`, {
      method: "DELETE",
    });
  },

  // --- Health ---

  healthCheck(): Promise<{ status: string; environment: string }> {
    return http("/health", { skipAuth: true });
  },
} as const;

