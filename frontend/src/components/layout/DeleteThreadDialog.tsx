import { useEffect } from "react";
import { Loader2, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { ChatThread } from "@/lib/api";

interface DeleteThreadDialogProps {
  thread: ChatThread | null;
  open: boolean;
  isDeleting: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function DeleteThreadDialog({
  thread,
  open,
  isDeleting,
  onConfirm,
  onCancel,
}: DeleteThreadDialogProps) {
  // Listen for Escape key to dismiss
  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !isDeleting) {
        onCancel();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, isDeleting, onCancel]);

  if (!open || !thread) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        onClick={() => {
          if (!isDeleting) onCancel();
        }}
        className="fixed inset-0 bg-black/60 backdrop-blur-xs transition-opacity animate-in fade-in"
      />

      {/* Modal Dialog Card */}
      <div className="relative z-50 w-full max-w-sm rounded-2xl border border-border bg-card p-5 shadow-lg animate-in fade-in zoom-in-95 duration-150">
        <div className="flex items-start gap-3.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-destructive/20 bg-destructive/10 text-destructive shrink-0">
            <Trash2 className="h-4 w-4" />
          </div>
          <div className="space-y-1 min-w-0">
            <h3 className="text-sm font-semibold tracking-tight text-foreground">
              Delete conversation?
            </h3>
            <p className="text-xs text-muted-foreground leading-relaxed">
              This will permanently delete{" "}
              <span className="font-medium text-foreground">
                "{thread.title || "Untitled Research"}"
              </span>{" "}
              and all of its research citations.
            </p>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="mt-5 flex items-center justify-end gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={onCancel}
            disabled={isDeleting}
            className="text-xs h-8 px-3"
          >
            Cancel
          </Button>
          <Button
            type="button"
            variant="destructive"
            size="sm"
            onClick={onConfirm}
            disabled={isDeleting}
            className="text-xs h-8 px-3 gap-1.5"
          >
            {isDeleting ? (
              <>
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                <span>Deleting…</span>
              </>
            ) : (
              <>
                <Trash2 className="h-3.5 w-3.5" />
                <span>Delete</span>
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}
