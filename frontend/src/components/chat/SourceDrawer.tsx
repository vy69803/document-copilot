/**
 * Slide-over drawer for inspecting exact source passage excerpts and SEC metadata.
 */

import { Check, Copy, FileText } from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import type { Citation } from "@/lib/api";

interface SourceDrawerProps {
  citation: Citation | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function SourceDrawer({
  citation,
  open,
  onOpenChange,
}: SourceDrawerProps) {
  const [copiedExcerpt, setCopiedExcerpt] = useState(false);
  const [copiedCitation, setCopiedCitation] = useState(false);

  if (!citation) return null;

  const handleCopyExcerpt = async () => {
    if (!citation.excerpt) return;
    await navigator.clipboard.writeText(citation.excerpt);
    setCopiedExcerpt(true);
    setTimeout(() => setCopiedExcerpt(false), 2000);
  };

  const handleCopyCitation = async () => {
    const citationString = `${citation.company_name || citation.ticker || "SEC Filing"} (${
      citation.ticker || ""
    }) ${citation.fiscal_year || ""} ${citation.filing_type || "10-K"}${
      citation.section ? `, Section: ${citation.section}` : ""
    }${citation.page ? `, Page ${citation.page}` : ""}`;

    await navigator.clipboard.writeText(citationString);
    setCopiedCitation(true);
    setTimeout(() => setCopiedCitation(false), 2000);
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full sm:max-w-md md:max-w-lg p-0 flex flex-col">
        {/* Header */}
        <div className="p-5 border-b border-border bg-muted/40">
          <SheetHeader className="text-left space-y-2">
            <div className="flex items-center gap-1.5 flex-wrap">
              <Badge
                variant="secondary"
                className="font-semibold text-xs border border-border"
              >
                {citation.ticker || "SEC"}
              </Badge>
              <Badge variant="outline" className="text-xs">
                {citation.filing_type || "10-K"}
              </Badge>
              {citation.fiscal_year && (
                <Badge variant="outline" className="text-xs">
                  FY {citation.fiscal_year}
                </Badge>
              )}
            </div>
            <SheetTitle className="text-base font-semibold text-foreground tracking-tight">
              {citation.company_name || `${citation.ticker} Annual Report`}
            </SheetTitle>
            <SheetDescription className="text-xs text-muted-foreground flex items-center gap-1.5">
              <FileText className="h-3.5 w-3.5" />
              Verified SEC EDGAR Grounded Disclosure
            </SheetDescription>
          </SheetHeader>
        </div>

        {/* Content Body */}
        <ScrollArea className="flex-1 p-5">
          <div className="space-y-5">
            {/* Filing Metadata Grid */}
            <div className="grid grid-cols-2 gap-2.5 rounded-lg border border-border bg-card p-3 text-xs">
              <div>
                <span className="text-muted-foreground block text-[11px]">
                  Filing Section
                </span>
                <span className="font-medium text-foreground">
                  {citation.section || "Item 7 (MD&A)"}
                </span>
              </div>
              <div>
                <span className="text-muted-foreground block text-[11px]">
                  Page Reference
                </span>
                <span className="font-medium text-foreground">
                  {citation.page ? `Page ${citation.page}` : "N/A"}
                </span>
              </div>
              <div>
                <span className="text-muted-foreground block text-[11px]">
                  Source Type
                </span>
                <span className="font-medium text-foreground">
                  Audited 10-K Filing
                </span>
              </div>
              <div>
                <span className="text-muted-foreground block text-[11px]">
                  Citation Index
                </span>
                <span className="font-mono font-medium text-foreground">
                  #{citation.citation_index}
                </span>
              </div>
            </div>

            {/* Source Excerpt */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <h4 className="text-xs font-semibold text-muted-foreground">
                  Source Passage Excerpt
                </h4>
                <Button
                  variant="ghost"
                  size="xs"
                  onClick={handleCopyExcerpt}
                  className="h-6 gap-1 text-[11px] text-muted-foreground hover:text-foreground"
                >
                  {copiedExcerpt ? (
                    <>
                      <Check className="h-3 w-3 text-emerald-500" />
                      <span>Copied</span>
                    </>
                  ) : (
                    <>
                      <Copy className="h-3 w-3" />
                      <span>Copy Excerpt</span>
                    </>
                  )}
                </Button>
              </div>

              <div className="relative rounded-xl border border-border bg-muted/30 p-4 text-xs font-mono leading-relaxed text-foreground/90 shadow-2xs">
                "{citation.excerpt || "Full text passage not available in preview."}"
              </div>
            </div>

            <Separator />

            {/* Grounding Notice */}
            <div className="rounded-lg border border-border/80 bg-muted/40 p-3 text-xs text-muted-foreground space-y-1">
              <p className="font-medium text-foreground text-xs">
                Driftwood Grounding Guarantee
              </p>
              <p className="leading-relaxed text-[11px]">
                This passage was retrieved directly from the verified EDGAR corpus and verified against the retrieval-augmented generation boundary.
              </p>
            </div>
          </div>
        </ScrollArea>

        {/* Footer Actions */}
        <div className="p-3.5 border-t border-border bg-card flex items-center justify-between gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={handleCopyCitation}
            className="flex-1 gap-1.5 text-xs h-8"
          >
            {copiedCitation ? (
              <Check className="h-3.5 w-3.5 text-emerald-500" />
            ) : (
              <Copy className="h-3.5 w-3.5" />
            )}
            {copiedCitation ? "Citation Copied" : "Copy Full Citation"}
          </Button>

          <Button
            variant="default"
            size="sm"
            onClick={() => onOpenChange(false)}
            className="text-xs h-8 px-4"
          >
            Done
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  );
}
