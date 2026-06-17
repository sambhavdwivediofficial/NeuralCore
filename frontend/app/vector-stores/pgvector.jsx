// app/vector-stores/pgvector.jsx

'use client';

import { useRouter } from 'next/navigation';
import { ArrowLeft } from 'lucide-react';
import { AppShell } from '@/components/layout/AppShell';
import { Button } from '@/components/common/Button';
import { PgVectorPanel } from '@/components/vectorstores/PgVectorPanel';
import { useVectorStores } from '@/hooks/useVectorStores';
import { ROUTES } from '@/lib/routes';
import { VECTOR_STORE_PROVIDERS } from '@/lib/constants';
import { PageLoader } from '@/components/common/Loader';

export default function PgVectorStorePage() {
  const router = useRouter();
  const { stores, isLoading } = useVectorStores();
  const pgvectorStore = stores.find((store) => store.provider === VECTOR_STORE_PROVIDERS.PGVECTOR);

  if (isLoading) {
    return (
      <AppShell>
        <PageLoader label="Loading PGVector status" />
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="flex flex-col gap-5">
        <Button
          variant="ghost"
          size="sm"
          className="-ml-2 w-fit"
          onClick={() => router.push(ROUTES.VECTOR_STORES)}
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Vector stores
        </Button>

        <div>
          <h1 className="text-lg font-semibold tracking-tight text-foreground">PGVector</h1>
          <p className="text-sm text-muted-foreground">
            PostgreSQL extension supporting ivfflat and hnsw index types
          </p>
        </div>

        <PgVectorPanel storeId={pgvectorStore?.id} />
      </div>
    </AppShell>
  );
}
