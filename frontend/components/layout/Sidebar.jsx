// frontend/components/layout/Sidebar.jsx
'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  FolderKanban,
  Database,
  Bot,
  Boxes,
  SearchCode,
  Activity,
  Settings,
  ChevronsLeft,
  ChevronsRight,
  Sparkles,
  MessageSquare,
  BookOpen,
  Workflow,
  FileText,
  Search,
  Layers,
  Puzzle,
  Building2,
} from 'lucide-react';
import { NAV_SECTIONS } from '@/lib/routes';
import { useSettingsContext } from '@/context/SettingsContext';
import { useProjectContext } from '@/context/ProjectContext';
import { cn } from '@/lib/utils';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/common/Select';

const ICONS = {
  LayoutDashboard,
  FolderKanban,
  Database,
  Bot,
  Boxes,
  SearchCode,
  Activity,
  Settings,
  MessageSquare,
  BookOpen,
  Workflow,
  FileText,
  Search,
  Layers,
  Puzzle,
  Building2,
};

export function Sidebar() {
  const pathname = usePathname();
  const { sidebarCollapsed, toggleSidebar } = useSettingsContext();
  const { projects, activeProjectId, setActiveProject, isLoading } = useProjectContext();

  return (
    <aside
      className={cn(
        'sticky top-0 flex h-screen flex-col border-r border-sidebar-border bg-sidebar transition-[width] duration-200',
        sidebarCollapsed ? 'w-16' : 'w-60'
      )}
    >
      <div className="flex h-14 items-center gap-2 border-b border-sidebar-border px-4">
        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-primary text-primary-foreground">
          <Sparkles className="h-4 w-4" />
        </div>
        {!sidebarCollapsed ? (
          <span className="text-sm font-semibold tracking-tight text-sidebar-foreground">
            NeuralCore
          </span>
        ) : null}
      </div>

      {!sidebarCollapsed ? (
        <div className="border-b border-sidebar-border p-3">
          <Select
            value={activeProjectId || ''}
            onValueChange={setActiveProject}
            disabled={isLoading || projects.length === 0}
          >
            <SelectTrigger className="h-8 bg-sidebar-accent text-xs">
              <SelectValue placeholder="Select project" />
            </SelectTrigger>
            <SelectContent>
              {projects.map((project) => (
                <SelectItem key={project.id} value={project.id}>
                  {project.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      ) : null}

      <nav className="scrollbar-thin flex-1 overflow-y-auto px-2 py-3">
        {NAV_SECTIONS.map((section) => (
          <div key={section.id} className="mb-4">
            {!sidebarCollapsed && section.label ? (
              <p className="mb-1 px-2 text-2xs font-medium uppercase tracking-wider text-sidebar-foreground/50">
                {section.label}
              </p>
            ) : null}
            <div className="flex flex-col gap-0.5">
              {section.items.map((item) => {
                const Icon = ICONS[item.icon];
                if (!Icon) return null;
                const isActive =
                  pathname === item.href || pathname.startsWith(`${item.href}/`);

                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    title={sidebarCollapsed ? item.label : undefined}
                    className={cn(
                      'flex items-center gap-2.5 rounded-md px-2 py-1.5 text-sm font-medium transition-colors',
                      isActive
                        ? 'bg-sidebar-accent text-sidebar-accent-foreground'
                        : 'text-sidebar-foreground/80 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground',
                      sidebarCollapsed && 'justify-center px-0'
                    )}
                  >
                    <Icon className="h-4 w-4 shrink-0" />
                    {!sidebarCollapsed ? <span>{item.label}</span> : null}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      <div className="border-t border-sidebar-border p-2">
        <button
          onClick={toggleSidebar}
          className="flex w-full items-center justify-center gap-2 rounded-md px-2 py-1.5 text-xs text-sidebar-foreground/70 transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
        >
          {sidebarCollapsed ? (
            <ChevronsRight className="h-4 w-4" />
          ) : (
            <>
              <ChevronsLeft className="h-4 w-4" />
              <span>Collapse</span>
            </>
          )}
        </button>
      </div>
    </aside>
  );
}
