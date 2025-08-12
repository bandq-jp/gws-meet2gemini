"use client";

import { useAuth, useUser } from "@clerk/nextjs";
import { useRouter, usePathname } from "next/navigation";
import { useState, useEffect } from "react";
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
  SidebarRail,
} from "@/components/ui/sidebar";
import {
  Users,
  Settings,
  BarChart3,
  Building2,
  Award,
  User,
  LogOut,
  ChevronDown,
  ChevronsLeftRight,
  FileText,
  Database,
  Target,
  TrendingUp,
  Calendar,
  UserCheck,
  MessageSquare,
  PieChart,
} from "lucide-react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export function AppSidebar() {
  const { signOut } = useAuth();
  const { user } = useUser();
  const router = useRouter();
  const pathname = usePathname();

  const teamItems = [
    {
      name: "ひとキャリ",
      href: "/hitocari",
      id: "hitocari",
      enabled: true,
      icon: Users,
    },
    {
      name: "モノテック",
      href: "/monotech", 
      id: "monotech",
      enabled: false,
      icon: Building2,
    },
    {
      name: "AchieveHR",
      href: "/achievehr",
      id: "achievehr", 
      enabled: false,
      icon: Award,
    },
  ];

  // 現在のパスに基づいてアクティブなチームを決定
  const getCurrentTeam = () => {
    return teamItems.find(team => pathname?.startsWith(team.href)) || teamItems[0];
  };

  const [activeTeam, setActiveTeam] = useState(getCurrentTeam());

  // パスが変更されたときにアクティブなチームを更新
  useEffect(() => {
    const currentTeam = getCurrentTeam();
    setActiveTeam(currentTeam);
  }, [pathname]);

  const handleTeamSelect = (team: typeof teamItems[0]) => {
    if (team.enabled) {
      setActiveTeam(team);
      router.push(team.href);
    }
  };

  // チーム別メニュー定義
  const getTeamMenuItems = (teamId: string) => {
    switch (teamId) {
      case 'hitocari':
        return [
          {
            title: "議事録管理",
            icon: FileText,
            href: "/hitocari",
            id: "meetings",
            enabled: true,
            description: "Google Meet議事録の管理と構造化データ抽出",
          },
          {
            title: "Zoho CRM",
            icon: Database,
            href: "/hitocari/zoho",
            id: "zoho",
            enabled: false,
            description: "求職者データベース管理",
          },
          {
            title: "効果測定",
            icon: Target,
            href: "/hitocari/analytics",
            id: "analytics",
            enabled: false,
            description: "採用活動の効果測定・分析",
          },
          {
            title: "分析",
            icon: TrendingUp,
            href: "/hitocari/reports",
            id: "reports",
            enabled: false,
            description: "データ分析・レポート機能",
          },
          {
            title: "候補者管理",
            icon: UserCheck,
            href: "/hitocari/candidates",
            id: "candidates",
            enabled: false,
            description: "候補者情報の統合管理",
          },
          {
            title: "面談予約",
            icon: Calendar,
            href: "/hitocari/appointments",
            id: "appointments",
            enabled: false,
            description: "面談・面接のスケジュール管理",
          },
          {
            title: "コミュニケーション",
            icon: MessageSquare,
            href: "/hitocari/communication",
            id: "communication",
            enabled: false,
            description: "候補者とのやり取り管理",
          },
        ];
      case 'monotech':
        return [
          {
            title: "プロジェクト管理",
            icon: Building2,
            href: "/monotech/projects",
            id: "projects",
            enabled: false,
            description: "技術プロジェクトの管理",
          },
          {
            title: "技術分析",
            icon: BarChart3,
            href: "/monotech/tech-analytics",
            id: "tech-analytics",
            enabled: false,
            description: "技術動向の分析",
          },
        ];
      case 'achievehr':
        return [
          {
            title: "人事評価",
            icon: Award,
            href: "/achievehr/evaluation",
            id: "evaluation",
            enabled: false,
            description: "従業員の人事評価システム",
          },
          {
            title: "パフォーマンス分析",
            icon: PieChart,
            href: "/achievehr/performance",
            id: "performance",
            enabled: false,
            description: "パフォーマンスデータの分析",
          },
        ];
      default:
        return [];
    }
  };

  const menuItems = getTeamMenuItems(activeTeam.id);

  const handleMenuClick = (item: typeof menuItems[0]) => {
    if (item.enabled) {
      router.push(item.href);
    }
  };

  const handleSignOut = () => {
    signOut(() => router.push("/"));
  };

  return (
    <Sidebar variant="sidebar" collapsible="icon">
      <SidebarHeader className="border-b border-sidebar-border">
        <SidebarMenu>
          <SidebarMenuItem>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <SidebarMenuButton
                  size="lg"
                  className="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
                >
                  <div className="flex aspect-square size-8 items-center justify-center rounded-lg text-primary-foreground bg-[linear-gradient(135deg,var(--brand-300),var(--brand-400))]">
                    <Building2 className="size-4" />
                  </div>
                  <div className="grid flex-1 text-left text-sm leading-tight">
                    <span className="truncate font-semibold">b&q Hub</span>
                    <span className="truncate text-xs text-muted-foreground">
                      {activeTeam.name}
                    </span>
                  </div>
                  <ChevronDown className="ml-auto" />
                </SidebarMenuButton>
              </DropdownMenuTrigger>
              <DropdownMenuContent
                className="w-[--radix-dropdown-menu-trigger-width] min-w-56 rounded-lg"
                align="start"
                side="bottom"
                sideOffset={4}
              >
                {teamItems.map((team) => (
                  <DropdownMenuItem
                    key={team.id}
                    onClick={() => handleTeamSelect(team)}
                    className={`gap-2 ${
                      !team.enabled
                        ? 'opacity-50 cursor-not-allowed'
                        : 'cursor-pointer'
                    }`}
                    disabled={!team.enabled}
                  >
                    <team.icon className="size-4" />
                    <div className="flex-1">
                      <div className="font-medium">{team.name}</div>
                      {!team.enabled && (
                        <div className="text-xs text-muted-foreground">開発中</div>
                      )}
                    </div>
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              {menuItems.map((item) => (
                <SidebarMenuItem key={`${activeTeam.id}-${item.id}`}>
                  <SidebarMenuButton
                    onClick={() => handleMenuClick(item)}
                    isActive={pathname === item.href}
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
  );
}