/**
 * Chat input box built on prompt-kit PromptInput primitives.
 * Supports auto-expanding textarea, enter submit shortcut, and streaming stop/send controls.
 */

import { ArrowUp, Square } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  PromptInput,
  PromptInputAction,
  PromptInputActions,
  PromptInputTextarea,
} from "@/components/prompt-kit/prompt-input";

interface ChatInputProps {
  onSend: (message: string) => void;
  onStop: () => void;
  isStreaming: boolean;
  disabled?: boolean;
}

export function ChatInput({
  onSend,
  onStop,
  isStreaming,
  disabled = false,
}: ChatInputProps) {
  const [input, setInput] = useState("");

  const handleSubmit = () => {
    const trimmed = input.trim();
    if (!trimmed || isStreaming || disabled) return;

    onSend(trimmed);
    setInput("");
  };

  return (
    <div className="w-full max-w-3xl mx-auto px-4 pb-4 pt-2">
      <PromptInput
        value={input}
        onValueChange={setInput}
        onSubmit={handleSubmit}
        isLoading={isStreaming}
        disabled={disabled}
      >
        <PromptInputTextarea
          placeholder="Ask about Apple, Amazon, Alphabet, Microsoft, or NVIDIA 10-K filings..."
          maxHeight={180}
        />

        <PromptInputActions>
          {isStreaming ? (
            <PromptInputAction tooltip="Stop generating">
              <Button
                type="button"
                size="icon-sm"
                onClick={onStop}
                className="h-7 w-7 rounded-lg bg-foreground text-background hover:bg-foreground/90 transition-transform active:scale-95"
              >
                <Square className="h-3 w-3 fill-current" />
                <span className="sr-only">Stop</span>
              </Button>
            </PromptInputAction>
          ) : (
            <PromptInputAction tooltip="Send message (Enter)">
              <Button
                type="button"
                size="icon-sm"
                onClick={handleSubmit}
                disabled={!input.trim() || disabled}
                className="h-7 w-7 rounded-lg bg-foreground text-background hover:bg-foreground/90 disabled:opacity-30 transition-all active:scale-95 shadow-2xs"
              >
                <ArrowUp className="h-3.5 w-3.5" />
                <span className="sr-only">Send</span>
              </Button>
            </PromptInputAction>
          )}
        </PromptInputActions>
      </PromptInput>

      {/* Trust Notice */}
      <p className="mt-2 text-center text-[11px] text-muted-foreground">
        Every claim is grounded in SEC 10-K filings. Verify figures using source citations.
      </p>
    </div>
  );
}
