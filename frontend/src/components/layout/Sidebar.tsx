/**
 * Collapsible Sidebar for navigating past research threads and starting new chats.
 */

import { Plus, PanelLeftClose, PanelLeftOpen } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { Button, buttonVariants } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { api, type ChatThread } from "@/lib/api";
import { cn } from "@/lib/utils";
import { DeleteThreadDialog } from "./DeleteThreadDialog";
import { SidebarNav } from "./SidebarNav";
import { UserMenu } from "./UserMenu";

export interface SidebarProps {
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
  onItemClick?: () => void;
}

export function Sidebar({
  isCollapsed = false,
  onToggleCollapse,
  onItemClick,
}: SidebarProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const activeThreadId = location.pathname.startsWith("/chat/")
    ? location.pathname.slice("/chat/".length)
    : undefined;
  const [threads, setThreads] = useState<ChatThread[]>([]);
  const [loading, setLoading] = useState(true);
  const [threadToDelete, setThreadToDelete] = useState<ChatThread | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    let ignore = false;
    api
      .listThreads()
      .then((data) => {
        if (!ignore) {
          setThreads(data);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (!ignore) {
          console.error("Failed to load threads", err);
          setLoading(false);
        }
      });

    return () => {
      ignore = true;
    };
  }, [activeThreadId]);

  const handlePromptDelete = (thread: ChatThread) => {
    setThreadToDelete(thread);
  };

  const handleConfirmDelete = async () => {
    if (!threadToDelete) return;
    setIsDeleting(true);
    try {
      await api.deleteThread(threadToDelete.id);
      // Remove from threads list immediately
      setThreads((prev) => prev.filter((t) => t.id !== threadToDelete.id));

      // If active conversation was deleted, route back to new chat
      if (activeThreadId === threadToDelete.id) {
        navigate("/chat", { replace: true });
      }
      setThreadToDelete(null);
    } catch (err) {
      console.error("Failed to delete thread", err);
    } finally {
      setIsDeleting(false);
    }
  };

  if (isCollapsed) {
    return (
      <aside className="flex h-full w-14 flex-col items-center justify-between border-r border-border bg-sidebar py-3 text-sidebar-foreground">
        {/* Rail Top */}
        <div className="flex flex-col items-center gap-3">
          {/* Brand mark */}
          <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-border bg-foreground font-semibold text-background text-xs shadow-xs">
            DC
          </div>

          {/* Expand Toggle */}
          {onToggleCollapse && (
            <Tooltip>
              <TooltipTrigger
                render={
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    onClick={onToggleCollapse}
                    aria-label="Expand sidebar"
                    className="h-8 w-8 text-muted-foreground hover:text-foreground"
                  >
                    <PanelLeftOpen className="h-4 w-4" />
                  </Button>
                }
              />
              <TooltipContent side="right" className="text-xs">
                Expand sidebar (Ctrl+B)
              </TooltipContent>
            </Tooltip>
          )}

          {/* New Chat Icon Button */}
          <Tooltip>
            <TooltipTrigger
              render={
                <Link
                  to="/chat"
                  onClick={() => onItemClick?.()}
                  className={cn(
                    buttonVariants({ variant: "outline", size: "icon-sm" }),
                    "h-8 w-8 rounded-lg border-border bg-background shadow-xs hover:bg-muted"
                  )}
                >
                  <Plus className="h-4 w-4" />
                  <span className="sr-only">New Research Chat</span>
                </Link>
              }
            />
            <TooltipContent side="right" className="text-xs">
              New Research Chat
            </TooltipContent>
          </Tooltip>
        </div>

        {/* Rail Bottom */}
        <div className="flex flex-col items-center gap-2">
          <Separator className="w-8" />
          <UserMenu isCollapsed={true} />
        </div>
      </aside>
    );
  }

  return (
    <>
      <aside className="flex h-full w-64 flex-col border-r border-border bg-sidebar text-sidebar-foreground">
        {/* Header / Brand */}
        <div className="flex h-14 items-center justify-between px-3.5 border-b border-sidebar-border">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg border border-border bg-foreground font-semibold text-background text-xs shadow-xs shrink-0">
              DC
            </div>
            <div className="min-w-0">
              <h1 className="text-xs font-semibold leading-none tracking-tight text-foreground truncate">
                Document Copilot
              </h1>
              <p className="text-[10px] text-muted-foreground mt-0.5 truncate">
                Driftwood Capital
              </p>
            </div>
          </div>

          {onToggleCollapse && (
            <Tooltip>
              <TooltipTrigger
                render={
                  <Button
                    variant="ghost"
                    size="icon-xs"
                    onClick={onToggleCollapse}
                    aria-label="Collapse sidebar"
                    className="h-7 w-7 text-muted-foreground hover:text-foreground"
                  >
                    <PanelLeftClose className="h-3.5 w-3.5" />
                  </Button>
                }
              />
              <TooltipContent side="right" className="text-xs">
                Collapse sidebar (Ctrl+B)
              </TooltipContent>
            </Tooltip>
          )}
        </div>

        {/* New Chat Button */}
        <div className="p-3">
          <Link
            to="/chat"
            onClick={() => onItemClick?.()}
            className={cn(
              buttonVariants({ variant: "default" }),
              "w-full justify-start gap-2 font-medium text-xs shadow-xs transition-all"
            )}
          >
            <Plus className="h-3.5 w-3.5" />
            New Research Chat
          </Link>
        </div>

        {/* Threads List */}
        <div className="flex-1 overflow-hidden px-2">
          <ScrollArea className="h-[calc(100vh-13rem)]">
            <SidebarNav
              threads={threads}
              activeThreadId={activeThreadId}
              onItemClick={onItemClick}
              onDeleteThread={handlePromptDelete}
              loading={loading}
            />
          </ScrollArea>
        </div>

        <Separator />

        {/* User Profile Footer */}
        <div className="p-2.5">
          <UserMenu isCollapsed={false} />
        </div>
      </aside>

      {/* Delete Confirmation Dialog */}
      <DeleteThreadDialog
        open={Boolean(threadToDelete)}
        thread={threadToDelete}
        isDeleting={isDeleting}
        onConfirm={handleConfirmDelete}
        onCancel={() => setThreadToDelete(null)}
      />
    </>
  );
}
