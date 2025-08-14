"use client";

import { useAuth, useUser } from "@clerk/nextjs";
import { useRouter, usePathname } from "next/navigation";
import { useEffect } from "react";
import { SidebarProvider } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/app-sidebar";

interface SidebarLayoutProps {
  children: React.ReactNode;
}

export function SidebarLayout({ children }: SidebarLayoutProps) {
  const { isLoaded, userId } = useAuth();
  const { user } = useUser();
  const router = useRouter();
  const pathname = usePathname();

  // Skip authentication check for sign-in, sign-up, and unauthorized pages
  const isAuthPage = pathname?.startsWith('/sign-') || pathname === '/unauthorized';

  useEffect(() => {
    if (!isAuthPage && isLoaded && !userId) {
      router.push('/sign-in');
      return;
    }

    if (!isAuthPage && isLoaded && user && userId) {
      const userEmail = user.emailAddresses[0]?.emailAddress;
      if (userEmail && !userEmail.endsWith('@bandq.jp')) {
        router.push('/unauthorized');
        return;
      }
    }
  }, [isLoaded, userId, user, router, isAuthPage]);

  // Show loading state while auth is loading
  if (!isAuthPage && !isLoaded) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
          <p className="mt-2 text-muted-foreground">読み込み中...</p>
        </div>
      </div>
    );
  }

  // If not authenticated and not on auth page, don't render anything (redirect will happen)
  if (!isAuthPage && !userId) {
    return null;
  }

  // For auth pages, don't show sidebar
  if (isAuthPage) {
    return <>{children}</>;
  }

  return (
    <SidebarProvider>
      <AppSidebar />
      <main className="flex-1 overflow-hidden">
        <div className="h-screen overflow-auto">
          {children}
        </div>
      </main>
    </SidebarProvider>
  );
}