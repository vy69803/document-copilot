/**
 * Pipeline status component rendered while assistant answers are being generated.
 * Uses prompt-kit Loader primitive with SEC grounding details.
 */

import { Loader } from "@/components/prompt-kit/loader";
import type { PipelineStatus } from "@/hooks/useChatStream";

interface StreamingStatusProps {
  status: PipelineStatus | null;
}

export function StreamingStatus({ status }: StreamingStatusProps) {
  const stage = status?.stage || "searching";
  const message = status?.message || undefined;

  return (
    <Loader
      variant="pipeline"
      stage={stage}
      message={message}
    />
  );
}
