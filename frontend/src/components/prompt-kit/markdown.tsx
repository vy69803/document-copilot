import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "@/lib/utils";
import { CodeBlock } from "@/components/prompt-kit/code-block";

export interface MarkdownProps {
  content: string;
  className?: string;
}

export function Markdown({ content, className }: MarkdownProps) {
  return (
    <div
      className={cn(
        "prose prose-neutral dark:prose-invert max-w-none text-sm leading-relaxed text-foreground",
        className
      )}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => (
            <h1 className="mt-4 mb-2 text-base font-semibold text-foreground tracking-tight">
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2 className="mt-3 mb-1.5 text-sm font-semibold text-foreground tracking-tight">
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 className="mt-2.5 mb-1 text-xs font-semibold text-foreground uppercase tracking-wider">
              {children}
            </h3>
          ),
          p: ({ children }) => (
            <p className="my-2 leading-relaxed text-foreground/90">{children}</p>
          ),
          ul: ({ children }) => (
            <ul className="my-2 pl-4 list-disc space-y-1 text-foreground/90">
              {children}
            </ul>
          ),
          ol: ({ children }) => (
            <ol className="my-2 pl-4 list-decimal space-y-1 text-foreground/90">
              {children}
            </ol>
          ),
          li: ({ children }) => (
            <li className="leading-relaxed">{children}</li>
          ),
          blockquote: ({ children }) => (
            <blockquote className="my-2.5 border-l-2 border-foreground/30 pl-3 italic text-muted-foreground">
              {children}
            </blockquote>
          ),
          table: ({ children }) => (
            <div className="my-3 overflow-x-auto rounded-lg border border-border">
              <table className="w-full text-left text-xs border-collapse">
                {children}
              </table>
            </div>
          ),
          thead: ({ children }) => (
            <thead className="bg-muted/80 border-b border-border font-medium text-foreground">
              {children}
            </thead>
          ),
          th: ({ children }) => (
            <th className="px-3 py-2 text-foreground font-semibold">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="px-3 py-2 border-b border-border/40 font-mono text-[11px] tabular-nums text-foreground/90">
              {children}
            </td>
          ),
          code: ({ children, className: codeClassName }) => {
            const isInline = !codeClassName;
            if (isInline) {
              return (
                <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-[12px] text-foreground">
                  {children}
                </code>
              );
            }
            const match = /language-(\w+)/.exec(codeClassName || "");
            const language = match ? match[1] : undefined;
            return (
              <CodeBlock
                code={String(children).replace(/\n$/, "")}
                language={language}
              />
            );
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
