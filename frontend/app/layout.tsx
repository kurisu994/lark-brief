import type { Metadata } from "next";
import "./globals.css";
import { AppNavbar } from "@/components/navbar";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "Lark Brief — 每日资讯简报",
  description: "每日资讯简报自动生成工具",
  icons: { icon: "/favicon.ico" },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN" className="h-full antialiased" suppressHydrationWarning>
      <body className="min-h-full flex flex-col bg-background font-sans">
        <Providers>
          <AppNavbar />
          <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 py-6">
            {children}
          </main>
        </Providers>
      </body>
    </html>
  );
}
