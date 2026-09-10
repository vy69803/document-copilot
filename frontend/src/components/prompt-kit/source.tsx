import { BookOpen } from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

export interface SourceProps {
  label: string;
  title?: string;
  excerpt?: string;
  onClick?: () => void;
  className?: string;
}

export function Source({
  label,
  title,
  excerpt,
  onClick,
  className,
}: SourceProps) {
  const content = (
    <button
      type="button"
      onClick={(e) => {
        if (onClick) {
          e.preventDefault();
          e.stopPropagation();
          onClick();
        }
      }}
      className={cn(
        "inline-flex items-baseline align-middle mx-1 cursor-pointer focus:outline-hidden",
        className
      )}
    >
      <Badge
        variant="outline"
        className="gap-1 px-1.5 py-0.5 text-[11px] font-medium border-border bg-muted/60 text-foreground hover:bg-muted hover:border-foreground/40 transition-colors shadow-2xs"
      >
        <BookOpen className="h-2.5 w-2.5 shrink-0 text-muted-foreground" />
        <span>[{label}]</span>
      </Badge>
    </button>
  );

  if (!title && !excerpt) {
    return content;
  }

  return (
    <Tooltip>
      <TooltipTrigger render={content} />
      <TooltipContent
        side="top"
        className="max-w-xs p-2.5 text-xs bg-popover text-popover-foreground border border-border shadow-md"
      >
        {title && <div className="font-semibold text-foreground mb-1">{title}</div>}
        {excerpt && (
          <p className="text-muted-foreground line-clamp-3 italic text-[11px] leading-relaxed">
            "{excerpt}"
          </p>
        )}
        {onClick && (
          <div className="mt-1.5 text-[10px] font-medium text-foreground/80">
            Click to inspect source passage →
          </div>
        )}
      </TooltipContent>
    </Tooltip>
  );
}
