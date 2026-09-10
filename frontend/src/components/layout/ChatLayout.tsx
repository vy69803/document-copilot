/**
 * Main application layout with collapsible desktop sidebar and responsive mobile drawer.
 */

import { Menu, PanelLeft } from "lucide-react";
import { useEffect, useState } from "react";
import { Outlet } from "react-router-dom";

import { Sidebar } from "@/components/layout/Sidebar";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

const SIDEBAR_STORAGE_KEY = "dc-sidebar-collapsed";

export function ChatLayout() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(() => {
    return localStorage.getItem(SIDEBAR_STORAGE_KEY) === "true";
  });

  const toggleSidebar = () => {
    setIsCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem(SIDEBAR_STORAGE_KEY, String(next));
      return next;
    });
  };

  // Listen for Ctrl+B / Cmd+B keyboard shortcut to toggle sidebar
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "b") {
        e.preventDefault();
        toggleSidebar();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background">
      {/* Desktop Collapsible Sidebar (visible on md+) */}
      <div className="hidden md:flex md:flex-shrink-0 transition-all duration-200 ease-in-out">
        <Sidebar
          isCollapsed={isCollapsed}
          onToggleCollapse={toggleSidebar}
        />
      </div>

      {/* Main Content Area */}
      <div className="flex flex-1 flex-col overflow-hidden min-w-0">
        {/* Top Header */}
        <header className="flex h-12 items-center justify-between border-b border-border px-4 bg-background/80 backdrop-blur-xs shrink-0">
          {/* Mobile drawer trigger */}
          <div className="flex items-center gap-2 md:hidden">
            <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
              <SheetTrigger
                render={
                  <Button variant="ghost" size="icon-sm" className="h-8 w-8">
                    <Menu className="h-4 w-4" />
                    <span className="sr-only">Toggle Sidebar</span>
                  </Button>
                }
              />
              <SheetContent side="left" className="p-0 w-64">
                <Sidebar onItemClick={() => setMobileOpen(false)} />
              </SheetContent>
            </Sheet>
            <span className="font-semibold text-xs text-foreground">Document Copilot</span>
          </div>

          {/* Desktop header left: Toggle button + title */}
          <div className="hidden md:flex items-center gap-2">
            {isCollapsed && (
              <Tooltip>
                <TooltipTrigger
                  render={
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      onClick={toggleSidebar}
                      aria-label="Expand sidebar"
                      className="h-8 w-8 text-muted-foreground hover:text-foreground"
                    >
                      <PanelLeft className="h-4 w-4" />
                    </Button>
                  }
                />
                <TooltipContent side="bottom" className="text-xs">
                  Expand sidebar (Ctrl+B)
                </TooltipContent>
              </Tooltip>
            )}
            <span className="text-xs font-medium text-muted-foreground">
              Driftwood Capital / SEC 10-K Copilot
            </span>
          </div>

          {/* Header right metadata indicator */}
          <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
            <span className="inline-block h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
            <span className="hidden sm:inline">EDGAR Grounded Corpus</span>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-hidden relative">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
