import type { ComponentType } from "react";
import { cn } from "@/lib/utils";

export interface PromptSuggestionProps {
  title: string;
  description?: string;
  icon?: ComponentType<{ className?: string }>;
  onClick: () => void;
  className?: string;
}

export function PromptSuggestion({
  title,
  description,
  icon: Icon,
  onClick,
  className,
}: PromptSuggestionProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "group flex w-full items-start gap-3 rounded-xl border border-border bg-card/60 p-3.5 text-left shadow-2xs transition-all",
        "hover:border-foreground/30 hover:bg-muted/60 active:scale-[0.99] cursor-pointer",
        "focus-visible:border-foreground focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-foreground/20",
        className
      )}
    >
      {Icon && (
        <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-border bg-background text-foreground shrink-0 group-hover:scale-105 transition-transform">
          <Icon className="h-4 w-4" />
        </div>
      )}
      <div className="flex-1 min-w-0">
        <h3 className="text-xs font-semibold text-foreground group-hover:text-foreground">
          {title}
        </h3>
        {description && (
          <p className="mt-0.5 text-xs text-muted-foreground line-clamp-2 leading-relaxed">
            {description}
          </p>
        )}
      </div>
    </button>
  );
}
