/**
 * Scrollable list of chat messages with auto-scrolling and prompt-kit ScrollButton.
 */

import { useEffect, useRef, useState } from "react";

import { MessageBubble } from "@/components/chat/MessageBubble";
import { ScrollButton } from "@/components/prompt-kit/scroll-button";
import type { PipelineStatus } from "@/hooks/useChatStream";
import type { ChatMessage, Citation } from "@/lib/api";

interface MessageListProps {
  messages: ChatMessage[];
  isStreaming: boolean;
  pipelineStatus?: PipelineStatus | null;
  onCitationClick: (citation: Citation) => void;
}

export function MessageList({
  messages,
  isStreaming,
  pipelineStatus = null,
  onCitationClick,
}: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [showScrollBottom, setShowScrollBottom] = useState(false);

  // Auto-scroll when new messages arrive or when streaming if user is near bottom
  useEffect(() => {
    if (!showScrollBottom) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isStreaming, showScrollBottom]);

  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const el = e.currentTarget;
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    setShowScrollBottom(distanceFromBottom > 120);
  };

  const scrollToBottom = () => {
    if (scrollContainerRef.current) {
      scrollContainerRef.current.scrollTo({
        top: scrollContainerRef.current.scrollHeight,
        behavior: "smooth",
      });
    } else {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
    setShowScrollBottom(false);
  };

  return (
    <div
      ref={scrollContainerRef}
      onScroll={handleScroll}
      className="flex-1 min-h-0 w-full overflow-y-auto overflow-x-hidden px-4 py-4"
    >
      <div className="max-w-3xl mx-auto w-full flex flex-col gap-2">
        {messages.map((msg, index) => {
          const isLast = index === messages.length - 1;
          return (
            <MessageBubble
              key={msg.id || index}
              message={msg}
              isStreaming={isLast && isStreaming}
              pipelineStatus={isLast ? pipelineStatus : null}
              onCitationClick={onCitationClick}
            />
          );
        })}
        <div ref={bottomRef} className="h-4 shrink-0" />
      </div>

      {/* Floating jump to bottom button */}
      <ScrollButton
        visible={showScrollBottom}
        onClick={scrollToBottom}
      />
    </div>
  );
}
