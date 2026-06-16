// app/vector-stores/page.jsx

'use client';

import { useRouter } from 'next/navigation';
import { Boxes, ChevronRight, Plus } from 'lucide-react';
import { AppShell } from '@/components/layout/AppShell';
import { Button } from '@/components/common/Button';
import { Card, CardContent } from '@/components/common/Card';
import { Badge } from '@/components/common/Badge';
import { EmptyState } from '@/components/common/EmptyState';
import { SkeletonCard } from '@/components/common/Loader';
import { useVectorStores } from '@/hooks/useVectorStores';
import { ROUTES } from '@/lib/routes';
import { VECTOR_STORE_PROVIDERS, VECTOR_STORE_LABELS } from '@/lib/constants';
import { formatCompactNumber, formatRelativeTime } from '@/lib/utils';
import '@/styles/dashboard.css';

const PROVIDER_ROUTE = {
  [VECTOR_STORE_PROVIDERS.QDRANT]: ROUTES.VECTOR_STORE_QDRANT,
  [VECTOR_STORE_PROVIDERS.MILVUS]: ROUTES.VECTOR_STORE_MILVUS,
  [VECTOR_STORE_PROVIDERS.PGVECTOR]: ROUTES.VECTOR_STORE_PGVECTOR,
};

export default function VectorStoresPage() {
  const router = useRouter();
  const { stores, isLoading } = useVectorStores();

  return (
    <AppShell>
      <div className="flex flex-col gap-5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-lg font-semibold tracking-tight text-foreground">Vector stores</h1>
            <p className="text-sm text-muted-foreground">
              Connected backends used for storing and searching embeddings
            </p>
          </div>
          <Button>
            <Plus className="h-3.5 w-3.5" />
            Connect store
          </Button>
        </div>

        {isLoading ? (
          <div className="dashboard-grid">
            {Array.from({ length: 4 }).map((_, index) => (
              <SkeletonCard key={index} />
            ))}
          </div>
        ) : stores.length === 0 ? (
          <EmptyState
            icon={Boxes}
            title="No vector stores connected"
            description="Connect Qdrant, Milvus, or PGVector to start storing embeddings."
          />
        ) : (
          <div className="dashboard-grid">
            {stores.map((store) => {
              const route = PROVIDER_ROUTE[store.provider];
              return (
                <Card
                  key={store.id}
                  className="cursor-pointer transition-colors hover:border-primary/40"
                  onClick={() => route && router.push(route)}
                >
                  <CardContent className="flex flex-col gap-3 p-4">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-semibold text-foreground">
                        {VECTOR_STORE_LABELS[store.provider] || store.provider}
                      </span>
                      <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant={store.healthy ? 'success' : 'destructive'}>
                        {store.healthy ? 'Healthy' : 'Unreachable'}
                      </Badge>
                      <Badge variant="outline">
                        {formatCompactNumber(store.collection_count)} collections
                      </Badge>
                    </div>
                    <span className="text-xs text-muted-foreground">
                      Checked {formatRelativeTime(store.last_checked_at)}
                    </span>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </div>
    </AppShell>
  );
}
