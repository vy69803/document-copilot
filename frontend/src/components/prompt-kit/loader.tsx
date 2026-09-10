import { BookOpen, Loader2, Search, ShieldCheck } from "lucide-react";
import { cn } from "@/lib/utils";

export interface LoaderProps {
  variant?: "spinner" | "dots" | "pipeline";
  stage?: "searching" | "analyzing" | "validating" | string;
  message?: string;
  detail?: string;
  className?: string;
}

export function Loader({
  variant = "spinner",
  stage = "searching",
  message,
  detail,
  className,
}: LoaderProps) {
  if (variant === "dots") {
    return (
      <div className={cn("inline-flex items-center gap-1.5 py-1", className)}>
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-foreground/60 [animation-delay:-0.3s]" />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-foreground/60 [animation-delay:-0.15s]" />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-foreground/60" />
      </div>
    );
  }

  if (variant === "spinner") {
    return (
      <div className={cn("flex items-center gap-2 text-xs text-muted-foreground", className)}>
        <Loader2 className="h-4 w-4 animate-spin text-foreground" />
        {message && <span>{message}</span>}
      </div>
    );
  }

  // Pipeline step variant — dedicated to SEC grounding workflow
  const getStageIcon = () => {
    switch (stage) {
      case "searching":
        return <Search className="h-3.5 w-3.5 animate-spin text-foreground shrink-0" />;
      case "analyzing":
        return <BookOpen className="h-3.5 w-3.5 text-foreground shrink-0" />;
      case "validating":
        return <ShieldCheck className="h-3.5 w-3.5 text-foreground shrink-0" />;
      default:
        return <Loader2 className="h-3.5 w-3.5 animate-spin text-foreground shrink-0" />;
    }
  };

  const defaultMessage =
    stage === "searching"
      ? "Searching SEC 10-K filings (pgvector + FTS)..."
      : stage === "analyzing"
      ? "Synthesizing evidence across disclosures..."
      : stage === "validating"
      ? "Validating grounding & source citations..."
      : "Processing query...";

  const defaultDetail =
    stage === "searching"
      ? "Embedding query & executing parallel hybrid search"
      : stage === "analyzing"
      ? "Formulating answer strictly bounded by retrieved 10-K chunks"
      : "Verifying cited passage coordinates";

  return (
    <div
      className={cn(
        "my-2 flex items-start gap-3 rounded-xl border border-border bg-muted/40 p-3 text-xs text-foreground shadow-2xs",
        className
      )}
    >
      <div className="flex h-7 w-7 items-center justify-center rounded-lg border border-border bg-background shadow-xs shrink-0">
        {getStageIcon()}
      </div>
      <div className="flex flex-col gap-0.5 min-w-0">
        <span className="font-medium text-foreground text-xs leading-tight">
          {message || defaultMessage}
        </span>
        <span className="text-[11px] text-muted-foreground">
          {detail || defaultDetail}
        </span>
      </div>
    </div>
  );
}
