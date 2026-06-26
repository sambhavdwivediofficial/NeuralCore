// app/projects/page.jsx

'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Plus, FolderKanban, MoreHorizontal, Trash2, Settings, ExternalLink } from 'lucide-react';
import { AppShell } from '@/components/layout/AppShell';
import { Button } from '@/components/common/Button';
import { Card, CardContent } from '@/components/common/Card';
import { Badge } from '@/components/common/Badge';
import { SearchBar } from '@/components/common/SearchBar';
import { EmptyState } from '@/components/common/EmptyState';
import { SkeletonCard } from '@/components/common/Loader';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from '@/components/common/DropdownMenu';
import {
  Modal,
  ModalContent,
  ModalHeader,
  ModalTitle,
  ModalDescription,
  ModalFooter,
} from '@/components/common/Modal';
import { useProjects } from '@/hooks/useProjects';
import { useProjectContext } from '@/context/ProjectContext';
import { deleteProject } from '@/services/projects';
import { toast } from '@/components/common/Toast';
import { getErrorMessage } from '@/lib/axios';
import { ROUTES } from '@/lib/routes';
import { formatRelativeTime, formatCompactNumber } from '@/lib/utils';
import { LLM_PROVIDER_LABELS } from '@/lib/constants';
import '@/styles/dashboard.css';

export default function ProjectsPage() {
  const router = useRouter();
  const [search, setSearch] = useState('');
  const { projects, isLoading, refresh } = useProjects({ search });
  const { setActiveProject } = useProjectContext();
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const handleOpen = (project) => {
    setActiveProject(project.id);
    router.push(ROUTES.PROJECT(project.id));
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setIsDeleting(true);
    try {
      await deleteProject(deleteTarget.id);
      toast.success(`${deleteTarget.name} deleted`);
      setDeleteTarget(null);
      refresh();
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <AppShell>
      <div className="flex flex-col gap-5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-lg font-semibold tracking-tight text-foreground">Projects</h1>
            <p className="text-sm text-muted-foreground">
              Workspaces for organizing agents, knowledge bases, and configurations
            </p>
          </div>
          <Button onClick={() => router.push(ROUTES.PROJECT_CREATE)}>
            <Plus className="h-3.5 w-3.5" />
            New project
          </Button>
        </div>

        <SearchBar value={search} onChange={setSearch} placeholder="Search projects" className="max-w-sm" />

        {isLoading ? (
          <div className="dashboard-grid">
            {Array.from({ length: 6 }).map((_, index) => (
              <SkeletonCard key={index} />
            ))}
          </div>
        ) : projects.length === 0 ? (
          <EmptyState
            icon={FolderKanban}
            title="No projects yet"
            description="Create your first project to start building knowledge bases and agents."
            action={
              <Button onClick={() => router.push(ROUTES.PROJECT_CREATE)}>
                <Plus className="h-3.5 w-3.5" />
                New project
              </Button>
            }
          />
        ) : (
          <div className="dashboard-grid">
            {projects.map((project) => (
              <Card key={project.id} className="group transition-colors hover:border-primary/40">
                <CardContent className="flex flex-col gap-3 p-4">
                  <div className="flex items-start justify-between">
                    <div
                      className="flex flex-1 cursor-pointer flex-col gap-1"
                      onClick={() => handleOpen(project)}
                    >
                      <span className="text-sm font-semibold text-foreground">{project.name}</span>
                      <span className="line-clamp-2 text-xs text-muted-foreground">
                        {project.description || 'No description provided'}
                      </span>
                    </div>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="iconSm" onClick={(e) => e.stopPropagation()}>
                          <MoreHorizontal className="h-3.5 w-3.5" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={() => handleOpen(project)}>
                          <ExternalLink className="h-3.5 w-3.5" />
                          Open
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => router.push(ROUTES.PROJECT_SETTINGS(project.id))}>
                          <Settings className="h-3.5 w-3.5" />
                          Settings
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem
                          className="text-destructive focus:text-destructive"
                          onClick={() => setDeleteTarget(project)}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                          Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>

                  <div className="flex items-center gap-2">
                    <Badge variant="muted">
                      {LLM_PROVIDER_LABELS[project.default_llm_provider] || project.default_llm_provider}
                    </Badge>
                    <Badge variant="outline">{formatCompactNumber(project.knowledge_base_count)} KBs</Badge>
                    <Badge variant="outline">{formatCompactNumber(project.agent_count)} agents</Badge>
                  </div>

                  <span className="text-xs text-muted-foreground">
                    Updated {formatRelativeTime(project.updated_at)}
                  </span>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      <Modal open={Boolean(deleteTarget)} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <ModalContent>
          <ModalHeader>
            <ModalTitle>Delete project</ModalTitle>
            <ModalDescription>
              This will permanently delete &quot;{deleteTarget?.name}&quot; including all knowledge
              bases, agents, and configurations. This action cannot be undone.
            </ModalDescription>
          </ModalHeader>
          <ModalFooter>
            <Button variant="outline" onClick={() => setDeleteTarget(null)}>
              Cancel
            </Button>
            <Button variant="destructive" isLoading={isDeleting} onClick={handleDelete}>
              Delete project
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </AppShell>
  );
}
