// frontend/app/knowledge-bases/[kb_id]/page.jsx

'use client';

import { use, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  ArrowLeft, FileText, MoreHorizontal, RefreshCw, Trash2, Boxes, SearchCode,
} from 'lucide-react';
import { AppShell } from '@/components/layout/AppShell';
import { Button } from '@/components/common/Button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/common/Card';
import { Badge } from '@/components/common/Badge';
import { PageLoader } from '@/components/common/Loader';
import { EmptyState } from '@/components/common/EmptyState';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/common/Tabs';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/common/Table';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/common/DropdownMenu';
import { UploadBox } from '@/components/knowledge/UploadBox';
import { useKnowledgeBase, useDocuments, useKnowledgeBaseStats } from '@/hooks/useKnowledgeBases';
import { uploadDocument, deleteDocument, reprocessDocument } from '@/services/knowledgebases';
import { toast } from '@/components/common/Toast';
import { getErrorMessage } from '@/lib/axios';
import { ROUTES } from '@/lib/routes';
import { DOCUMENT_STATUS, VECTOR_STORE_LABELS } from '@/lib/constants';
import { formatBytes, formatRelativeTime, formatCompactNumber } from '@/lib/utils';
import '@/styles/knowledge.css';

const STATUS_VARIANT = {
  [DOCUMENT_STATUS.READY]: 'success',
  [DOCUMENT_STATUS.PROCESSING]: 'default',
  [DOCUMENT_STATUS.FAILED]: 'destructive',
  [DOCUMENT_STATUS.QUEUED]: 'muted',
};

export default function KnowledgeBaseDetailPage({ params }) {
  const { kb_id } = use(params);
  const router = useRouter();
  const { knowledgeBase, isLoading } = useKnowledgeBase(kb_id);
  const { documents, isLoading: documentsLoading, refresh: refreshDocuments } = useDocuments(kb_id, { page_size: 50 });
  const { stats } = useKnowledgeBaseStats(kb_id);
  const [isUploading, setIsUploading] = useState(false);

  const handleUpload = async (files) => {
    setIsUploading(true);
    try {
      for (const file of files) {
        const formData = new FormData();
        formData.append('file', file);
        await uploadDocument(kb_id, formData);
      }
      toast.success(`${files.length} file${files.length > 1 ? 's' : ''} queued for processing`);
      refreshDocuments();
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setIsUploading(false);
    }
  };

  const handleDelete = async (document) => {
    try {
      await deleteDocument(kb_id, document.id);
      toast.success(`${document.name} deleted`);
      refreshDocuments();
    } catch (error) {
      toast.error(getErrorMessage(error));
    }
  };

  const handleReprocess = async (document) => {
    try {
      await reprocessDocument(kb_id, document.id);
      toast.success(`Reprocessing ${document.name}`);
      refreshDocuments();
    } catch (error) {
      toast.error(getErrorMessage(error));
    }
  };

  if (isLoading) {
    return (
      <AppShell>
        <PageLoader label="Loading knowledge base" />
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="flex flex-col gap-5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex flex-col gap-2">
            <Button variant="ghost" size="sm" className="-ml-2 w-fit" onClick={() => router.push(ROUTES.KNOWLEDGE_BASES)}>
              <ArrowLeft className="h-3.5 w-3.5" />
              Knowledge bases
            </Button>
            <h1 className="text-lg font-semibold tracking-tight text-foreground">{knowledgeBase?.name}</h1>
            <p className="text-sm text-muted-foreground">{knowledgeBase?.description || 'No description provided'}</p>
            <div className="flex items-center gap-2">
              <Badge variant="muted">{VECTOR_STORE_LABELS[knowledgeBase?.vector_store] || knowledgeBase?.vector_store}</Badge>
              <Badge variant="outline">{formatCompactNumber(stats?.document_count)} documents</Badge>
              <Badge variant="outline">{formatCompactNumber(stats?.chunk_count)} chunks</Badge>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={() => router.push(ROUTES.KNOWLEDGE_BASE_CHUNKS(kb_id))}>
              <Boxes className="h-3.5 w-3.5" /> Chunks
            </Button>
            <Button variant="outline" size="sm" onClick={() => router.push(ROUTES.KNOWLEDGE_BASE_RETRIEVAL(kb_id))}>
              <SearchCode className="h-3.5 w-3.5" /> Test retrieval
            </Button>
          </div>
        </div>

        <Tabs defaultValue="documents">
          <TabsList>
            <TabsTrigger value="documents">Documents</TabsTrigger>
            <TabsTrigger value="upload">Upload</TabsTrigger>
          </TabsList>

          <TabsContent value="documents">
            <Card>
              <CardHeader>
                <CardTitle>Documents</CardTitle>
                <CardDescription>All documents ingested into this knowledge base</CardDescription>
              </CardHeader>
              <CardContent className="p-0">
                {documentsLoading ? (
                  <div className="flex flex-col gap-2 p-4">
                    {Array.from({ length: 4 }).map((_, i) => (
                      <div key={i} className="skeleton h-12 w-full rounded-md" />
                    ))}
                  </div>
                ) : documents.length === 0 ? (
                  <div className="p-4">
                    <EmptyState icon={FileText} title="No documents yet" description="Upload files from the Upload tab to start building this knowledge base." />
                  </div>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Name</TableHead>
                        <TableHead className="w-24">Size</TableHead>
                        <TableHead className="w-28">Status</TableHead>
                        <TableHead className="w-32">Updated</TableHead>
                        <TableHead className="w-16" />
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {documents.map((doc) => (
                        <TableRow key={doc.id}>
                          <TableCell className="font-medium text-foreground">{doc.name}</TableCell>
                          <TableCell className="text-xs text-muted-foreground">{formatBytes(doc.size_bytes)}</TableCell>
                          <TableCell>
                            <Badge variant={STATUS_VARIANT[doc.status] || 'muted'}>{doc.status}</Badge>
                          </TableCell>
                          <TableCell className="text-xs text-muted-foreground">{formatRelativeTime(doc.updated_at)}</TableCell>
                          <TableCell>
                            <DropdownMenu>
                              <DropdownMenuTrigger asChild>
                                <Button variant="ghost" size="iconSm"><MoreHorizontal className="h-3.5 w-3.5" /></Button>
                              </DropdownMenuTrigger>
                              <DropdownMenuContent align="end">
                                <DropdownMenuItem onClick={() => handleReprocess(doc)}>
                                  <RefreshCw className="h-3.5 w-3.5" /> Reprocess
                                </DropdownMenuItem>
                                <DropdownMenuItem className="text-destructive focus:text-destructive" onClick={() => handleDelete(doc)}>
                                  <Trash2 className="h-3.5 w-3.5" /> Delete
                                </DropdownMenuItem>
                              </DropdownMenuContent>
                            </DropdownMenu>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="upload">
            <Card>
              <CardHeader>
                <CardTitle>Upload documents</CardTitle>
                <CardDescription>
                  Files will be chunked using the {knowledgeBase?.chunking_strategy} strategy and embedded with {knowledgeBase?.embedding_provider}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <UploadBox onUpload={handleUpload} isUploading={isUploading} />
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </AppShell>
  );
}
