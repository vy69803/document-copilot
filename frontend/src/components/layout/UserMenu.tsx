import { LogOut, Moon, MoreVertical, Sun, UserCheck } from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useAuth } from "@/lib/auth";
import { useTheme } from "@/hooks/useTheme";

export interface UserMenuProps {
  isCollapsed?: boolean;
}

export function UserMenu({ isCollapsed = false }: UserMenuProps) {
  const { user, signOut } = useAuth();
  const { theme, toggleTheme } = useTheme();

  const userInitials = user?.email
    ? user.email.slice(0, 2).toUpperCase()
    : "DC";

  const trigger = isCollapsed ? (
    <Button
      variant="ghost"
      size="icon-sm"
      className="h-9 w-9 rounded-lg hover:bg-sidebar-accent"
      aria-label="User settings"
    >
      <Avatar className="h-7 w-7 rounded-md border border-border">
        <AvatarFallback className="bg-muted text-[11px] font-semibold text-foreground">
          {userInitials}
        </AvatarFallback>
      </Avatar>
    </Button>
  ) : (
    <button
      type="button"
      className="flex w-full items-center justify-between gap-2.5 rounded-lg border border-sidebar-border bg-sidebar-accent/30 p-2 text-left hover:bg-sidebar-accent/70 transition-colors cursor-pointer outline-hidden focus-visible:ring-1 focus-visible:ring-ring"
    >
      <div className="flex items-center gap-2.5 min-w-0">
        <Avatar className="h-7 w-7 rounded-md border border-border shrink-0">
          <AvatarFallback className="bg-muted text-[11px] font-semibold text-foreground">
            {userInitials}
          </AvatarFallback>
        </Avatar>
        <div className="min-w-0 flex-1">
          <p className="truncate text-xs font-medium text-sidebar-foreground">
            {user?.email || "analyst@driftwood.com"}
          </p>
          <p className="text-[10px] text-muted-foreground">Analyst</p>
        </div>
      </div>
      <MoreVertical className="h-4 w-4 text-muted-foreground shrink-0" />
    </button>
  );

  return (
    <DropdownMenu>
      {isCollapsed ? (
        <Tooltip>
          <TooltipTrigger render={<DropdownMenuTrigger render={trigger} />} />
          <TooltipContent side="right" className="text-xs">
            {user?.email}
          </TooltipContent>
        </Tooltip>
      ) : (
        <DropdownMenuTrigger render={trigger} />
      )}

      <DropdownMenuContent
        side={isCollapsed ? "right" : "top"}
        align={isCollapsed ? "end" : "start"}
        className="w-56"
      >
        <DropdownMenuGroup>
          <DropdownMenuLabel className="font-normal">
            <div className="flex flex-col space-y-1">
              <p className="text-xs font-medium leading-none text-foreground">
                {user?.email}
              </p>
              <div className="flex items-center gap-1 text-[10px] text-muted-foreground">
                <UserCheck className="h-3 w-3" />
                <span>SEC Research Analyst</span>
              </div>
            </div>
          </DropdownMenuLabel>
        </DropdownMenuGroup>
        <DropdownMenuSeparator />

        <DropdownMenuItem onClick={toggleTheme} className="cursor-pointer">
          {theme === "dark" ? (
            <>
              <Sun className="h-4 w-4 mr-2" />
              <span>Light Mode</span>
            </>
          ) : (
            <>
              <Moon className="h-4 w-4 mr-2" />
              <span>Dark Mode</span>
            </>
          )}
        </DropdownMenuItem>

        <DropdownMenuSeparator />

        <DropdownMenuItem
          variant="destructive"
          onClick={() => signOut()}
          className="cursor-pointer"
        >
          <LogOut className="h-4 w-4 mr-2" />
          <span>Sign Out</span>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
