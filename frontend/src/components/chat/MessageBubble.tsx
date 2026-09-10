/**
 * Renders individual user and assistant messages with markdown formatting
 * and interactive citation badges, using prompt-kit primitives.
 */

import { useState } from "react";
import {
  Check,
  Copy,
  FileText,
  ShieldAlert,
  Sparkles,
  User,
} from "lucide-react";

import { CitationBadge } from "@/components/chat/CitationBadge";
import { StreamingStatus } from "@/components/chat/StreamingStatus";
import {
  Message,
  MessageAction,
  MessageActions,
  MessageAvatar,
  MessageContent,
} from "@/components/prompt-kit/message";
import { Markdown } from "@/components/prompt-kit/markdown";
import type { PipelineStatus } from "@/hooks/useChatStream";
import type { ChatMessage, Citation } from "@/lib/api";

interface MessageBubbleProps {
  message: ChatMessage;
  onCitationClick: (citation: Citation) => void;
  isStreaming?: boolean;
  pipelineStatus?: PipelineStatus | null;
}

export function MessageBubble({
  message,
  onCitationClick,
  isStreaming = false,
  pipelineStatus = null,
}: MessageBubbleProps) {
  const isUser = message.role === "user";
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    if (!message.content) return;
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (isUser) {
    return (
      <Message role="user">
        <MessageContent>
          <p className="whitespace-pre-wrap break-words">{message.content}</p>
        </MessageContent>
        <MessageAvatar
          icon={<User className="h-3.5 w-3.5" />}
          fallback="U"
        />
      </Message>
    );
  }

  const isRefusal =
    !isUser &&
    Boolean(message.content) &&
    (message.content.includes("do not contain sufficient information") ||
      message.content.includes("not mentioned in the available filings") ||
      message.content.includes("insufficient information to answer"));

  return (
    <Message role="assistant">
      <MessageAvatar
        icon={<Sparkles className="h-3.5 w-3.5" />}
        fallback="DC"
      />

      <div className="flex-1 min-w-0 max-w-[95%] md:max-w-[85%]">
        <MessageContent className="max-w-full">
          {isRefusal && (
            <div className="mb-3 flex items-center gap-1.5 rounded-lg border border-border bg-muted/60 px-2.5 py-1 text-xs text-foreground font-medium w-fit">
              <ShieldAlert className="h-3.5 w-3.5 text-muted-foreground" />
              <span>Corpus Boundary — Strict Grounded Refusal</span>
            </div>
          )}

          {/* Streaming Pipeline Status Indicator */}
          {isStreaming && !message.content && (
            <StreamingStatus status={pipelineStatus} />
          )}

          {/* Response text formatted via prompt-kit Markdown */}
          {message.content ? (
            <div>
              <Markdown content={message.content} />

              {isStreaming && pipelineStatus?.stage === "validating" && (
                <div className="mt-3 pt-2 border-t border-border/40 text-xs text-muted-foreground flex items-center gap-2">
                  <span className="h-1.5 w-1.5 rounded-full bg-foreground animate-pulse" />
                  <span>{pipelineStatus.message || "Validating citations & grounding..."}</span>
                </div>
              )}
            </div>
          ) : null}

          {/* Citations Shelf */}
          {message.citations && message.citations.length > 0 && (
            <div className="mt-4 pt-3 border-t border-border/60">
              <div className="flex items-center gap-1.5 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                <FileText className="h-3.5 w-3.5" />
                Source Citations ({message.citations.length})
              </div>
              <div className="flex flex-wrap gap-1.5">
                {message.citations.map((cit, idx) => (
                  <CitationBadge
                    key={idx}
                    citation={cit}
                    onClick={() => onCitationClick(cit)}
                  />
                ))}
              </div>
            </div>
          )}
        </MessageContent>

        {/* Hover Action Bar */}
        {message.content && !isStreaming && (
          <MessageActions>
            <MessageAction
              tooltip="Copy response"
              onClick={handleCopy}
              icon={
                copied ? (
                  <Check className="h-3.5 w-3.5 text-emerald-500" />
                ) : (
                  <Copy className="h-3.5 w-3.5" />
                )
              }
              label={copied ? "Copied" : "Copy"}
            />
          </MessageActions>
        )}
      </div>
    </Message>
  );
}
