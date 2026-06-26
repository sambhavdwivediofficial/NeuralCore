// frontend/app/chat/page.jsx

'use client';

import '@/styles/chat.css';
import { useState } from 'react';
import { BookOpen, ChevronRight } from 'lucide-react';
import { ChatWindow } from '@/components/chat/ChatWindow';
import { useKnowledgeBases } from '@/hooks/useKnowledgeBases';
import { EmptyState } from '@/components/common/EmptyState';
import { PageLoader } from '@/components/common/Loader';
import { ROUTES } from '@/lib/routes';
import Link from 'next/link';
import { cn } from '@/lib/utils';

export default function ChatPage() {
  const { knowledgeBases, isLoading } = useKnowledgeBases();
  const [selectedKb, setSelectedKb] = useState(null);

  if (isLoading) {
    return <div className="flex h-full items-center justify-center"><PageLoader /></div>;
  }

  return (
    <div className="chat-layout">
      <aside className="chat-sidebar">
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <span className="text-xs font-semibold text-foreground">Knowledge Bases</span>
          <Link href={ROUTES.KNOWLEDGE_BASE_CREATE}
            className="flex h-5 w-5 items-center justify-center rounded text-muted-foreground hover:text-foreground hover:bg-accent transition-colors">
            <span className="text-sm leading-none">+</span>
          </Link>
        </div>
        <div className="flex-1 overflow-y-auto py-2 scrollbar-thin">
          {knowledgeBases.length === 0 ? (
            <div className="px-3 py-6 text-center">
              <p className="text-xs text-muted-foreground">No knowledge bases yet</p>
              <Link href={ROUTES.KNOWLEDGE_BASE_CREATE} className="text-xs text-primary hover:underline mt-1 block">
                Create one
              </Link>
            </div>
          ) : (
            knowledgeBases.map((kb) => (
              <button key={kb.id} type="button" onClick={() => setSelectedKb(kb)}
                className={cn(
                  'flex w-full items-center gap-2.5 px-3 py-2 text-left transition-colors hover:bg-accent',
                  selectedKb?.id === kb.id ? 'bg-primary/8 text-primary' : 'text-muted-foreground'
                )}>
                <BookOpen className="h-3.5 w-3.5 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="truncate text-xs font-medium">{kb.name}</p>
                  <p className="text-[0.625rem] text-muted-foreground">{kb.chunk_count ?? 0} chunks</p>
                </div>
                {selectedKb?.id === kb.id && <ChevronRight className="h-3 w-3 flex-shrink-0" />}
              </button>
            ))
          )}
        </div>
      </aside>

      {selectedKb ? (
        <ChatWindow knowledgeBaseId={selectedKb.id} />
      ) : (
        <div className="flex flex-1 flex-col items-center justify-center gap-4 text-center p-8">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 text-primary">
            <BookOpen className="h-7 w-7" />
          </div>
          <div className="flex flex-col gap-1.5">
            <h3 className="text-sm font-semibold text-foreground">Select a knowledge base</h3>
            <p className="text-xs text-muted-foreground max-w-xs">
              Choose a knowledge base from the sidebar to start a conversation.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
