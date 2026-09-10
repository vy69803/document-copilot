/**
 * Empty state shown when starting a new research conversation.
 * Presents curated starter prompts from Driftwood Capital's SEC filing corpus
 * using prompt-kit PromptSuggestion primitives.
 */

import { Building2, Cpu, FileText, Layers, ShieldAlert, TrendingUp } from "lucide-react";
import { PromptSuggestion } from "@/components/prompt-kit/prompt-suggestion";

interface EmptyStateProps {
  onSelectPrompt: (prompt: string) => void;
}

const SUGGESTED_PROMPTS = [
  {
    icon: TrendingUp,
    title: "Apple Revenue Mix Shift",
    prompt:
      "Across Apple's 2021–2025 10-Ks, how did the revenue mix between iPhone, Services, Mac, iPad, and Wearables change?",
  },
  {
    icon: Building2,
    title: "AWS Operating Margins",
    prompt:
      "For Amazon, compare AWS operating income and margin against North America and International from 2021 to 2025.",
  },
  {
    icon: Cpu,
    title: "NVIDIA Data Center Demand",
    prompt:
      "How did NVIDIA describe demand drivers, customer concentration, and supply constraints for Data Center from 2021 to 2025?",
  },
  {
    icon: Layers,
    title: "Microsoft Azure & Cloud Capacity",
    prompt:
      "Across Microsoft's 2021–2025 filings, what changed in the way the company describes Azure, AI infrastructure, and cloud capacity?",
  },
  {
    icon: ShieldAlert,
    title: "AI Risk Factor Evolution",
    prompt:
      "Which of the 5 companies materially changed risk-factor language related to AI, export controls, or supply chain between 2021 and 2025?",
  },
  {
    icon: FileText,
    title: "Hyperscaler CapEx Trends",
    prompt:
      "Compare capital expenditures and purchase commitments for Microsoft, Alphabet, Amazon, and NVIDIA.",
  },
];

export function EmptyState({ onSelectPrompt }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[80%] max-w-3xl mx-auto px-4 py-8 text-center animate-in fade-in duration-300">
      {/* Brand icon */}
      <div className="inline-flex items-center justify-center h-12 w-12 mb-4 rounded-xl border border-border bg-card text-foreground shadow-xs">
        <span className="text-base font-bold tracking-tight">DC</span>
      </div>

      <h2 className="text-xl font-semibold tracking-tight text-foreground sm:text-2xl">
        Driftwood Document Copilot
      </h2>
      <p className="mt-1.5 text-xs text-muted-foreground max-w-md leading-relaxed">
        Grounded research copilot for audited 10-K disclosures (2021–2025) across Apple, Amazon, Alphabet, Microsoft, and NVIDIA.
      </p>

      {/* Suggestion Prompts Grid using PromptSuggestion primitive */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5 mt-8 w-full text-left">
        {SUGGESTED_PROMPTS.map((item, idx) => (
          <PromptSuggestion
            key={idx}
            icon={item.icon}
            title={item.title}
            description={item.prompt}
            onClick={() => onSelectPrompt(item.prompt)}
          />
        ))}
      </div>
    </div>
  );
}
