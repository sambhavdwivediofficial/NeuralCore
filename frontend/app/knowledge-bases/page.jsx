// app/knowledge-bases/page.jsx

'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Plus, Database, MoreHorizontal, Trash2, ExternalLink } from 'lucide-react';
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
import { useKnowledgeBases } from '@/hooks/useKnowledgeBases';
import { useProjectContext } from '@/context/ProjectContext';
import { deleteKnowledgeBase } from '@/services/knowledgebases';
import { toast } from '@/components/common/Toast';
import { getErrorMessage } from '@/lib/axios';
import { ROUTES } from '@/lib/routes';
import { VECTOR_STORE_LABELS } from '@/lib/constants';
import { formatRelativeTime, formatCompactNumber } from '@/lib/utils';
import '@/styles/dashboard.css';

export default function KnowledgeBasesPage() {
  const router = useRouter();
  const { activeProjectId } = useProjectContext();
  const [search, setSearch] = useState('');
  const { knowledgeBases, isLoading, refresh } = useKnowledgeBases({
    project_id: activeProjectId,
    search,
  });
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setIsDeleting(true);
    try {
      await deleteKnowledgeBase(deleteTarget.id);
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
            <h1 className="text-lg font-semibold tracking-tight text-foreground">Knowledge bases</h1>
            <p className="text-sm text-muted-foreground">
              Document collections used for retrieval and RAG pipelines
            </p>
          </div>
          <Button onClick={() => router.push(ROUTES.KNOWLEDGE_BASE_CREATE)}>
            <Plus className="h-3.5 w-3.5" />
            New knowledge base
          </Button>
        </div>

        <SearchBar
          value={search}
          onChange={setSearch}
          placeholder="Search knowledge bases"
          className="max-w-sm"
        />

        {isLoading ? (
          <div className="dashboard-grid">
            {Array.from({ length: 6 }).map((_, index) => (
              <SkeletonCard key={index} />
            ))}
          </div>
        ) : knowledgeBases.length === 0 ? (
          <EmptyState
            icon={Database}
            title="No knowledge bases yet"
            description="Create a knowledge base and upload documents to enable retrieval."
            action={
              <Button onClick={() => router.push(ROUTES.KNOWLEDGE_BASE_CREATE)}>
                <Plus className="h-3.5 w-3.5" />
                New knowledge base
              </Button>
            }
          />
        ) : (
          <div className="dashboard-grid">
            {knowledgeBases.map((kb) => (
              <Card key={kb.id} className="transition-colors hover:border-primary/40">
                <CardContent className="flex flex-col gap-3 p-4">
                  <div className="flex items-start justify-between">
                    <button
                      className="flex flex-1 flex-col gap-1 text-left"
                      onClick={() => router.push(ROUTES.KNOWLEDGE_BASE_DETAIL(kb.id))}
                    >
                      <span className="text-sm font-semibold text-foreground">{kb.name}</span>
                      <span className="line-clamp-2 text-xs text-muted-foreground">
                        {kb.description || 'No description provided'}
                      </span>
                    </button>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="iconSm" onClick={(e) => e.stopPropagation()}>
                          <MoreHorizontal className="h-3.5 w-3.5" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={() => router.push(ROUTES.KNOWLEDGE_BASE_DETAIL(kb.id))}>
                          <ExternalLink className="h-3.5 w-3.5" />
                          Open
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem
                          className="text-destructive focus:text-destructive"
                          onClick={() => setDeleteTarget(kb)}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                          Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>

                  <div className="flex items-center gap-2">
                    <Badge variant="muted">{VECTOR_STORE_LABELS[kb.vector_store] || kb.vector_store}</Badge>
                    <Badge variant="outline">{formatCompactNumber(kb.document_count)} docs</Badge>
                    <Badge variant="outline">{formatCompactNumber(kb.chunk_count)} chunks</Badge>
                  </div>

                  <span className="text-xs text-muted-foreground">
                    Updated {formatRelativeTime(kb.updated_at)}
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
            <ModalTitle>Delete knowledge base</ModalTitle>
            <ModalDescription>
              This will permanently delete &quot;{deleteTarget?.name}&quot; including all documents
              and chunks. This action cannot be undone.
            </ModalDescription>
          </ModalHeader>
          <ModalFooter>
            <Button variant="outline" onClick={() => setDeleteTarget(null)}>
              Cancel
            </Button>
            <Button variant="destructive" isLoading={isDeleting} onClick={handleDelete}>
              Delete
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </AppShell>
  );
}
