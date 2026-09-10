import { useState } from "react";
import { Check, Copy } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

export interface CodeBlockProps {
  code: string;
  language?: string;
  filename?: string;
  className?: string;
}

export function CodeBlock({
  code,
  language,
  filename,
  className,
}: CodeBlockProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      className={cn(
        "group relative my-3 overflow-hidden rounded-xl border border-border bg-muted/40 dark:bg-zinc-950",
        className
      )}
    >
      {(filename || language) && (
        <div className="flex items-center justify-between border-b border-border/60 bg-muted/70 px-3.5 py-1.5 text-xs text-muted-foreground">
          <span className="font-mono text-[11px] font-medium text-foreground">
            {filename || language}
          </span>
          <Button
            variant="ghost"
            size="xs"
            onClick={handleCopy}
            className="h-6 gap-1 text-[11px] text-muted-foreground hover:text-foreground"
          >
            {copied ? (
              <>
                <Check className="h-3 w-3 text-emerald-500" />
                <span>Copied</span>
              </>
            ) : (
              <>
                <Copy className="h-3 w-3" />
                <span>Copy</span>
              </>
            )}
          </Button>
        </div>
      )}

      {!filename && !language && (
        <div className="absolute right-2 top-2 z-10 opacity-0 transition-opacity group-hover:opacity-100">
          <Button
            variant="secondary"
            size="xs"
            onClick={handleCopy}
            className="h-6 gap-1 border border-border bg-background/80 text-[11px] backdrop-blur-xs"
          >
            {copied ? (
              <>
                <Check className="h-3 w-3 text-emerald-500" />
                <span>Copied</span>
              </>
            ) : (
              <>
                <Copy className="h-3 w-3" />
                <span>Copy</span>
              </>
            )}
          </Button>
        </div>
      )}

      <pre className="overflow-x-auto p-4 font-mono text-xs leading-relaxed text-foreground">
        <code>{code}</code>
      </pre>
    </div>
  );
}
