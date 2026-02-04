"use client";

/**
 * AppSidebar - Left navigation sidebar (ChatGPT/Claude style)
 *
 * Features:
 * - Collapsible (220px ↔ 60px)
 * - New chat button with accent color
 * - Navigation items with tooltips when collapsed
 * - User button (Clerk)
 */

import { UserButton } from "@clerk/nextjs";
import {
  MessageSquarePlus,
  Settings,
  Sparkles,
  PanelLeftClose,
  PanelLeftOpen,
  LayoutDashboard,
} from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import Link from "next/link";

export type SidebarView = "chat" | "dashboard" | "settings";

interface Props {
  currentView: SidebarView;
  onViewChange?: (view: SidebarView) => void;
  onNewConversation: () => void;
  collapsed: boolean;
  onCollapsedChange: (collapsed: boolean) => void;
}

interface NavItemProps {
  icon: React.ReactNode;
  label: string;
  active: boolean;
  onClick?: () => void;
  href?: string;
  collapsed: boolean;
  accent?: boolean;
}

function NavItem({ icon, label, active, onClick, href, collapsed, accent }: NavItemProps) {
  const baseClassName = `
    group flex items-center w-full rounded-lg transition-all duration-200 cursor-pointer
    ${collapsed ? "justify-center h-10 w-10 mx-auto" : "gap-3 px-3 h-10"}
    ${
      active
        ? "bg-[#1a1a2e] text-white shadow-sm shadow-[#1a1a2e]/15"
        : accent
          ? "text-[#e94560] hover:bg-[#e94560]/8"
          : "text-[#6b7280] hover:bg-[#f0f1f5] hover:text-[#1a1a2e]"
    }
  `;

  const content = (
    <>
      <span className="shrink-0">{icon}</span>
      {!collapsed && (
        <span className="text-[13px] font-medium tracking-tight truncate">{label}</span>
      )}
    </>
  );

  const button = href ? (
    <Link href={href} className={baseClassName}>
      {content}
    </Link>
  ) : (
    <button onClick={onClick} className={baseClassName}>
      {content}
    </button>
  );

  if (collapsed) {
    return (
      <Tooltip delayDuration={0}>
        <TooltipTrigger asChild>{button}</TooltipTrigger>
        <TooltipContent side="right" sideOffset={8}>
          <p className="text-xs">{label}</p>
        </TooltipContent>
      </Tooltip>
    );
  }

  return button;
}

export function AppSidebar({
  currentView,
  onViewChange,
  onNewConversation,
  collapsed,
  onCollapsedChange,
}: Props) {
  return (
    <TooltipProvider>
      <aside
        className={`
          hidden md:flex flex-col bg-white border-r border-[#e5e7eb] h-full
          transition-[width] duration-300 ease-in-out shrink-0
          ${collapsed ? "w-[60px]" : "w-[220px]"}
        `}
      >
        {/* Brand + Collapse toggle */}
        <div
          className={`
            flex items-center h-14 shrink-0
            ${collapsed ? "justify-center px-0" : "px-4 justify-between"}
          `}
        >
          {collapsed ? (
            /* Collapsed: expand button */
            <Tooltip delayDuration={0}>
              <TooltipTrigger asChild>
                <button
                  onClick={() => onCollapsedChange(false)}
                  className="w-8 h-8 flex items-center justify-center rounded-lg text-[#9ca3af] hover:text-[#1a1a2e] hover:bg-[#f0f1f5] transition-all duration-200 cursor-pointer"
                >
                  <PanelLeftOpen className="w-[18px] h-[18px]" />
                </button>
              </TooltipTrigger>
              <TooltipContent side="right" sideOffset={8}>
                <p className="text-xs">サイドバーを開く</p>
              </TooltipContent>
            </Tooltip>
          ) : (
            /* Expanded: brand + collapse button */
            <>
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-gradient-to-br from-[#1a1a2e] to-[#2d2d52] rounded-lg flex items-center justify-center shrink-0 shadow-sm">
                  <Sparkles className="w-4 h-4 text-white" />
                </div>
                <div className="flex flex-col min-w-0">
                  <span className="text-[13px] font-bold text-[#1a1a2e] tracking-tight leading-tight">
                    Marketing AI
                  </span>
                  <span className="text-[10px] text-[#9ca3af] leading-tight">
                    SEO & Analytics
                  </span>
                </div>
              </div>
              <Tooltip delayDuration={0}>
                <TooltipTrigger asChild>
                  <button
                    onClick={() => onCollapsedChange(true)}
                    className="w-7 h-7 flex items-center justify-center rounded-md text-[#9ca3af] hover:text-[#1a1a2e] hover:bg-[#f0f1f5] transition-all duration-200 cursor-pointer"
                  >
                    <PanelLeftClose className="w-4 h-4" />
                  </button>
                </TooltipTrigger>
                <TooltipContent side="right" sideOffset={4}>
                  <p className="text-xs">折りたたむ</p>
                </TooltipContent>
              </Tooltip>
            </>
          )}
        </div>

        {/* Separator */}
        <div className={`mx-3 h-px bg-[#e5e7eb] shrink-0`} />

        {/* Navigation */}
        <nav className={`flex-1 py-3 space-y-1 ${collapsed ? "px-[10px]" : "px-3"}`}>
          {/* New conversation */}
          <NavItem
            icon={<MessageSquarePlus className="w-[18px] h-[18px]" />}
            label="新しいチャット"
            active={false}
            accent
            onClick={() => {
              onViewChange?.("chat");
              onNewConversation();
            }}
            collapsed={collapsed}
          />

          <div className={`h-px bg-[#f0f1f5] my-2 ${collapsed ? "mx-1" : "mx-0"}`} />

          {/* Chat */}
          <NavItem
            icon={<Sparkles className="w-[18px] h-[18px]" />}
            label="チャット"
            active={currentView === "chat"}
            onClick={() => onViewChange?.("chat")}
            collapsed={collapsed}
          />

          {/* Dashboard */}
          <NavItem
            icon={<LayoutDashboard className="w-[18px] h-[18px]" />}
            label="ダッシュボード"
            active={currentView === "dashboard"}
            href="/marketing/dashboard"
            collapsed={collapsed}
          />

          {/* Settings */}
          <NavItem
            icon={<Settings className="w-[18px] h-[18px]" />}
            label="設定"
            active={currentView === "settings"}
            onClick={() => onViewChange?.("settings")}
            collapsed={collapsed}
          />
        </nav>

        {/* Separator */}
        <div className={`mx-3 h-px bg-[#e5e7eb] shrink-0`} />

        {/* Bottom: User */}
        <div className={`py-3 space-y-2 ${collapsed ? "px-[10px]" : "px-3"}`}>
          {/* User */}
          <div
            className={`
              flex items-center rounded-lg
              ${collapsed ? "justify-center py-1" : "gap-3 px-3 py-1.5"}
            `}
          >
            <UserButton
              appearance={{
                elements: {
                  avatarBox: "w-8 h-8",
                },
              }}
            />
            {!collapsed && (
              <span className="text-xs text-[#9ca3af] truncate">アカウント</span>
            )}
          </div>
        </div>
      </aside>
    </TooltipProvider>
  );
}
