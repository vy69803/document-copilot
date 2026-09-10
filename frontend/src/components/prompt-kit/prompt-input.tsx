import {
  type ChangeEvent,
  type KeyboardEvent,
  type ReactNode,
  createContext,
  useContext,
  useRef,
} from "react";
import { cn } from "@/lib/utils";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface PromptInputContextValue {
  value: string;
  setValue: (value: string) => void;
  onSubmit?: () => void;
  isLoading?: boolean;
  disabled?: boolean;
}

const PromptInputContext = createContext<PromptInputContextValue | null>(null);

export function usePromptInput() {
  const ctx = useContext(PromptInputContext);
  if (!ctx) {
    throw new Error("usePromptInput must be used within a PromptInput");
  }
  return ctx;
}

export interface PromptInputProps {
  value: string;
  onValueChange: (value: string) => void;
  onSubmit?: () => void;
  isLoading?: boolean;
  disabled?: boolean;
  className?: string;
  children: ReactNode;
}

export function PromptInput({
  value,
  onValueChange,
  onSubmit,
  isLoading = false,
  disabled = false,
  className,
  children,
}: PromptInputProps) {
  return (
    <PromptInputContext.Provider
      value={{
        value,
        setValue: onValueChange,
        onSubmit,
        isLoading,
        disabled,
      }}
    >
      <div
        className={cn(
          "relative flex flex-col rounded-2xl border border-border bg-card text-card-foreground shadow-xs transition-all",
          "focus-within:border-foreground/40 focus-within:ring-1 focus-within:ring-foreground/20",
          disabled && "opacity-60 pointer-events-none",
          className
        )}
      >
        {children}
      </div>
    </PromptInputContext.Provider>
  );
}

export interface PromptInputTextareaProps {
  placeholder?: string;
  maxHeight?: number;
  className?: string;
  autoFocus?: boolean;
}

export function PromptInputTextarea({
  placeholder = "Ask a question...",
  maxHeight = 200,
  className,
  autoFocus,
}: PromptInputTextareaProps) {
  const { value, setValue, onSubmit, isLoading, disabled } = usePromptInput();
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const adjustHeight = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, maxHeight)}px`;
  };

  const handleChange = (e: ChangeEvent<HTMLTextAreaElement>) => {
    setValue(e.target.value);
    adjustHeight();
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!isLoading && !disabled && value.trim()) {
        onSubmit?.();
      }
    }
  };

  return (
    <textarea
      ref={textareaRef}
      value={value}
      onChange={handleChange}
      onKeyDown={handleKeyDown}
      placeholder={placeholder}
      rows={1}
      autoFocus={autoFocus}
      disabled={disabled}
      className={cn(
        "w-full resize-none bg-transparent px-4 pt-3.5 pb-12 text-sm text-foreground placeholder:text-muted-foreground focus:outline-hidden leading-relaxed",
        className
      )}
    />
  );
}

export interface PromptInputActionsProps {
  className?: string;
  children: ReactNode;
}

export function PromptInputActions({
  className,
  children,
}: PromptInputActionsProps) {
  return (
    <div
      className={cn(
        "absolute right-2.5 bottom-2.5 flex items-center gap-1.5",
        className
      )}
    >
      {children}
    </div>
  );
}

export interface PromptInputActionProps {
  tooltip?: string;
  children: ReactNode;
  className?: string;
}

export function PromptInputAction({
  tooltip,
  children,
  className,
}: PromptInputActionProps) {
  if (!tooltip) {
    return <div className={className}>{children}</div>;
  }

  return (
    <Tooltip>
      <TooltipTrigger render={<div className={className}>{children}</div>} />
      <TooltipContent side="top" className="text-xs">
        {tooltip}
      </TooltipContent>
    </Tooltip>
  );
}
