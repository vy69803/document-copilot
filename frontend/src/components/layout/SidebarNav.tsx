import { ChevronRight, MessageSquare, Trash2 } from "lucide-react";
import { Link } from "react-router-dom";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import type { ChatThread } from "@/lib/api";

interface SidebarNavProps {
  threads: ChatThread[];
  activeThreadId?: string;
  onItemClick?: () => void;
  onDeleteThread?: (thread: ChatThread) => void;
  loading?: boolean;
}

interface GroupedThreads {
  today: ChatThread[];
  yesterday: ChatThread[];
  previous7Days: ChatThread[];
  older: ChatThread[];
}

function groupThreads(threads: ChatThread[]): GroupedThreads {
  const groups: GroupedThreads = {
    today: [],
    yesterday: [],
    previous7Days: [],
    older: [],
  };

  const now = new Date();
  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const yesterdayStart = todayStart - 86400000;
  const last7DaysStart = todayStart - 7 * 86400000;

  for (const thread of threads) {
    const threadDate = new Date(thread.updated_at || thread.created_at).getTime();
    if (threadDate >= todayStart) {
      groups.today.push(thread);
    } else if (threadDate >= yesterdayStart) {
      groups.yesterday.push(thread);
    } else if (threadDate >= last7DaysStart) {
      groups.previous7Days.push(thread);
    } else {
      groups.older.push(thread);
    }
  }

  return groups;
}

export function SidebarNav({
  threads,
  activeThreadId,
  onItemClick,
  onDeleteThread,
  loading = false,
}: SidebarNavProps) {
  if (loading && threads.length === 0) {
    return (
      <div className="flex items-center justify-center py-8 text-xs text-muted-foreground">
        Loading conversations…
      </div>
    );
  }

  if (threads.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-10 px-3 text-center">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-sidebar-accent text-muted-foreground mb-2">
          <MessageSquare className="h-4 w-4 opacity-70" />
        </div>
        <p className="text-xs font-medium text-sidebar-foreground">No past chats yet</p>
        <p className="text-[11px] text-muted-foreground mt-0.5 leading-relaxed">
          Ask a question to start exploring SEC filing insights.
        </p>
      </div>
    );
  }

  const grouped = groupThreads(threads);

  const renderSection = (title: string, list: ChatThread[]) => {
    if (list.length === 0) return null;

    return (
      <div key={title} className="mb-4">
        <h3 className="px-2.5 pb-1 text-[11px] font-medium text-muted-foreground">
          {title}
        </h3>
        <div className="space-y-0.5">
          {list.map((thread) => {
            const isActive = thread.id === activeThreadId;
            return (
              <div
                key={thread.id}
                className="group/item relative flex w-full items-center"
              >
                <Link
                  to={`/chat/${thread.id}`}
                  onClick={() => onItemClick?.()}
                  className={`flex w-full items-center gap-2 rounded-md px-2.5 py-1.5 pr-7 text-left text-xs transition-colors ${
                    isActive
                      ? "bg-sidebar-accent text-sidebar-accent-foreground font-medium"
                      : "text-sidebar-foreground/80 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground"
                  }`}
                >
                  <MessageSquare className="h-3.5 w-3.5 shrink-0 text-muted-foreground group-hover/item:text-foreground transition-colors" />
                  <span className="flex-1 truncate">
                    {thread.title || "Untitled Research"}
                  </span>
                  {isActive && (
                    <ChevronRight className="h-3 w-3 text-muted-foreground shrink-0 group-hover/item:opacity-0 transition-opacity" />
                  )}
                </Link>

                {onDeleteThread && (
                  <Tooltip>
                    <TooltipTrigger
                      render={
                        <button
                          type="button"
                          onClick={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            onDeleteThread(thread);
                          }}
                          aria-label={`Delete ${thread.title || "conversation"}`}
                          className="absolute right-1.5 flex h-5 w-5 items-center justify-center rounded text-muted-foreground opacity-0 hover:bg-destructive/10 hover:text-destructive transition-all group-hover/item:opacity-100 cursor-pointer"
                        >
                          <Trash2 className="h-3 w-3" />
                        </button>
                      }
                    />
                    <TooltipContent side="right" className="text-xs">
                      Delete chat
                    </TooltipContent>
                  </Tooltip>
                )}
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  return (
    <div className="p-1">
      {renderSection("Today", grouped.today)}
      {renderSection("Yesterday", grouped.yesterday)}
      {renderSection("Previous 7 Days", grouped.previous7Days)}
      {renderSection("Older", grouped.older)}
    </div>
  );
}
