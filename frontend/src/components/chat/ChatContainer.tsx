/**
 * Main chat container uniting message stream, input controls, empty state,
 * and citation inspection drawer.
 */

import { AlertCircle } from "lucide-react";
import { useState } from "react";

import { ChatInput } from "@/components/chat/ChatInput";
import { EmptyState } from "@/components/chat/EmptyState";
import { MessageList } from "@/components/chat/MessageList";
import { SourceDrawer } from "@/components/chat/SourceDrawer";
import { useChatStream } from "@/hooks/useChatStream";
import type { Citation } from "@/lib/api";

interface ChatContainerProps {
  threadId?: string | null;
  onThreadCreated?: (threadId: string) => void;
}

export function ChatContainer({
  threadId,
  onThreadCreated,
}: ChatContainerProps) {
  const {
    messages,
    isStreaming,
    isLoadingHistory,
    pipelineStatus,
    error,
    sendMessage,
    stop,
  } = useChatStream({
    threadId,
    onThreadCreated,
  });

  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(
    null
  );

  const hasMessages = messages.length > 0;
  const isAuthError =
    Boolean(error) &&
    (error!.toLowerCase().includes("session") ||
      error!.toLowerCase().includes("sign in") ||
      error!.toLowerCase().includes("expired"));

  return (
    <div className="flex h-full w-full flex-col justify-between overflow-hidden bg-background">
      {/* Scrollable Center Area */}
      <div className="flex-1 min-h-0 overflow-hidden relative flex flex-col">
        {isLoadingHistory ? (
          <div className="flex h-full items-center justify-center">
            <div className="flex flex-col items-center gap-2 text-xs text-muted-foreground">
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-border border-t-foreground" />
              <span>Loading conversation…</span>
            </div>
          </div>
        ) : !hasMessages ? (
          <div className="flex-1 min-h-0 w-full overflow-y-auto p-4">
            <EmptyState onSelectPrompt={sendMessage} />
          </div>
        ) : (
          <MessageList
            messages={messages}
            isStreaming={isStreaming}
            pipelineStatus={pipelineStatus}
            onCitationClick={(cit) => setSelectedCitation(cit)}
          />
        )}

        {/* Floating Error Notification */}
        {error && (
          <div className="mx-auto my-2 max-w-lg w-full px-4">
            <div className="flex items-center justify-between gap-3 rounded-xl border border-destructive/30 bg-destructive/10 p-3 text-xs text-destructive shadow-sm animate-in fade-in">
              <div className="flex items-center gap-2">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{error}</span>
              </div>
              {isAuthError && (
                <a
                  href="/login"
                  className="shrink-0 rounded-md bg-destructive px-2.5 py-1 text-[11px] font-medium text-destructive-foreground hover:bg-destructive/90 transition-colors"
                >
                  Sign In
                </a>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Input Bar */}
      <div className="border-t border-border/50 bg-background/80 backdrop-blur-xs shrink-0">
        <ChatInput
          onSend={sendMessage}
          onStop={stop}
          isStreaming={isStreaming}
        />
      </div>

      {/* Source Citation Inspector Drawer */}
      <SourceDrawer
        citation={selectedCitation}
        open={!!selectedCitation}
        onOpenChange={(open) => {
          if (!open) setSelectedCitation(null);
        }}
      />
    </div>
  );
}
