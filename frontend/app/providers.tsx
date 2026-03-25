"use client";

import { I18nProvider } from "@/lib/i18n";
import { ThemeProvider } from "next-themes";

/** 全局 Providers：暗黑模式 + 国际化 */
export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
      <I18nProvider>{children}</I18nProvider>
    </ThemeProvider>
  );
}
