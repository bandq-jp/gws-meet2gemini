"use client";

import { useState } from "react";
import { useAuth, useUser, UserButton } from "@clerk/nextjs";
import { useRouter, usePathname } from "next/navigation";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarRail,
  SidebarTrigger,
  SidebarInset,
} from "@/components/ui/sidebar";
import {
  Users,
  Settings,
  BarChart3,
  Building2,
  Award,
  User,
  LogOut,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

interface ModernAppShellProps {
  children: React.ReactNode;
  activeTab?: string;
}

export function ModernAppShell({ children, activeTab }: ModernAppShellProps) {
  const { signOut } = useAuth();
  const { user } = useUser();
  const router = useRouter();
  const pathname = usePathname();

  const menuItems = [
    {
      title: "ひとキャリ",
      icon: Users,
      href: "/hitocari",
      id: "hitocari",
      enabled: true,
      description: "人材採用・議事録管理",
    },
    {
      title: "モノテック",
      icon: Building2,
      href: "/monotech",
      id: "monotech",
      enabled: false,
      description: "技術・製品管理（開発中）",
    },
    {
      title: "AchieveHR",
      icon: Award,
      href: "/achievehr", 
      id: "achievehr",
      enabled: false,
      description: "人事評価システム（開発中）",
    },
    {
      title: "分析",
      icon: BarChart3,
      href: "/analytics",
      id: "analytics",
      enabled: false,
      description: "データ分析・レポート（開発中）",
    },
  ];

  const handleMenuClick = (item: typeof menuItems[0]) => {
    if (item.enabled) {
      router.push(item.href);
    }
  };

  const handleSignOut = () => {
    signOut(() => router.push("/"));
  };

  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full">
        <Sidebar variant="inset">
          <SidebarHeader className="border-b border-sidebar-border">
            <div className="flex items-center gap-2 px-4 py-2">
              <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                <Building2 className="size-4" />
              </div>
              <div className="grid flex-1 text-left text-sm leading-tight">
                <span className="truncate font-semibold">b&q Hub</span>
                <span className="truncate text-xs text-muted-foreground">
                  統合管理システム
                </span>
              </div>
            </div>
          </SidebarHeader>
          
          <SidebarContent>
            <SidebarGroup>
              <SidebarGroupContent>
                <SidebarMenu>
                  {menuItems.map((item) => (
                    <SidebarMenuItem key={item.id}>
                      <SidebarMenuButton
                        onClick={() => handleMenuClick(item)}
                        isActive={activeTab === item.id || pathname === item.href}
                        disabled={!item.enabled}
                        className={`
                          group w-full transition-all duration-200
                          ${!item.enabled 
                            ? 'opacity-40 cursor-not-allowed hover:bg-transparent hover:text-sidebar-foreground' 
                            : 'cursor-pointer'
                          }
                        `}
                        tooltip={!item.enabled ? `${item.title} - ${item.description}` : undefined}
                      >
                        <item.icon className={`
                          size-4 transition-opacity duration-200
                          ${!item.enabled ? 'opacity-50' : ''}
                        `} />
                        <span className={`
                          transition-opacity duration-200
                          ${!item.enabled ? 'opacity-60' : ''}
                        `}>
                          {item.title}
                        </span>
                        {!item.enabled && (
                          <span className="ml-auto text-xs text-muted-foreground/60">
                            Soon
                          </span>
                        )}
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  ))}
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>
          </SidebarContent>
          
          <SidebarFooter className="border-t border-sidebar-border">
            <SidebarMenu>
              <SidebarMenuItem>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <SidebarMenuButton
                      size="lg" 
                      className="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
                    >
                      <Avatar className="h-8 w-8 rounded-lg">
                        <AvatarImage 
                          src={user?.imageUrl} 
                          alt={user?.fullName || "User"} 
                        />
                        <AvatarFallback className="rounded-lg bg-primary text-primary-foreground">
                          {user?.fullName?.split(' ').map(n => n[0]).join('') || 'U'}
                        </AvatarFallback>
                      </Avatar>
                      <div className="grid flex-1 text-left text-sm leading-tight">
                        <span className="truncate font-semibold">
                          {user?.fullName || 'ユーザー'}
                        </span>
                        <span className="truncate text-xs text-muted-foreground">
                          {user?.emailAddresses[0]?.emailAddress}
                        </span>
                      </div>
                    </SidebarMenuButton>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent 
                    className="w-[--radix-dropdown-menu-trigger-width] min-w-56 rounded-lg"
                    side="bottom"
                    align="end"
                    sideOffset={4}
                  >
                    <DropdownMenuLabel className="p-0 font-normal">
                      <div className="flex items-center gap-2 px-1 py-1.5 text-left text-sm">
                        <Avatar className="h-8 w-8 rounded-lg">
                          <AvatarImage 
                            src={user?.imageUrl} 
                            alt={user?.fullName || "User"} 
                          />
                          <AvatarFallback className="rounded-lg">
                            {user?.fullName?.split(' ').map(n => n[0]).join('') || 'U'}
                          </AvatarFallback>
                        </Avatar>
                        <div className="grid flex-1 text-left text-sm leading-tight">
                          <span className="truncate font-semibold">
                            {user?.fullName || 'ユーザー'}
                          </span>
                          <span className="truncate text-xs text-muted-foreground">
                            {user?.emailAddresses[0]?.emailAddress}
                          </span>
                        </div>
                      </div>
                    </DropdownMenuLabel>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem className="gap-2" disabled>
                      <User className="h-4 w-4" />
                      プロフィール
                    </DropdownMenuItem>
                    <DropdownMenuItem className="gap-2" disabled>
                      <Settings className="h-4 w-4" />
                      設定
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem onClick={handleSignOut} className="gap-2">
                      <LogOut className="h-4 w-4" />
                      ログアウト
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarFooter>
          <SidebarRail />
        </Sidebar>
        
        <SidebarInset>
          <header className="flex h-16 shrink-0 items-center gap-2 border-b px-4">
            <SidebarTrigger className="-ml-1" />
            <div className="mx-auto">
              <h1 className="text-lg font-semibold">
                {menuItems.find(item => item.id === activeTab)?.title || 'b&q Hub'}
              </h1>
            </div>
          </header>
          <div className="flex flex-1 flex-col gap-4 p-4">
            {children}
          </div>
        </SidebarInset>
      </div>
    </SidebarProvider>
  );
}