/**
 * Interactive inline citation badge for assistant messages.
 * Uses prompt-kit Source primitive.
 */

import { Source } from "@/components/prompt-kit/source";
import type { Citation } from "@/lib/api";

interface CitationBadgeProps {
  citation: Citation;
  onClick: () => void;
}

export function CitationBadge({ citation, onClick }: CitationBadgeProps) {
  const labelParts = [
    citation.ticker || "SEC",
    citation.fiscal_year ? `${citation.fiscal_year}` : "",
    citation.filing_type || "10-K",
    citation.section ? `§ ${citation.section}` : citation.page ? `p. ${citation.page}` : "",
  ].filter(Boolean);

  const label = labelParts.join(" ");
  const title = citation.company_name || citation.ticker || "SEC Source Filing";

  return (
    <Source
      label={label}
      title={title}
      excerpt={citation.excerpt}
      onClick={onClick}
    />
  );
}
