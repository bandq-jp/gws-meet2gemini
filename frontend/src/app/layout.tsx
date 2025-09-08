import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { ClerkProvider } from "@clerk/nextjs";
import { jaJP } from "@clerk/localizations";
import { Toaster } from "react-hot-toast";
import { SidebarLayout } from "@/components/sidebar-layout";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "b&q Hub",
  description: "b&q社内統合管理システム - ひとキャリ、モノテック、AchieveHR",
  keywords: ["b&q", "人材", "採用", "議事録", "CRM", "内部システム"],
  authors: [{ name: "b&q Inc." }],
  icons: {
    icon: "/favicon.ico",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const publishableKey = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY;
  const signInUrl = process.env.NEXT_PUBLIC_CLERK_SIGN_IN_URL || '/sign-in';
  const signUpUrl = process.env.NEXT_PUBLIC_CLERK_SIGN_UP_URL || '/sign-up';
  const afterSignInUrl = process.env.NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL || '/';
  const afterSignUpUrl = process.env.NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL || '/';
  return (
    <ClerkProvider 
      publishableKey={publishableKey}
      signInUrl={signInUrl}
      signUpUrl={signUpUrl}
      afterSignInUrl={afterSignInUrl}
      afterSignUpUrl={afterSignUpUrl}
      localization={jaJP}
      appearance={{
        variables: {
          colorPrimary: "hsl(220.9, 39.3%, 11%)",
          colorBackground: "hsl(0, 0%, 100%)",
          colorText: "hsl(224, 71.4%, 4.1%)",
          colorTextSecondary: "hsl(220, 8.9%, 46.1%)",
          colorInputBackground: "hsl(0, 0%, 100%)",
          colorInputText: "hsl(224, 71.4%, 4.1%)",
          borderRadius: "0.5rem"
        },
        elements: {
          card: "shadow-none border border-border",
          headerTitle: "text-foreground",
          headerSubtitle: "text-muted-foreground",
          formButtonPrimary: "bg-primary text-primary-foreground hover:bg-primary/90",
          formFieldInput: "border-input bg-background text-foreground",
          footerActionLink: "text-primary hover:text-primary/80",
        }
      }}
    >
      <html lang="ja" className="light">
        <body
          className={`${geistSans.variable} ${geistMono.variable} antialiased light`}
        >
          <SidebarLayout>
            {children}
          </SidebarLayout>
          <Toaster 
            position="top-right"
            toastOptions={{
              duration: 4000,
              style: {
                background: 'hsl(var(--background))',
                color: 'hsl(var(--foreground))',
                border: '1px solid hsl(var(--border))',
              },
            }}
          />
        </body>
      </html>
    </ClerkProvider>
  );
}
