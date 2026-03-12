import { useState } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/app-sidebar";
import { CommandPalette } from "@/components/command-palette";
import { useEventSource } from "@/hooks/use-event-source";
import { Separator } from "@/components/ui/separator";

import DashboardPage from "@/pages/dashboard";
import SessionsPage from "@/pages/sessions";
import SessionDetailPage from "@/pages/session-detail";
import SearchPage from "@/pages/search";
import AnalyticsPage from "@/pages/analytics";
import AnalysisPage from "@/pages/analysis";
import ImportPage from "@/pages/import";

function AppShell() {
  useEventSource();

  return (
    <SidebarProvider>
      <AppSidebar />
      <main className="flex-1 overflow-auto">
        <header className="flex h-12 items-center gap-2 border-b px-4">
          <SidebarTrigger />
          <Separator orientation="vertical" className="h-5" />
          <span className="text-sm text-muted-foreground">Claude Code Analytics</span>
          <span className="ml-auto text-xs text-muted-foreground">
            <kbd className="rounded border bg-muted px-1.5 py-0.5 text-[10px]">⌘K</kbd>
          </span>
        </header>
        <CommandPalette />
        <div className="p-6">
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/sessions" element={<SessionsPage />} />
            <Route path="/sessions/:id" element={<SessionDetailPage />} />
            <Route path="/search" element={<SearchPage />} />
            <Route path="/analytics" element={<AnalyticsPage />} />
            <Route path="/analysis" element={<AnalysisPage />} />
            <Route path="/import" element={<ImportPage />} />
          </Routes>
        </div>
      </main>
    </SidebarProvider>
  );
}

export default function App() {
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        retry: 1,
      },
    },
  }));

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AppShell />
      </BrowserRouter>
    </QueryClientProvider>
  );
}
