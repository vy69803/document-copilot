import { ArrowDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

export interface ScrollButtonProps {
  visible: boolean;
  onClick: () => void;
  className?: string;
  label?: string;
}

export function ScrollButton({
  visible,
  onClick,
  className,
  label = "Scroll to bottom",
}: ScrollButtonProps) {
  if (!visible) return null;

  return (
    <Button
      variant="outline"
      size="icon-sm"
      onClick={onClick}
      title={label}
      aria-label={label}
      className={cn(
        "fixed bottom-24 right-8 z-30 h-8 w-8 rounded-full border border-border bg-background/90 text-foreground shadow-md backdrop-blur-xs transition-all hover:bg-muted active:scale-95 animate-in fade-in zoom-in-95",
        className
      )}
    >
      <ArrowDown className="h-4 w-4" />
    </Button>
  );
}
