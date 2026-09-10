/**
 * Main chat route component supporting active and new thread workflows.
 */

import { useNavigate, useParams } from "react-router-dom";

import { ChatContainer } from "@/components/chat/ChatContainer";

export function ChatPage() {
  const { threadId } = useParams<{ threadId?: string }>();
  const navigate = useNavigate();

  const handleThreadCreated = (newThreadId: string) => {
    navigate(`/chat/${newThreadId}`, { replace: true });
  };

  return (
    <ChatContainer
      threadId={threadId}
      onThreadCreated={handleThreadCreated}
    />
  );
}
