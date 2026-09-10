import { type ReactNode, createContext, useContext } from "react";
import { cn } from "@/lib/utils";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

type MessageRole = "user" | "assistant" | "system";

interface MessageContextValue {
  role: MessageRole;
}

const MessageContext = createContext<MessageContextValue>({ role: "assistant" });

export function useMessage() {
  return useContext(MessageContext);
}

export interface MessageProps {
  role: MessageRole;
  className?: string;
  children: ReactNode;
}

export function Message({ role, className, children }: MessageProps) {
  return (
    <MessageContext.Provider value={{ role }}>
      <div
        className={cn(
          "group relative flex w-full gap-3 px-4 py-3 transition-colors",
          role === "user" ? "justify-end" : "justify-start",
          className
        )}
      >
        {children}
      </div>
    </MessageContext.Provider>
  );
}

export interface MessageAvatarProps {
  icon?: ReactNode;
  fallback?: string;
  className?: string;
}

export function MessageAvatar({
  icon,
  fallback = "AI",
  className,
}: MessageAvatarProps) {
  const { role } = useMessage();

  return (
    <Avatar
      className={cn(
        "h-7 w-7 shrink-0 rounded-lg border border-border shadow-xs",
        role === "user"
          ? "bg-foreground text-background"
          : "bg-muted text-foreground",
        className
      )}
    >
      <AvatarFallback className="text-[11px] font-semibold">
        {icon || fallback}
      </AvatarFallback>
    </Avatar>
  );
}

export interface MessageContentProps {
  className?: string;
  children: ReactNode;
}

export function MessageContent({ className, children }: MessageContentProps) {
  const { role } = useMessage();

  return (
    <div
      className={cn(
        "relative rounded-2xl p-4 text-sm leading-relaxed shadow-2xs transition-all",
        role === "user"
          ? "max-w-[80%] md:max-w-[70%] rounded-tr-xs bg-primary text-primary-foreground"
          : "max-w-[95%] md:max-w-[85%] rounded-tl-xs border border-border bg-card text-card-foreground",
        className
      )}
    >
      {children}
    </div>
  );
}

export interface MessageActionsProps {
  className?: string;
  children: ReactNode;
}

export function MessageActions({ className, children }: MessageActionsProps) {
  return (
    <div
      className={cn(
        "mt-2 flex items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100",
        className
      )}
    >
      {children}
    </div>
  );
}

export interface MessageActionProps {
  tooltip?: string;
  onClick: () => void;
  icon: ReactNode;
  label?: string;
  className?: string;
}

export function MessageAction({
  tooltip,
  onClick,
  icon,
  label,
  className,
}: MessageActionProps) {
  const button = (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "inline-flex items-center gap-1 rounded-md px-1.5 py-1 text-xs text-muted-foreground hover:bg-muted hover:text-foreground transition-colors cursor-pointer",
        className
      )}
    >
      {icon}
      {label && <span>{label}</span>}
    </button>
  );

  if (!tooltip) return button;

  return (
    <Tooltip>
      <TooltipTrigger render={button} />
      <TooltipContent side="bottom" className="text-xs">
        {tooltip}
      </TooltipContent>
    </Tooltip>
  );
}
