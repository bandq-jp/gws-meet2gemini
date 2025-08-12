"use client";

import { useState } from "react";
import { UserButton, useUser } from "@clerk/nextjs";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  Building2,
  Users,
  Settings,
  Home,
  BarChart3,
  FileText,
  Briefcase,
} from "lucide-react";

interface AppShellProps {
  children: React.ReactNode;
  activeTab?: string;
}

export function AppShell({ children, activeTab = "hitocari" }: AppShellProps) {
  const { user } = useUser();
  const [collapsed, setCollapsed] = useState(false);

  const menuItems = [
    {
      id: "dashboard",
      title: "ダッシュボード",
      icon: Home,
      href: "/",
      enabled: true,
    },
    {
      id: "hitocari",
      title: "ひとキャリ",
      icon: Users,
      href: "/hitocari",
      enabled: true,
      description: "議事録・面談管理",
    },
    {
      id: "monotech",
      title: "モノテック",
      icon: Building2,
      href: "/monotech",
      enabled: false,
      description: "準備中",
    },
    {
      id: "achievehr",
      title: "AchieveHR",
      icon: Briefcase,
      href: "/achievehr",
      enabled: false,
      description: "準備中",
    },
  ];

  const adminItems = [
    {
      id: "analytics",
      title: "分析",
      icon: BarChart3,
      href: "/analytics",
      enabled: false,
    },
    {
      id: "settings",
      title: "設定",
      icon: Settings,
      href: "/settings",
      enabled: false,
    },
  ];

  return (
    <SidebarProvider>
      <div className="min-h-screen flex w-full bg-background">
        <Sidebar variant="floating" className="border-r">
          <SidebarHeader className="border-b p-4">
            <div className="flex items-center gap-2">
              <div className="flex items-center justify-center w-8 h-8 bg-primary text-primary-foreground rounded-lg font-bold">
                b&q
              </div>
              <div className="flex flex-col">
                <h1 className="font-semibold text-sm">b&q Hub</h1>
                <p className="text-xs text-muted-foreground">統合管理システム</p>
              </div>
            </div>
          </SidebarHeader>

          <SidebarContent>
            <SidebarGroup>
              <SidebarGroupLabel>メインメニュー</SidebarGroupLabel>
              <SidebarGroupContent>
                <SidebarMenu>
                  {menuItems.map((item) => (
                    <SidebarMenuItem key={item.id}>
                      <SidebarMenuButton
                        asChild
                        isActive={activeTab === item.id}
                        disabled={!item.enabled}
                      >
                        <a 
                          href={item.enabled ? item.href : "#"}
                          className="w-full flex items-center gap-3 px-3 py-2 rounded-md transition-colors relative"
                        >
                          <item.icon className="w-4 h-4 flex-shrink-0" />
                          <div className="flex-1 text-left">
                            <div className="flex items-center gap-2">
                              <span className="text-sm font-medium">{item.title}</span>
                              {!item.enabled && (
                                <Badge variant="outline" className="text-xs">
                                  準備中
                                </Badge>
                              )}
                            </div>
                            {item.description && (
                              <p className="text-xs text-muted-foreground mt-0.5">
                                {item.description}
                              </p>
                            )}
                          </div>
                        </a>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  ))}
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>

            <SidebarGroup>
              <SidebarGroupLabel>管理</SidebarGroupLabel>
              <SidebarGroupContent>
                <SidebarMenu>
                  {adminItems.map((item) => (
                    <SidebarMenuItem key={item.id}>
                      <SidebarMenuButton
                        asChild
                        disabled={!item.enabled}
                      >
                        <a 
                          href={item.enabled ? item.href : "#"}
                          className="w-full flex items-center gap-3 px-3 py-2 rounded-md transition-colors"
                        >
                          <item.icon className="w-4 h-4" />
                          <span className="text-sm font-medium">{item.title}</span>
                          {!item.enabled && (
                            <Badge variant="outline" className="text-xs ml-auto">
                              準備中
                            </Badge>
                          )}
                        </a>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  ))}
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>
          </SidebarContent>

          <SidebarFooter className="border-t p-4">
            <div className="flex items-center gap-3">
              <UserButton 
                appearance={{
                  elements: {
                    userButtonAvatarBox: "w-8 h-8",
                  }
                }}
              />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-foreground truncate">
                  {user?.firstName} {user?.lastName}
                </p>
                <p className="text-xs text-muted-foreground truncate">
                  {user?.emailAddresses[0]?.emailAddress}
                </p>
              </div>
            </div>
          </SidebarFooter>
        </Sidebar>

        <main className="flex-1 flex flex-col overflow-hidden">
          <header className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
            <div className="flex h-14 items-center px-4">
              <SidebarTrigger className="mr-4" />
              <div className="flex items-center gap-4">
                <FileText className="w-5 h-5 text-muted-foreground" />
                <div>
                  <h2 className="text-lg font-semibold">
                    {menuItems.find(item => item.id === activeTab)?.title || "ダッシュボード"}
                  </h2>
                  <p className="text-sm text-muted-foreground">
                    {menuItems.find(item => item.id === activeTab)?.description || "統合管理システム"}
                  </p>
                </div>
              </div>
            </div>
          </header>
          <div className="flex-1 overflow-auto">
            {children}
          </div>
        </main>
      </div>
    </SidebarProvider>
  );
}