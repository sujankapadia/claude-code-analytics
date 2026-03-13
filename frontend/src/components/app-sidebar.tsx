import { useQuery } from "@tanstack/react-query";
import { NavLink, useLocation } from "react-router-dom";
import {
  BarChart3,
  BookOpen,
  BrainCircuit,
  FolderOpen,
  Home,
  Import,
  MessageSquare,
  Search,
} from "lucide-react";

import { fetchProjects } from "@/api/client";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import { ScrollArea } from "@/components/ui/scroll-area";

const navItems = [
  { to: "/", label: "Dashboard", icon: Home },
  { to: "/sessions", label: "Sessions", icon: MessageSquare },
  { to: "/search", label: "Search", icon: Search },
  { to: "/analytics", label: "Analytics", icon: BarChart3 },
  { to: "/analysis", label: "Analysis", icon: BrainCircuit },
  { to: "/examples", label: "Examples", icon: BookOpen },
  { to: "/import", label: "Import", icon: Import },
];

export function AppSidebar() {
  const location = useLocation();
  const { data: projects } = useQuery({
    queryKey: ["projects"],
    queryFn: fetchProjects,
  });

  return (
    <Sidebar>
      <SidebarHeader className="border-b px-4 py-3">
        <span className="text-sm font-semibold tracking-tight">
          Claude Code Analytics
        </span>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Navigation</SidebarGroupLabel>
          <SidebarMenu>
            {navItems.map((item) => (
              <SidebarMenuItem key={item.to}>
                <SidebarMenuButton
                  isActive={
                    item.to === "/"
                      ? location.pathname === "/"
                      : location.pathname.startsWith(item.to)
                  }
                  render={<NavLink to={item.to} />}
                >
                  <item.icon className="size-4" />
                  <span>{item.label}</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
            ))}
          </SidebarMenu>
        </SidebarGroup>

        <SidebarGroup>
          <SidebarGroupLabel>Projects</SidebarGroupLabel>
          <ScrollArea className="h-[calc(100vh-20rem)]">
            <SidebarMenu>
              {projects?.map((p) => {
                const shortName = p.project_name.split("/").pop() ?? p.project_name;
                return (
                  <SidebarMenuItem key={p.project_id}>
                    <SidebarMenuButton
                      isActive={location.search.includes(p.project_id)}
                      render={<NavLink to={`/sessions?project_id=${p.project_id}`} />}
                    >
                      <FolderOpen className="size-4" />
                      <span className="truncate" title={p.project_name}>
                        {shortName}
                      </span>
                      <span className="ml-auto text-xs text-muted-foreground">
                        {p.total_sessions}
                      </span>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                );
              })}
            </SidebarMenu>
          </ScrollArea>
        </SidebarGroup>
      </SidebarContent>
    </Sidebar>
  );
}
